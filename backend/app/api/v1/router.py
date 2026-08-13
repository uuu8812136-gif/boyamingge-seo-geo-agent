from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import (
    CurrentUserProfile,
    ChangePasswordRequest,
    ROLE_ADMIN,
    ROLE_CITY_MANAGER,
    ROLE_DEALER,
    ROLE_OPERATOR,
    ROLE_STORE_MANAGER,
    RefreshTokenRequest,
    Token,
    get_current_user,
    get_password_hash,
    password_strength_error,
    login_for_access_token,
    refresh_access_token,
    require_roles,
    verify_password,
)
from app.models import City, Lead
from app.models.user import User
from app.schemas.article import ArticleDetail, ArticleListResponse, ContentDetailResponse, ContentListResponse
from app.schemas.content import (
    ContentGenerateRequest,
    ContentGenerateResponse,
    EEATScoreRequest,
    EEATScoreResponse,
)
from app.schemas.dealer import (
    ConfirmRequest,
    ConfirmResponse,
    DealerLeadListResponse,
    DealerProfile,
    DealerPublicationDetail,
    DealerPublicationListResponse,
    DealerStats,
    LeadStatusUpdateRequest,
    LeadStatusUpdateResponse,
    MaterialListResponse,
    MaterialUploadRequest,
    MaterialUploadResponse,
)
from app.schemas.hotline import HotlinePushRequest, HotlinePushResponse
from app.schemas.intent import IntentRequest, IntentResponse
from app.schemas.knowledge import (
    KnowledgeDocumentCreate,
    KnowledgeDocumentDetail,
    KnowledgeDocumentUpdate,
    KnowledgeListResponse,
    KnowledgeRebuildResponse,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
)
from app.schemas.lead import LeadListResponse, LeadSubmitRequest, LeadSubmitResponse
from app.schemas.metrics import MetricsResponse
from app.schemas.publish import (
    AssistRequest,
    AssistResponse,
    DistributeRequest,
    DistributeResponse,
    PublishRequest,
    PublishResponse,
)
from app.api.v1.cities import router as cities_router
from app.api.v1.admin_cities import router as admin_cities_router
from app.api.v1.content_posts import router as content_posts_router
from app.api.v1.content_materials import router as content_materials_router
from app.api.v1.external_accounts import router as external_accounts_router
from app.api.v1.external_publish import router as external_publish_router
from app.services.article_service import get_article, get_content_detail, list_articles, list_content
from app.services.content_service import (
    create_knowledge_document,
    delete_knowledge_document,
    generate_content_item,
    get_knowledge_document,
    list_knowledge_documents,
    rebuild_knowledge_document,
    score_content,
    search_knowledge,
    update_knowledge_document,
)
from app.services.dealer_service import (
    confirm_publication,
    get_dealer_profile,
    get_dealer_publication_detail,
    get_dealer_stats,
    list_dealer_leads,
    list_dealer_materials,
    list_dealer_publications,
    update_lead_status,
    upload_material,
    upload_material_file,
)
from app.services.distribute_service import assist_l2, distribute_l1
from app.services.hotline_service import push_hotline
from app.services.intent_service import mine_intents
from app.services.lead_service import assert_can_access_lead, list_leads, submit_lead
from app.services.metrics_service import query_metrics
from app.services.publish_service import publish_content
from fastapi.security import OAuth2PasswordRequestForm

router = APIRouter(prefix="/api/v1")
router.include_router(cities_router)
router.include_router(admin_cities_router)
router.include_router(content_posts_router)
router.include_router(content_materials_router)
router.include_router(external_accounts_router)
router.include_router(external_publish_router)


@router.post("/auth/token", response_model=Token, tags=["auth"])
async def auth_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[Session, Depends(get_db)],
):
    return await login_for_access_token(form_data, db)


@router.post("/auth/refresh", response_model=Token, tags=["auth"])
def auth_refresh(
    payload: RefreshTokenRequest,
    db: Annotated[Session, Depends(get_db)],
):
    """使用 refresh_token 换取新的 access_token + refresh_token。

    客户端在 access_token 过期（401）时，可用 refresh_token 调用此端点无感刷新。
    """
    return refresh_access_token(payload.refresh_token, db)


@router.get("/auth/me", response_model=CurrentUserProfile, tags=["auth"])
def auth_me(user: Annotated[User, Depends(get_current_user)]):
    """返回当前登录账号与权限范围，供后台按角色渲染菜单。"""
    return CurrentUserProfile.model_validate(user)


@router.post("/auth/change-password", tags=["auth"])
def auth_change_password(
    payload: ChangePasswordRequest,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    if not verify_password(payload.current_password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="当前密码不正确")
    password_error = password_strength_error(payload.new_password)
    if password_error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=password_error)
    if verify_password(payload.new_password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="新密码不能与当前密码相同")
    user.hashed_password = get_password_hash(payload.new_password)
    user.password_changed_at = datetime.now(timezone.utc)
    user.token_version = (user.token_version or 0) + 1
    db.commit()
    return {"status": "password_changed", "message": "密码已修改，请重新登录"}


@router.post("/intents", response_model=IntentResponse, tags=["intent"])
def create_intents(
    payload: IntentRequest,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(ROLE_ADMIN, ROLE_OPERATOR))],
):
    return mine_intents(db, payload)


@router.post("/content/generate", response_model=ContentGenerateResponse, tags=["content"])
async def content_generate(
    payload: ContentGenerateRequest,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(ROLE_ADMIN, ROLE_OPERATOR))],
):
    try:
        return await generate_content_item(db, payload)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.post("/content/eeat-score", response_model=EEATScoreResponse, tags=["content"])
def content_eeat_score(
    payload: EEATScoreRequest,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(ROLE_ADMIN, ROLE_OPERATOR))],
):
    try:
        return score_content(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="资源不存在") from exc


@router.post("/publish", response_model=PublishResponse, tags=["publish"])
def publish(
    payload: PublishRequest,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(ROLE_ADMIN, ROLE_OPERATOR))],
):
    return publish_content(db, payload)


@router.post("/distribute", response_model=DistributeResponse, tags=["distribute"])
def distribute(
    payload: DistributeRequest,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(ROLE_ADMIN, ROLE_OPERATOR, ROLE_DEALER))],
):
    return distribute_l1(db, payload)


@router.post("/distribute/assist", response_model=AssistResponse, tags=["distribute"])
def distribute_assist(
    payload: AssistRequest,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(ROLE_ADMIN, ROLE_OPERATOR, ROLE_DEALER))],
):
    return assist_l2(db, payload)


@router.post("/hotline/push", response_model=HotlinePushResponse, tags=["hotline"])
def hotline_push(
    payload: HotlinePushRequest,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    return push_hotline(db, payload)


@router.get("/metrics", response_model=MetricsResponse, tags=["metrics"])
def metrics(
    city: Annotated[str, Query()],
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_roles(ROLE_ADMIN, ROLE_OPERATOR, ROLE_CITY_MANAGER))],
    date_from: Annotated[str | None, Query()] = None,
    date_to: Annotated[str | None, Query()] = None,
    metric_type: Annotated[str | None, Query(pattern="^(rank|traffic|lead|cost)$")] = None,
):
    if user.role == ROLE_CITY_MANAGER:
        city_row = db.query(City).filter(City.name == city).first()
        if not city_row or city_row.id != user.city_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权查看其它城市指标")
    return query_metrics(db, city, date_from, date_to, metric_type)


@router.get("/articles", response_model=ArticleListResponse, tags=["articles"])
def articles_list(
    db: Annotated[Session, Depends(get_db)],
    city: Annotated[str | None, Query()] = None,
    tag: Annotated[str | None, Query()] = None,
):
    return list_articles(db, city, tag)


@router.get("/articles/{slug}", response_model=ArticleDetail, tags=["articles"])
def articles_detail(slug: str, db: Annotated[Session, Depends(get_db)]):
    article = get_article(db, slug)
    if not article:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文章不存在")
    return article


@router.get("/content", response_model=ContentListResponse, tags=["content"])
def content_list(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(ROLE_ADMIN, ROLE_OPERATOR))],
    city: Annotated[str | None, Query()] = None,
    status: Annotated[str | None, Query()] = None,
):
    return list_content(db, city, status)


@router.get("/content/{content_id}", response_model=ContentDetailResponse, tags=["content"])
def content_detail(
    content_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(ROLE_ADMIN, ROLE_OPERATOR))],
):
    detail = get_content_detail(db, content_id)
    if not detail:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="内容不存在")
    return detail


@router.get("/knowledge", response_model=KnowledgeListResponse, tags=["knowledge"])
def knowledge_list(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(ROLE_ADMIN, ROLE_OPERATOR))],
    city: Annotated[str | None, Query()] = None,
    status: Annotated[str | None, Query()] = None,
    doc_type: Annotated[str | None, Query()] = None,
):
    return list_knowledge_documents(db, city=city, status=status, doc_type=doc_type)


@router.post("/knowledge", response_model=KnowledgeDocumentDetail, tags=["knowledge"])
def knowledge_create(
    payload: KnowledgeDocumentCreate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(ROLE_ADMIN, ROLE_OPERATOR))],
):
    try:
        return create_knowledge_document(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/knowledge/search", response_model=KnowledgeSearchResponse, tags=["knowledge"])
def knowledge_search(
    payload: KnowledgeSearchRequest,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(ROLE_ADMIN, ROLE_OPERATOR))],
):
    return search_knowledge(db, payload)


@router.get("/knowledge/{document_id}", response_model=KnowledgeDocumentDetail, tags=["knowledge"])
def knowledge_detail(
    document_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(ROLE_ADMIN, ROLE_OPERATOR))],
):
    detail = get_knowledge_document(db, document_id)
    if not detail:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="知识库资料不存在")
    return detail


@router.patch("/knowledge/{document_id}", response_model=KnowledgeDocumentDetail, tags=["knowledge"])
def knowledge_update(
    document_id: int,
    payload: KnowledgeDocumentUpdate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(ROLE_ADMIN, ROLE_OPERATOR))],
):
    try:
        detail = update_knowledge_document(db, document_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if not detail:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="知识库资料不存在")
    return detail


@router.delete("/knowledge/{document_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["knowledge"])
def knowledge_delete(
    document_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(ROLE_ADMIN, ROLE_OPERATOR))],
):
    if not delete_knowledge_document(db, document_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="知识库资料不存在")
    return None


@router.post("/knowledge/{document_id}/rebuild", response_model=KnowledgeRebuildResponse, tags=["knowledge"])
def knowledge_rebuild(
    document_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(ROLE_ADMIN, ROLE_OPERATOR))],
):
    try:
        result = rebuild_knowledge_document(db, document_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="知识库资料不存在")
    return result


@router.post("/leads", response_model=LeadSubmitResponse, tags=["leads"])
def leads_submit(
    payload: LeadSubmitRequest,
    db: Annotated[Session, Depends(get_db)],
):
    return submit_lead(db, payload)


@router.get("/leads", response_model=LeadListResponse, tags=["leads"])
def leads_list(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_roles(ROLE_ADMIN, ROLE_OPERATOR, ROLE_CITY_MANAGER, ROLE_STORE_MANAGER))],
    city: Annotated[str | None, Query()] = None,
    status: Annotated[str | None, Query()] = None,
):
    return list_leads(db, city, status, user=user)


@router.patch("/leads/{lead_id}/status", response_model=LeadStatusUpdateResponse, tags=["leads"])
def admin_update_lead_status(
    lead_id: int,
    payload: LeadStatusUpdateRequest,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_roles(ROLE_ADMIN, ROLE_OPERATOR, ROLE_CITY_MANAGER, ROLE_STORE_MANAGER))],
):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="线索不存在")
    assert_can_access_lead(db, user, lead)
    lead.status = payload.status
    db.commit()
    return LeadStatusUpdateResponse(lead_id=lead.id, status=lead.status, message="状态已更新")


# ── 经销商工作台 ──────────────────────────────────────────────


def _dealer_code(user: User) -> str:
    if not user.dealer_code:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="非经销商账号")
    return user.dealer_code


@router.get("/dealer/profile", response_model=DealerProfile, tags=["dealer"])
def dealer_profile(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_roles(ROLE_DEALER))],
):
    code = _dealer_code(user)
    profile = get_dealer_profile(db, code)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="经销商信息不存在")
    return profile


@router.get("/dealer/stats", response_model=DealerStats, tags=["dealer"])
def dealer_stats(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_roles(ROLE_DEALER))],
):
    return get_dealer_stats(db, _dealer_code(user))


@router.get("/dealer/publications", response_model=DealerPublicationListResponse, tags=["dealer"])
def dealer_publications(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_roles(ROLE_DEALER))],
    status: Annotated[str | None, Query()] = None,
):
    return list_dealer_publications(db, _dealer_code(user), status)


@router.get("/dealer/publications/{publication_id}", response_model=DealerPublicationDetail, tags=["dealer"])
def dealer_publication_detail(
    publication_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_roles(ROLE_DEALER))],
):
    detail = get_dealer_publication_detail(db, _dealer_code(user), publication_id)
    if not detail:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="内容不存在或无权查看")
    return detail


@router.post("/dealer/publications/{publication_id}/confirm", response_model=ConfirmResponse, tags=["dealer"])
def dealer_confirm(
    publication_id: int,
    payload: ConfirmRequest,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_roles(ROLE_DEALER))],
):
    try:
        return confirm_publication(db, _dealer_code(user), publication_id, payload.action)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/dealer/materials", response_model=MaterialUploadResponse, tags=["dealer"])
def dealer_upload_material(
    payload: MaterialUploadRequest,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_roles(ROLE_DEALER))],
):
    return upload_material(db, _dealer_code(user), payload)


@router.post("/dealer/materials/upload", response_model=MaterialUploadResponse, tags=["dealer"])
def dealer_upload_material_file(
    file: UploadFile,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_roles(ROLE_DEALER))],
):
    return upload_material_file(db, _dealer_code(user), file)


@router.get("/dealer/materials", response_model=MaterialListResponse, tags=["dealer"])
def dealer_materials(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_roles(ROLE_DEALER))],
):
    return list_dealer_materials(db, _dealer_code(user))


@router.get("/dealer/leads", response_model=DealerLeadListResponse, tags=["dealer"])
def dealer_leads(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_roles(ROLE_DEALER))],
):
    return list_dealer_leads(db, _dealer_code(user))


@router.patch("/dealer/leads/{lead_id}", response_model=LeadStatusUpdateResponse, tags=["dealer"])
def dealer_update_lead(
    lead_id: int,
    payload: LeadStatusUpdateRequest,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_roles(ROLE_DEALER))],
):
    try:
        lead = update_lead_status(db, _dealer_code(user), lead_id, payload.status)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return LeadStatusUpdateResponse(lead_id=lead.id, status=lead.status, message="状态已更新")
