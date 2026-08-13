import re

from app.core.config import get_settings
from app.schemas.content import EEATBreakdown

settings = get_settings()

AD_LAW_PATTERNS = [
    r"最好",
    r"第一",
    r"唯一",
    r"国家级",
    r"100%有效",
]


def score_experience(content: str) -> int:
    case_patterns = [r"业主", r"小区", r"案例", r"户型", r"张先生", r"李女士"]
    hits = sum(1 for p in case_patterns if re.search(p, content))
    return min(100, 50 + hits * 10)


def score_expertise(content: str) -> int:
    param_patterns = [r"\d+\.?\d*mm", r"中空", r"五金", r"型材", r"玻璃", r"壁厚"]
    hits = sum(1 for p in param_patterns if re.search(p, content))
    return min(100, 40 + hits * 12)


def score_authority(content: str, metadata: dict | None = None) -> int:
    if re.search(r"作者|工程师|认证|博雅敏格", content):
        return 70
    if metadata and metadata.get("author"):
        return 65
    return 45


def score_trust(content: str) -> int:
    score = 75
    for pattern in AD_LAW_PATTERNS:
        if re.search(pattern, content):
            score -= 15
    if "具体以门店实测为准" in content or "价格" in content:
        score += 10
    return max(0, min(100, score))


def weighted_avg(experience: int, expertise: int, authority: int, trust: int) -> int:
    total = experience * 0.25 + expertise * 0.25 + authority * 0.2 + trust * 0.3
    return int(round(total))


def evaluate_eeat(content: str, metadata: dict | None = None) -> tuple[int, EEATBreakdown, bool, list[str]]:
    scenario = settings.mock_scenario

    # Scenario: content_violation — 模拟内容违规（EEAT 极低分）
    if scenario == "content_violation":
        breakdown = EEATBreakdown(experience=10, expertise=15, authoritativeness=10, trustworthiness=5)
        return 10, breakdown, False, ["模拟内容违规：包含敏感信息，EEAT 评分极低"]

    # Scenario: empty — 模拟空内容
    if scenario == "empty" and not content.strip():
        breakdown = EEATBreakdown(experience=0, expertise=0, authoritativeness=0, trustworthiness=0)
        return 0, breakdown, False, ["内容为空"]

    experience = score_experience(content)
    expertise = score_expertise(content)
    authority = score_authority(content, metadata)
    trust = score_trust(content)
    breakdown = EEATBreakdown(
        experience=experience,
        expertise=expertise,
        authoritativeness=authority,
        trustworthiness=trust,
    )
    total = weighted_avg(experience, expertise, authority, trust)
    passed = total >= settings.eeat_threshold

    suggestions: list[str] = []
    if experience < 60:
        suggestions.append("增加 1 个本地真实案例以提升经验维度")
    if expertise < 60:
        suggestions.append("补充至少 3 个具体产品参数以提升专业维度")
    if authority < 50:
        suggestions.append("标注作者身份以提升权威维度")
    if trust < 70:
        suggestions.append("补充价格标注并规避广告法敏感词以提升可信维度")
    if not passed:
        suggestions.append(f"综合评分低于 {settings.eeat_threshold}，稿件已标记 rejected")

    return total, breakdown, passed, suggestions
