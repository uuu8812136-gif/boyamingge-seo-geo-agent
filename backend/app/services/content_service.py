import hashlib
import json
import re
import time
from datetime import datetime, timezone

from sqlalchemy import String, cast, func, or_
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.redis_client import cache_delete, cache_get, cache_set
from app.models import Content, Intent, KnowledgeChunk, KnowledgeDocument

settings = get_settings()
from app.schemas.content import (
    ContentReference,
    ContentGenerateRequest,
    ContentGenerateResponse,
    ContentMetadata,
    EEATScoreRequest,
    EEATScoreResponse,
)
from app.schemas.knowledge import (
    KnowledgeDocumentCreate,
    KnowledgeDocumentDetail,
    KnowledgeDocumentItem,
    KnowledgeDocumentUpdate,
    KnowledgeListResponse,
    KnowledgeRebuildResponse,
    KnowledgeSearchHit,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
)
from app.services.eeat import evaluate_eeat
from app.services.llm import CITY_PINYIN, _mock_knowledge_references, generate_content, select_model


MAX_CHUNK_CHARS = 700
MAX_SEARCH_CANDIDATES = 200


def _content_cache_key(
    payload: ContentGenerateRequest,
    references: list[ContentReference] | None = None,
) -> str:
    raw_payload = payload.model_dump()
    raw_payload["knowledge_refs"] = [
        f"{ref.document_id}:{ref.chunk_id}:{ref.score}" for ref in references or []
    ]
    raw = json.dumps(raw_payload, ensure_ascii=False, sort_keys=True)
    return f"content:{hashlib.sha256(raw.encode()).hexdigest()}"


def _clean_str_list(items: list[str] | None) -> list[str]:
    if not items:
        return []
    cleaned: list[str] = []
    seen: set[str] = set()
    for item in items:
        value = str(item).strip()
        if not value:
            continue
        key = value.lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(value)
    return cleaned


def _split_terms(*values: str | None) -> list[str]:
    terms: list[str] = []
    seen: set[str] = set()
    for raw in values:
        if not raw:
            continue
        candidates = [raw, *re.split(r"[\s,，、;；|/]+", raw)]
        for candidate in candidates:
            value = candidate.strip()
            if len(value) < 2:
                continue
            key = value.lower()
            if key in seen:
                continue
            seen.add(key)
            terms.append(value)
    return terms


def _chunk_text(content: str, max_chars: int = MAX_CHUNK_CHARS) -> list[str]:
    paragraphs = [part.strip() for part in re.split(r"\n{2,}", content.strip()) if part.strip()]
    if not paragraphs and content.strip():
        paragraphs = [content.strip()]

    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if len(paragraph) > max_chars:
            if current:
                chunks.append(current.strip())
                current = ""
            for index in range(0, len(paragraph), max_chars):
                piece = paragraph[index : index + max_chars].strip()
                if piece:
                    chunks.append(piece)
            continue

        next_chunk = f"{current}\n\n{paragraph}".strip() if current else paragraph
        if len(next_chunk) <= max_chars:
            current = next_chunk
        else:
            if current:
                chunks.append(current.strip())
            current = paragraph

    if current:
        chunks.append(current.strip())
    return chunks


def _keywords_for_chunk(document: KnowledgeDocument, content: str) -> list[str]:
    base_terms = _split_terms(
        document.title,
        document.doc_type,
        document.city,
        document.category,
        " ".join(_clean_str_list(document.tags)),
    )
    content_terms = _split_terms(*re.split(r"[。！？；，、\n\r]+", content[:800]))
    return _clean_str_list([*base_terms, *content_terms])[:24]


def _replace_knowledge_chunks(db: Session, document: KnowledgeDocument) -> int:
    db.query(KnowledgeChunk).filter(KnowledgeChunk.document_id == document.id).delete()
    chunks = _chunk_text(document.content)
    if not chunks:
        raise ValueError("知识库正文不能为空")

    tags = _clean_str_list(document.tags)
    for index, chunk_content in enumerate(chunks):
        db.add(
            KnowledgeChunk(
                document_id=document.id,
                chunk_index=index,
                content=chunk_content,
                keywords=_keywords_for_chunk(document, chunk_content),
                tags=tags,
            )
        )
    return len(chunks)


def _knowledge_item(db: Session, document: KnowledgeDocument) -> KnowledgeDocumentItem:
    chunk_count = (
        db.query(func.count(KnowledgeChunk.id))
        .filter(KnowledgeChunk.document_id == document.id)
        .scalar()
    )
    return KnowledgeDocumentItem(
        id=document.id,
        title=document.title,
        doc_type=document.doc_type,
        city=document.city,
        category=document.category,
        tags=_clean_str_list(document.tags),
        source=document.source,
        status=document.status,
        created_at=document.created_at,
        updated_at=document.updated_at,
        chunk_count=chunk_count or 0,
    )


def list_knowledge_documents(
    db: Session,
    city: str | None = None,
    status: str | None = None,
    doc_type: str | None = None,
) -> KnowledgeListResponse:
    query = db.query(KnowledgeDocument)
    if city:
        query = query.filter(KnowledgeDocument.city == city)
    if status:
        query = query.filter(KnowledgeDocument.status == status)
    if doc_type:
        query = query.filter(KnowledgeDocument.doc_type == doc_type)

    total = query.count()
    rows = query.order_by(KnowledgeDocument.updated_at.desc(), KnowledgeDocument.id.desc()).limit(100).all()
    return KnowledgeListResponse(total=total, items=[_knowledge_item(db, row) for row in rows])


def get_knowledge_document(db: Session, document_id: int) -> KnowledgeDocumentDetail | None:
    document = db.query(KnowledgeDocument).filter(KnowledgeDocument.id == document_id).first()
    if not document:
        return None
    chunks = (
        db.query(KnowledgeChunk)
        .filter(KnowledgeChunk.document_id == document.id)
        .order_by(KnowledgeChunk.chunk_index.asc())
        .all()
    )
    item = _knowledge_item(db, document)
    return KnowledgeDocumentDetail(
        **item.model_dump(),
        content=document.content,
        chunks=chunks,
    )


def create_knowledge_document(db: Session, payload: KnowledgeDocumentCreate) -> KnowledgeDocumentDetail:
    if not payload.title.strip():
        raise ValueError("知识库标题不能为空")
    if not payload.content.strip():
        raise ValueError("知识库正文不能为空")

    document = KnowledgeDocument(
        title=payload.title.strip(),
        doc_type=payload.doc_type.strip() or "general",
        city=payload.city.strip() if payload.city else None,
        category=payload.category.strip() if payload.category else None,
        tags=_clean_str_list(payload.tags),
        source=payload.source.strip() if payload.source else None,
        content=payload.content.strip(),
        status=payload.status.strip() or "active",
    )
    db.add(document)
    db.flush()
    _replace_knowledge_chunks(db, document)
    db.commit()
    db.refresh(document)
    detail = get_knowledge_document(db, document.id)
    if not detail:
        raise ValueError("知识库资料创建失败")
    return detail


def update_knowledge_document(
    db: Session,
    document_id: int,
    payload: KnowledgeDocumentUpdate,
) -> KnowledgeDocumentDetail | None:
    document = db.query(KnowledgeDocument).filter(KnowledgeDocument.id == document_id).first()
    if not document:
        return None

    data = payload.model_dump(exclude_unset=True)
    rebuild_fields = {"title", "doc_type", "city", "category", "tags", "content"}
    should_rebuild = bool(rebuild_fields.intersection(data))

    for field, value in data.items():
        if field in {"title", "doc_type", "status"}:
            if value is None:
                continue
            value = value.strip()
        if field in {"city", "category", "source"} and isinstance(value, str):
            value = value.strip() or None
        if field == "tags":
            value = _clean_str_list(value)
        if field == "content":
            if value is not None and not value.strip():
                raise ValueError("知识库正文不能为空")
            value = value.strip() if value is not None else value
        setattr(document, field, value)

    if not document.title.strip():
        raise ValueError("知识库标题不能为空")

    document.updated_at = datetime.now(timezone.utc)
    db.flush()
    if should_rebuild:
        _replace_knowledge_chunks(db, document)
    db.commit()
    db.refresh(document)
    return get_knowledge_document(db, document.id)


def delete_knowledge_document(db: Session, document_id: int) -> bool:
    document = db.query(KnowledgeDocument).filter(KnowledgeDocument.id == document_id).first()
    if not document:
        return False
    db.query(KnowledgeChunk).filter(KnowledgeChunk.document_id == document.id).delete()
    db.delete(document)
    db.commit()
    return True


def rebuild_knowledge_document(db: Session, document_id: int) -> KnowledgeRebuildResponse | None:
    document = db.query(KnowledgeDocument).filter(KnowledgeDocument.id == document_id).first()
    if not document:
        return None
    document.updated_at = datetime.now(timezone.utc)
    count = _replace_knowledge_chunks(db, document)
    db.commit()
    return KnowledgeRebuildResponse(document_id=document.id, chunk_count=count)


def _score_knowledge_hit(
    document: KnowledgeDocument,
    chunk: KnowledgeChunk,
    terms: list[str],
    payload: KnowledgeSearchRequest,
) -> int:
    title = (document.title or "").lower()
    content = (chunk.content or "").lower()
    category = (document.category or "").lower()
    source = (document.source or "").lower()
    tag_text = " ".join(_clean_str_list(document.tags) + _clean_str_list(chunk.tags)).lower()
    keyword_text = " ".join(_clean_str_list(chunk.keywords)).lower()
    score = 0

    for term in terms:
        value = term.lower()
        if value in title:
            score += 14
        if value in keyword_text:
            score += 10
        if value in tag_text:
            score += 8
        if value in content:
            score += 6
        if value in category:
            score += 4
        if value in source:
            score += 2

    if payload.city:
        if document.city == payload.city:
            score += 10
        elif not document.city:
            score += 2
    if payload.doc_type and document.doc_type == payload.doc_type:
        score += 5
    if payload.category and document.category == payload.category:
        score += 4
    requested_tags = set(_clean_str_list(payload.tags))
    if requested_tags:
        matched_tags = requested_tags.intersection(set(_clean_str_list(document.tags)))
        score += len(matched_tags) * 6

    return score


def search_knowledge(db: Session, payload: KnowledgeSearchRequest) -> KnowledgeSearchResponse:
    terms = _split_terms(payload.query, payload.city, payload.doc_type, payload.category, " ".join(payload.tags))
    query = (
        db.query(KnowledgeChunk, KnowledgeDocument)
        .join(KnowledgeDocument, KnowledgeChunk.document_id == KnowledgeDocument.id)
        .filter(KnowledgeDocument.status == "active")
    )

    if payload.city:
        query = query.filter(
            or_(
                KnowledgeDocument.city == payload.city,
                KnowledgeDocument.city.is_(None),
                KnowledgeDocument.city == "",
            )
        )
    if payload.doc_type:
        query = query.filter(KnowledgeDocument.doc_type == payload.doc_type)
    if payload.category:
        query = query.filter(KnowledgeDocument.category == payload.category)

    if terms:
        term_filters = []
        for term in terms[:12]:
            pattern = f"%{term}%"
            term_filters.append(
                or_(
                    KnowledgeChunk.content.ilike(pattern),
                    cast(KnowledgeChunk.keywords, String).ilike(pattern),
                    cast(KnowledgeChunk.tags, String).ilike(pattern),
                    KnowledgeDocument.title.ilike(pattern),
                    KnowledgeDocument.doc_type.ilike(pattern),
                    KnowledgeDocument.city.ilike(pattern),
                    KnowledgeDocument.category.ilike(pattern),
                    cast(KnowledgeDocument.tags, String).ilike(pattern),
                    KnowledgeDocument.source.ilike(pattern),
                )
            )
        query = query.filter(or_(*term_filters))

    rows = (
        query.order_by(KnowledgeDocument.updated_at.desc(), KnowledgeChunk.chunk_index.asc())
        .limit(MAX_SEARCH_CANDIDATES)
        .all()
    )

    hits: list[KnowledgeSearchHit] = []
    for chunk, document in rows:
        score = _score_knowledge_hit(document, chunk, terms, payload)
        if terms and score <= 0:
            continue
        hits.append(
            KnowledgeSearchHit(
                chunk_id=chunk.id,
                document_id=document.id,
                title=document.title,
                doc_type=document.doc_type,
                city=document.city,
                category=document.category,
                source=document.source,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                keywords=_clean_str_list(chunk.keywords),
                tags=_clean_str_list(chunk.tags),
                score=score,
            )
        )

    hits.sort(key=lambda item: (item.score, -item.chunk_index), reverse=True)
    limited = hits[: payload.limit]
    return KnowledgeSearchResponse(total=len(hits), items=limited)


def search_knowledge_for_generation(
    db: Session,
    intent: str,
    city: str,
    content_type: str,
    limit: int = 5,
) -> list[KnowledgeSearchHit]:
    response = search_knowledge(
        db,
        KnowledgeSearchRequest(
            query=f"{intent} {city} {content_type}",
            city=city,
            limit=limit,
        ),
    )
    return response.items


def _excerpt(content: str, max_chars: int = 180) -> str:
    compact = re.sub(r"\s+", " ", content).strip()
    if len(compact) <= max_chars:
        return compact
    return f"{compact[:max_chars].rstrip()}..."


def _format_knowledge_context(hits: list[KnowledgeSearchHit]) -> str:
    if not hits:
        return ""
    lines = ["以下为内部知识库片段，请优先使用可核验事实，避免编造："]
    for index, hit in enumerate(hits, start=1):
        source = hit.source or f"knowledge:{hit.document_id}#{hit.chunk_id}"
        lines.append(
            f"[{index}] 标题：{hit.title}；城市：{hit.city or '通用'}；"
            f"来源：{source}；片段：{_excerpt(hit.content, 320)}"
        )
    return "\n".join(lines)


def _content_references(hits: list[KnowledgeSearchHit]) -> list[ContentReference]:
    return [
        ContentReference(
            document_id=hit.document_id,
            chunk_id=hit.chunk_id,
            title=hit.title,
            source=hit.source,
            excerpt=_excerpt(hit.content),
            score=hit.score,
        )
        for hit in hits
    ]


async def generate_content_item(
    db: Session,
    payload: ContentGenerateRequest,
) -> ContentGenerateResponse:
    knowledge_hits = search_knowledge_for_generation(
        db,
        payload.intent,
        payload.city,
        payload.type,
        limit=5 if payload.type == "seo" else 3,
    )
    references = _content_references(knowledge_hits)

    # Mock fallback: if knowledge search returned nothing, use mock references
    if not references and (settings.llm_mock_mode or not settings.deepseek_api_key):
        references = [
            ContentReference(
                document_id=0,
                chunk_id=0,
                title=ref["title"],
                source=ref.get("source", "internal"),
                excerpt="",
                score=ref.get("relevance", 0.9),
            )
            for ref in _mock_knowledge_references(payload.city, payload.intent)
        ]

    if payload.use_cache:
        cache_key = _content_cache_key(payload, references)
        cached = cache_get(cache_key)
        if cached:
            cached_content_id = cached.get("content_id")
            if cached_content_id and db.query(Content.id).filter(Content.id == cached_content_id).first():
                return ContentGenerateResponse(**cached)
            cache_delete(cache_key)

    intent_row = (
        db.query(Intent)
        .filter(Intent.label == payload.intent)
        .order_by(Intent.id.desc())
        .first()
    )
    intent_id = intent_row.id if intent_row else None

    model = select_model(payload.type, payload.priority)
    markdown, schema_jsonld, generation_time_ms = await generate_content(
        payload.intent,
        payload.city,
        payload.type,
        payload.priority,
        knowledge_context=_format_knowledge_context(knowledge_hits),
    )

    eeat_score, breakdown, passed, _ = evaluate_eeat(markdown)
    status = "approved" if passed else "rejected"

    content = Content(
        intent_id=intent_id,
        city=payload.city,
        type=payload.type,
        markdown=markdown,
        eeat_score=eeat_score,
        eeat_breakdown=breakdown.model_dump(),
        status=status,
        model_used=model,
        schema_jsonld=schema_jsonld,
    )
    db.add(content)
    db.commit()
    db.refresh(content)

    response = ContentGenerateResponse(
        content_id=content.id,
        markdown=markdown,
        metadata=ContentMetadata(
            eeat_score=eeat_score,
            eeat_breakdown=breakdown,
            model_used=model,
            images=[f"/media/dealer_upload/{CITY_PINYIN.get(payload.city, 'city')}_1.jpg"],
            schema_jsonld=schema_jsonld,
            generation_time_ms=generation_time_ms or int(time.time() * 1000) % 10000,
            references=references,
        ),
    )

    if payload.use_cache:
        cache_set(_content_cache_key(payload, references), response.model_dump())

    return response


def score_content(db: Session, payload: EEATScoreRequest) -> EEATScoreResponse:
    content = db.query(Content).filter(Content.id == payload.content_id).first()
    if not content:
        raise ValueError("content not found")

    eeat_score, breakdown, passed, suggestions = evaluate_eeat(payload.markdown)
    content.eeat_score = eeat_score
    content.eeat_breakdown = breakdown.model_dump()
    content.markdown = payload.markdown
    content.status = "approved" if passed else "rejected"
    db.commit()

    return EEATScoreResponse(
        content_id=payload.content_id,
        eeat_score=eeat_score,
        passed=passed,
        breakdown=breakdown,
        suggestions=suggestions,
    )
