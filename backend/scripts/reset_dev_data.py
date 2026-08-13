"""一键重置开发数据脚本。

用法：python -m scripts.reset_dev_data
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.database import SessionLocal, engine, Base
from app.models import (
    CallRecord, City, CityCase, CityFaq, Content, ContentTemplate,
    Dealer, Intent, KnowledgeChunk, KnowledgeDocument, Lead, Material, Publication, Store,
)
from app.models.user import User
from app.main import (
    seed_cities, seed_city_cases, seed_city_faqs, seed_contents_and_publications,
    seed_dealers, seed_knowledge, seed_leads, seed_stores, seed_users,
)


def reset_all():
    """Drop all data and re-seed."""
    print("⚠️  即将删除所有数据并重新生成开发数据...")

    db = SessionLocal()
    try:
        # Delete in reverse dependency order
        tables = [
            CallRecord, Material, Publication, Content, Lead, Dealer,
            CityFaq, CityCase, Store, City, Intent,
            KnowledgeChunk, KnowledgeDocument, ContentTemplate,
        ]
        for table in tables:
            count = db.query(table).delete()
            print(f"  删除 {table.__tablename__}: {count} 条")

        # Delete users separately (different Base)
        user_count = db.query(User).delete()
        print(f"  删除 user: {user_count} 条")

        db.commit()
        print("\n✅ 数据已清空，开始重新生成...\n")

        # Re-seed
        seed_users(db)
        seed_dealers(db)
        seed_cities(db)
        seed_stores(db)
        seed_city_cases(db)
        seed_city_faqs(db)
        seed_knowledge(db)
        seed_leads(db)
        seed_contents_and_publications(db)

        print("\n✅ 开发数据已重新生成！")
        print("\n测试账号：")
        print("  admin / admin123 (管理员)")
        print("  operator / operator123 (运营)")
        print("  dealer_gz / dealer123 (广州经销商)")
        print("  dealer_sz / dealer123 (深圳经销商)")
        print("  dealer_bj / dealer123 (北京经销商)")

    except Exception as e:
        db.rollback()
        print(f"\n❌ 重置失败: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    reset_all()
