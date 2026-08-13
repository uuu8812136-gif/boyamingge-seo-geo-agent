from pydantic import BaseModel


class PublishRequest(BaseModel):
    content_id: int
    target: str = "website"
    schedule_at: str | None = None


class PublishResponse(BaseModel):
    status: str
    url: str
    published_at: str


class DistributeRequest(BaseModel):
    content_id: int
    platforms: list[str]
    dealer_id: str


class DistributeTask(BaseModel):
    platform: str
    status: str
    confirm_url: str | None = None
    expires_at: str
    demo: bool = False


class DistributeResponse(BaseModel):
    tasks: list[DistributeTask]


class AssistPackageContent(BaseModel):
    title: str
    body: str
    images: list[str]


class AssistPackage(BaseModel):
    platform: str
    download_url: str | None = None
    content: AssistPackageContent
    demo: bool = False


class AssistRequest(BaseModel):
    content_id: int
    platforms: list[str]


class AssistResponse(BaseModel):
    packages: list[AssistPackage]
