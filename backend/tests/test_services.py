from app.services.eeat import evaluate_eeat
from app.services.llm import select_model


def test_select_model_layers():
    assert select_model("seo", "P0") == "deepseek-v4-pro"
    assert select_model("seo", "P1") == "deepseek-v4-pro"
    assert select_model("seo", "P2") == "deepseek-v4-flash"
    assert select_model("geo", "P2") == "deepseek-v4-flash"
    assert select_model("schema", "P0") == "template"


def test_eeat_gate():
    content = (
        "# 广州防盗门安装攻略\n"
        "天河区某小区业主张先生三室两厅案例。\n"
        "型材壁厚1.8mm，玻璃5+12A+5中空，五金进口品牌。\n"
        "价格具体以门店实测为准。\n"
        "作者：博雅敏格广州认证安装工程师"
    )
    score, breakdown, passed, _ = evaluate_eeat(content)
    assert score >= 70
    assert passed is True
    assert breakdown.experience >= 60
