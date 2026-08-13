import hashlib
import json

from sqlalchemy.orm import Session

from app.core.redis_client import cache_get, cache_set
from app.models import Intent
from app.schemas.intent import IntentItem, IntentRequest, IntentResponse
from app.services.llm import CITY_CODE

INTENT_TYPES = ["commercial", "informational", "transactional"]
TYPE_MAP = {
    "安装": "transactional",
    "价格": "commercial",
    "怎么选": "informational",
    "攻略": "informational",
}


def _cache_key(payload: IntentRequest) -> str:
    raw = json.dumps(payload.model_dump(), ensure_ascii=False, sort_keys=True)
    return f"intent:{hashlib.sha256(raw.encode()).hexdigest()}"


def _classify_intent(term: str) -> str:
    for key, value in TYPE_MAP.items():
        if key in term:
            return value
    return "commercial"


def _extract_label(term: str) -> str:
    cleaned = term.replace(" ", "")
    for suffix in ("安装", "价格", "攻略", "怎么选"):
        cleaned = cleaned.replace(suffix, "")
    return cleaned or term.strip()


def _priority(hotness: int, difficulty: int) -> str:
    if hotness >= 80 and difficulty <= 65:
        return "P0"
    if hotness >= 60:
        return "P1"
    return "P2"


def mine_intents(db: Session, payload: IntentRequest) -> IntentResponse:
    cache_key = _cache_key(payload)
    cached = cache_get(cache_key)
    if cached:
        return IntentResponse(**cached)

    intents: list[IntentItem] = []
    seen: set[str] = set()

    for term in payload.search_terms:
        label = _extract_label(term)
        if label in seen:
            continue
        seen.add(label)

        intent_type = _classify_intent(term)
        hotness = min(100, 60 + len(term) * 3)
        difficulty = min(100, 45 + len(label) * 4)
        priority = _priority(hotness, difficulty)
        keywords = list({label, term.replace(" ", ""), f"{label}安装", f"{label}价格"})

        city_map = {city: CITY_CODE.get(city, city[:2].upper()) for city in payload.cities}

        db_intent = Intent(
            label=label,
            intent_type=intent_type,
            city_list=payload.cities,
            keyword_json=keywords,
            hotness_score=hotness,
            difficulty_score=difficulty,
            priority=priority,
        )
        db.add(db_intent)
        db.commit()
        db.refresh(db_intent)

        intents.append(
            IntentItem(
                label=label,
                intent_type=intent_type,
                keywords=keywords[:10],
                city_map=city_map,
                hotness_score=hotness,
                difficulty_score=difficulty,
                priority=priority,
            )
        )
        if len(intents) >= payload.top_k:
            break

    response = IntentResponse(intents=intents)
    cache_set(cache_key, response.model_dump())
    return response
