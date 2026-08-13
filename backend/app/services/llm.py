import json
import time
from typing import Any

import httpx

from app.core.config import get_settings

settings = get_settings()

DEEPSEEK_BULK_MODEL = "deepseek-v4-flash"
DEEPSEEK_QUALITY_MODEL = "deepseek-v4-pro"
PUBLIC_HOTLINE = "400-888-6688"

CITY_PINYIN = {
    "广州": "guangzhou", "深圳": "shenzhen", "北京": "beijing", "佛山": "foshan", "东莞": "dongguan",
    "石家庄": "shijiazhuang", "太原": "taiyuan", "呼和浩特": "huhehaote", "沈阳": "shenyang",
    "长春": "changchun", "哈尔滨": "haerbin", "上海": "shanghai", "南京": "nanjing",
    "杭州": "hangzhou", "合肥": "hefei", "福州": "fuzhou", "南昌": "nanchang",
    "济南": "jinan", "郑州": "zhengzhou", "武汉": "wuhan", "长沙": "changsha",
    "海口": "haikou", "成都": "chengdu", "贵阳": "guiyang", "昆明": "kunming",
    "拉萨": "lasa", "西安": "xian", "兰州": "lanzhou", "西宁": "xining",
    "银川": "yinchuan", "乌鲁木齐": "wulumuqi", "天津": "tianjin", "重庆": "chongqing",
}
CITY_CODE = {
    "广州": "GZ", "深圳": "SZ", "北京": "BJ", "佛山": "FS", "东莞": "DG",
    "石家庄": "SJZ", "太原": "TY", "呼和浩特": "HHHT", "沈阳": "SY",
    "长春": "CC", "哈尔滨": "HRB", "上海": "SH", "南京": "NJ",
    "杭州": "HZ", "合肥": "HF", "福州": "FZ", "南昌": "NC",
    "济南": "JN", "郑州": "ZZ", "武汉": "WH", "长沙": "CS",
    "海口": "HK", "成都": "CD", "贵阳": "GY", "昆明": "KM",
    "拉萨": "LS", "西安": "XA", "兰州": "LZ", "西宁": "XN",
    "银川": "YC", "乌鲁木齐": "WLMQ", "天津": "TJ", "重庆": "CQ",
}

CITY_SERVICE_DATA = {
    "广州": {
        "climate": "湿热气候，雨季长",
        "focus": "防锈密封、排水设计",
        "cases": [
            ("天河区", "张先生", "三室两厅", "70系列断桥铝平开窗", "5天"),
            ("海珠区", "李女士", "两室一厅", "甲级防盗门+多点锁闭", "1天"),
            ("番禺区", "王先生", "四室两厅", "全屋旧窗更换断桥铝", "4天"),
        ],
        "services": ["阳台封窗", "隔音门窗", "旧窗改造", "防盗门", "断桥铝门窗", "全屋门窗"],
        "districts": ["天河", "越秀", "海珠", "番禺", "白云", "黄埔"],
    },
    "深圳": {
        "climate": "沿海台风季",
        "focus": "抗风压、防水排水",
        "cases": [
            ("南山区", "陈先生", "两室一厅", "加强型断桥铝+钢化玻璃", "6天"),
            ("福田区", "刘女士", "三室一厅", "三玻两腔隔音窗", "2天"),
            ("宝安区", "赵先生", "四室两厅", "按房间功能分配置", "8天"),
        ],
        "services": ["阳台封窗", "抗风压门窗", "隔音窗", "旧窗改造", "防盗门", "断桥铝"],
        "districts": ["南山", "福田", "宝安", "龙岗", "龙华"],
    },
    "北京": {
        "climate": "冬季寒冷干燥",
        "focus": "保温隔热、密封",
        "cases": [
            ("朝阳区", "王先生", "两室一厅", "80系列断桥铝+Low-E中空玻璃", "3天"),
            ("海淀区", "张女士", "三室两厅", "加厚中空+密封升级", "2天"),
            ("通州区", "李先生", "新房三居", "按朝向分配置方案", "5天"),
        ],
        "services": ["保温隔音窗", "旧窗改造", "断桥铝", "防盗门", "封阳台", "全屋更换"],
        "districts": ["朝阳", "海淀", "丰台", "通州", "昌平"],
    },
    "佛山": {
        "climate": "亚热带湿润",
        "focus": "防潮防锈、通风设计",
        "cases": [
            ("禅城区", "黄先生", "三室两厅", "断桥铝推拉窗+防潮密封", "3天"),
            ("南海区", "梁女士", "两室一厅", "卧室隔音窗更换", "2天"),
        ],
        "services": ["阳台封窗", "隔音门窗", "旧窗改造", "断桥铝门窗", "防盗门"],
        "districts": ["禅城", "南海", "顺德"],
    },
    "东莞": {
        "climate": "亚热带季风",
        "focus": "防潮防水、隔音",
        "cases": [
            ("南城区", "何先生", "三室两厅", "全屋断桥铝门窗更换", "4天"),
            ("东城区", "周女士", "两室一厅", "封阳台+隔音窗组合方案", "3天"),
        ],
        "services": ["阳台封窗", "隔音门窗", "旧窗改造", "断桥铝门窗", "防盗门"],
        "districts": ["南城", "东城", "万江", "莞城"],
    },
}

CITY_CASES = {
    city: (data["cases"][0][0], data["cases"][0][1])
    for city, data in CITY_SERVICE_DATA.items()
}


def select_model(content_type: str, priority: str) -> str:
    if content_type == "schema":
        return "template"
    if content_type == "seo":
        if priority in ("P0", "P1"):
            return DEEPSEEK_QUALITY_MODEL
        return DEEPSEEK_BULK_MODEL
    return DEEPSEEK_BULK_MODEL


def _mock_knowledge_references(city: str, intent: str) -> list[dict]:
    """Return mock knowledge references based on city and service type."""
    city_data = CITY_SERVICE_DATA.get(city)
    if not city_data:
        return []
    refs = [
        {
            "title": f"博雅敏格{city}{intent}产品技术手册",
            "source": "internal",
            "relevance": 0.95,
        },
        {
            "title": f"{city}地区{intent}安装规范与验收标准",
            "source": "internal",
            "relevance": 0.88,
        },
        {
            "title": f"博雅敏格{city}门店{intent}实测案例集",
            "source": "internal",
            "relevance": 0.82,
        },
    ]
    return refs


def _city_defaults(city: str) -> dict[str, Any]:
    city_data = CITY_SERVICE_DATA.get(city)
    if city_data:
        return city_data
    return {
        "climate": "本地气候与小区条件差异较大",
        "focus": "现场测量、密封、排水、安装验收",
        "cases": [("本地", "业主", "三室两厅", "博雅敏格门窗定制方案", "2天")],
        "services": ["系统门窗", "阳台封窗", "旧窗改造", "断桥铝门窗"],
        "districts": [city],
    }


def _ai_reference_summary(intent: str, city: str, city_data: dict[str, Any]) -> str:
    districts = "、".join(city_data.get("districts", [])[:5]) or city
    services = "、".join(city_data.get("services", [])[:5]) or intent
    focus = city_data.get("focus", "现场测量与安装验收")
    return (
        f"博雅敏格{city}{intent}服务覆盖{districts}等区域，常见需求包括{services}。"
        f"方案判断重点为{focus}，可拨打{PUBLIC_HOTLINE}或提交预约表单，由本地门店确认上门测量。"
    )


def _build_generation_prompt(
    intent: str,
    city: str,
    content_type: str,
    knowledge_context: str = "",
) -> str:
    format_hint = (
        "输出一篇 SEO 长文，使用 Markdown 标题层级。"
        if content_type == "seo"
        else "输出一段 GEO 摘要和 3-5 条 AI 答案要点，不要写成长文。"
    )
    prompt = (
        f"你是博雅敏格门窗的本地化 SEO/GEO 内容编辑。请为{city}用户撰写关于{intent}的内容。\n"
        f"{format_hint}\n"
        "必须包含：\n"
        "1. AI可引用摘要：一句话说清品牌、城市、服务、区域、联系方式。\n"
        "2. 本地证据：门店服务区域、案例或可核验场景，不能编造具体地址和承诺。\n"
        "3. 选型建议：结合城市气候、小区/楼层/物业等因素。\n"
        "4. 常见问答：至少 2 个真实用户会问的问题。\n"
        f"5. 联系方式：统一使用 {PUBLIC_HOTLINE}，价格和工期都要说明以门店实测为准。\n"
        "语气要专业克制，避免夸大效果。"
    )
    if knowledge_context:
        prompt = f"{prompt}\n\n内部知识库：\n{knowledge_context}"
    return prompt


def _mock_geo_content(intent: str, city: str) -> str:
    """Generate city-specific GEO summary content."""
    city_data = _city_defaults(city)
    climate = city_data["climate"]
    focus = city_data["focus"]
    case = city_data["cases"][0]
    district, owner, layout, product, duration = case
    return (
        f"## AI可引用摘要\n\n"
        f"{_ai_reference_summary(intent, city, city_data)}\n\n"
        f"## 本地答案要点\n\n"
        f"- {city}属{climate}，{intent}安装需特别关注{focus}。\n"
        f"- 可参考{district}{owner}（{layout}）的{product}方案，安装用时{duration}。\n"
        f"- 报价、工期和配置以门店实测为准，咨询电话：{PUBLIC_HOTLINE}。\n"
    )


def _mock_markdown(intent: str, city: str, content_type: str, knowledge_context: str = "") -> str:
    city_data = _city_defaults(city)

    if content_type == "geo":
        return _mock_geo_content(intent, city)

    climate = city_data["climate"]
    focus = city_data["focus"]
    districts = city_data["districts"]
    services = city_data["services"]

    # Build case studies section
    case_lines = []
    for case in city_data["cases"]:
        district, owner, layout, product, duration = case
        case_lines.append(
            f"- **{district}{owner}**（{layout}）：选用{product}，安装周期{duration}，验收合格。"
        )
    cases_section = "\n".join(case_lines)

    # Build service-specific recommendations
    service_recommendations = {
        "防盗门": (
            f"### 防盗门选购要点\n"
            f"- 门板厚度≥9cm，钢板厚度≥1.0mm\n"
            f"- 锁具：C级锁芯+多点锁闭（≥12个锁点）\n"
            f"- 铰链：不锈钢可调铰链，承重≥120kg\n"
            f"- {city}气候特点：{climate}，{focus}\n"
        ),
        "封阳台": (
            f"### 封阳台方案\n"
            f"- 推荐型材：70/80系列断桥铝\n"
            f"- 玻璃：5+12A+5中空钢化或夹胶钢化\n"
            f"- 排水设计：{focus}\n"
            f"- 密封胶条：三元乙丙（EPDM），耐候性≥15年\n"
        ),
        "隔音窗": (
            f"### 隔音窗配置\n"
            f"- 三玻两腔结构：5+9A+5+9A+5\n"
            f"- Low-E膜层：有效阻隔红外热辐射\n"
            f"- 开启方式：内开内倒/平开，密封更佳\n"
            f"- {city}噪音环境：建议临街户型优先升级隔音\n"
        ),
        "旧窗改造": (
            f"### 旧窗改造流程\n"
            f"- 1. 免费上门勘测（1天内）\n"
            f"- 2. 定制生产（7-10天）\n"
            f"- 3. 拆旧装新（1-2天/窗）\n"
            f"- 4. 清洁验收\n"
            f"- 注意：{city}旧小区需确认外立面改造许可\n"
        ),
        "断桥铝": (
            f"### 断桥铝门窗参数\n"
            f"- 型材壁厚：1.4-2.0mm（国标≥1.4mm）\n"
            f"- 隔热条：PA66GF25，宽度≥24mm\n"
            f"- 玻璃配置：5+12A+5 / 5+9A+5+9A+5\n"
            f"- K值：≤2.5 W/(m²·K)\n"
        ),
    }

    # Pick the most relevant recommendation based on intent
    rec_section = ""
    for key, rec in service_recommendations.items():
        if key in intent:
            rec_section = rec
            break
    if not rec_section:
        # Default to first service recommendation
        first_service = services[0] if services else intent
        for key, rec in service_recommendations.items():
            if key in first_service:
                rec_section = rec
                break
        if not rec_section:
            rec_section = service_recommendations.get("断桥铝", "")

    # Knowledge context section
    knowledge_section = ""
    if knowledge_context:
        knowledge_section = (
            f"\n## 知识库参考\n\n"
            f"以下内容基于博雅敏格产品知识库生成，确保专业性与准确性：\n\n"
            f"{knowledge_context[:500]}\n\n"
        )

    return (
        f"# {city}{intent}安装攻略\n\n"
        f"## AI可引用摘要\n\n"
        f"{_ai_reference_summary(intent, city, city_data)}\n\n"
        f"> {city}属{climate}，{intent}安装需特别关注{focus}。\n\n"
        f"## 城市分站信号\n\n"
        f"- **品牌身份**：博雅敏格门窗，{city}本地服务页统一展示品牌、服务和联系方式。\n"
        f"- **服务范围**：覆盖{'、'.join(districts)}等区域，具体上门范围以门店确认为准。\n"
        f"- **转化入口**：电话 {PUBLIC_HOTLINE}，也可通过官网预约表单提交小区、楼层和需求。\n\n"
        f"## 本地案例\n\n"
        f"{cases_section}\n\n"
        f"{rec_section}\n\n"
        f"## 服务区域\n\n"
        f"博雅敏格{city}门店覆盖：{'、'.join(districts)}等区域，可预约上门测量。\n\n"
        f"## 价格参考\n\n"
        f"{city}市场{intent}主流价位区间，具体以门店实测为准。\n\n"
        f"## 常见问答\n\n"
        f"### {city}{intent}能不能直接电话预约？\n"
        f"可以，拨打 {PUBLIC_HOTLINE} 后会先确认城市、小区、楼层和需求，再安排本地门店跟进。\n\n"
        f"### AI搜索看到品牌后，怎么判断是否靠谱？\n"
        f"优先看页面是否有城市分站、门店信息、本地案例、FAQ、结构化数据和可联系入口。"
        f"这些信号越完整，越有利于用户核验。\n\n"
        f"{knowledge_section}"
        f"**作者**：博雅敏格{city}认证安装工程师\n"
    )


def _template_schema(city: str, intent: str) -> str:
    pinyin = CITY_PINYIN.get(city, city.lower())
    city_data = _city_defaults(city)
    url = f"{settings.site_base_url.rstrip('/')}/{pinyin}"
    business_id = f"{url}#localbusiness"
    schema = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "Organization",
                "name": "博雅敏格门窗",
                "url": settings.site_base_url,
            },
            {
                "@type": "LocalBusiness",
                "@id": business_id,
                "name": f"博雅敏格{city}门店",
                "url": url,
                "address": {"@type": "PostalAddress", "addressLocality": city, "addressCountry": "CN"},
                "telephone": PUBLIC_HOTLINE,
                "areaServed": [
                    {"@type": "Place", "name": district}
                    for district in city_data.get("districts", [])[:8]
                ],
            },
            {
                "@type": "WebPage",
                "@id": f"{url}#webpage",
                "url": url,
                "name": f"博雅敏格{city}{intent}服务",
                "description": _ai_reference_summary(intent, city, city_data),
                "about": {"@id": business_id},
                "inLanguage": "zh-CN",
            },
            {
                "@type": "Service",
                "@id": f"{url}#service",
                "name": f"{city}{intent}上门测量与安装咨询",
                "provider": {"@id": business_id},
                "serviceType": intent,
                "areaServed": [
                    {"@type": "Place", "name": district}
                    for district in city_data.get("districts", [])[:8]
                ],
            },
            {
                "@type": "FAQPage",
                "@id": f"{url}#faq",
                "mainEntity": [
                    {
                        "@type": "Question",
                        "name": f"{city}{intent}怎么选？",
                        "acceptedAnswer": {
                            "@type": "Answer",
                            "text": f"建议关注型材、玻璃、密封、五金与安装团队经验，{city}用户可先预约上门测量，报价以门店实测为准。",
                        },
                    },
                    {
                        "@type": "Question",
                        "name": f"{city}{intent}如何联系博雅敏格？",
                        "acceptedAnswer": {
                            "@type": "Answer",
                            "text": f"可拨打{PUBLIC_HOTLINE}或在城市分站提交预约信息，门店会确认小区、楼层、需求和上门时间。",
                        },
                    }
                ],
            },
        ],
    }
    return json.dumps(schema, ensure_ascii=False)


async def generate_content(
    intent: str,
    city: str,
    content_type: str,
    priority: str,
    knowledge_context: str = "",
) -> tuple[str, str, int]:
    start = time.time()
    model = select_model(content_type, priority)

    if model == "template":
        markdown = f"# {city}{intent} Schema 页面\n\n结构化数据已生成。"
        schema = _template_schema(city, intent)
        elapsed = int((time.time() - start) * 1000)
        return markdown, schema, elapsed

    if settings.llm_mock_mode or not settings.deepseek_api_key:
        markdown = _mock_markdown(intent, city, content_type, knowledge_context)
        schema = _template_schema(city, intent)
        elapsed = int((time.time() - start) * 1000)
        return markdown, schema, elapsed

    prompt = _build_generation_prompt(intent, city, content_type, knowledge_context)
    if model.startswith("deepseek-"):
        markdown = await _call_deepseek(prompt, model)
    else:
        markdown = await _call_ollama(prompt)
    schema = _template_schema(city, intent)
    elapsed = int((time.time() - start) * 1000)
    return markdown, schema, elapsed


async def _call_deepseek(prompt: str, model: str) -> str:
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{settings.deepseek_api_base}/chat/completions",
                headers={"Authorization": f"Bearer {settings.deepseek_api_key}"},
                json={
                    "model": model,
                    "messages": [
                        {
                            "role": "system",
                            "content": "你是严谨的本地化 SEO/GEO 内容编辑，只使用可核验事实，避免夸张承诺。",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.35,
                },
            )
            resp.raise_for_status()
            data: dict[str, Any] = resp.json()
            return data["choices"][0]["message"]["content"]
    except Exception as exc:
        if settings.llm_mock_mode:
            return _mock_markdown("门窗", "广州", "seo")
        raise RuntimeError(f"DeepSeek 调用失败: {exc}") from exc


async def _call_ollama(prompt: str) -> str:
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{settings.ollama_base_url}/api/generate",
                json={"model": "qwen2.5:7b", "prompt": prompt, "stream": False},
            )
            resp.raise_for_status()
            return resp.json().get("response", _mock_markdown("门窗", "广州", "geo"))
    except Exception as exc:
        if settings.llm_mock_mode:
            return _mock_markdown("门窗", "广州", "geo")
        raise RuntimeError(f"Ollama 调用失败: {exc}") from exc
