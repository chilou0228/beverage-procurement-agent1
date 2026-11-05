from pathlib import Path
import sqlite3
import sys

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR / "data" / "database" / "beverage_agent.db"

REQUIRED_TABLES = {
    "products",
    "sales_daily",
    "inventory_snapshot",
    "inventory_batches",
    "purchase_orders",
    "purchase_order_details",
    "purchase_receipts",
    "suppliers",
    "supplier_ratings_v2",
    "supplier_strategies",
    "product_supplier_mapping",
    "backup_supplier_recommendations",
    "competitor_prices",
    "promotions",
    "promotion_details",
}


def main():
    print("=" * 65)
    print("酒水采销 Agent｜Demo 上线前检查")
    print("=" * 65)

    errors = []

    if not DB_PATH.exists():
        print(f"FAIL：数据库不存在：{DB_PATH}")
        sys.exit(1)

    with sqlite3.connect(DB_PATH) as conn:

        tables = pd.read_sql_query(
            """
            SELECT name
            FROM sqlite_master
            WHERE type='table'
            """,
            conn
        )["name"].tolist()

        missing = REQUIRED_TABLES - set(tables)

        if missing:
            print(f"FAIL：缺失数据表：{sorted(missing)}")
            errors.append("数据库表完整性")
        else:
            print(
                f"PASS：必要数据表完整，共{len(REQUIRED_TABLES)}张"
            )

        for table in sorted(REQUIRED_TABLES):
            if table not in tables:
                continue

            count = pd.read_sql_query(
                f'SELECT COUNT(*) AS n FROM "{table}"',
                conn
            )["n"].iloc[0]

            print(f"PASS：{table}，记录数：{count}")

            if count == 0:
                errors.append(f"{table}为空")

    try:
        sys.path.insert(0, str(BASE_DIR))

        from src.agent.agent import (
            get_business_overview,
            get_category_analysis,
            get_inventory_risks,
            get_supplier_analysis,
            get_competitor_analysis,
            get_procurement_plan,
            get_promotion_analysis,
            diagnose_product,
            simulate_promotion,
            ask_agent,
        )

        print("\n【业务工具检查】")

        tests = [
            ("经营总览", get_business_overview),
            ("品类分析", get_category_analysis),
            ("库存风险", get_inventory_risks),
            ("供应商分析", get_supplier_analysis),
            ("竞品分析", get_competitor_analysis),
            ("采购建议", get_procurement_plan),
            ("促销分析", get_promotion_analysis),
        ]

        for name, function in tests:
            try:
                result = function()

                if result is None:
                    raise ValueError("函数返回空结果")

                print(f"PASS：{name}")

            except Exception as exc:
                print(f"FAIL：{name}：{exc}")
                errors.append(name)

        try:
            products = pd.read_sql_query(
                "SELECT sku_id FROM products LIMIT 1",
                sqlite3.connect(DB_PATH)
            )

            sku = products.iloc[0]["sku_id"]

            result = diagnose_product(sku)

            if "error" in result:
                raise ValueError(result["error"])

            print("PASS：单SKU诊断")

        except Exception as exc:
            print(f"FAIL：单SKU诊断：{exc}")
            errors.append("单SKU诊断")

        try:
            products = pd.read_sql_query(
                """
                SELECT sku_id
                FROM products
                LIMIT 1
                """,
                sqlite3.connect(DB_PATH)
            )

            sku = products.iloc[0]["sku_id"]

            result = simulate_promotion(
                sku,
                0.85
            )

            if "error" in result:
                raise ValueError(result["error"])

            print("PASS：促销方案模拟")

        except Exception as exc:
            print(f"FAIL：促销方案模拟：{exc}")
            errors.append("促销方案模拟")

        try:
            result = ask_agent(
                "最近30天经营情况怎么样？"
            )

            if not result.get("answer"):
                raise ValueError("Agent未返回回答")

            print("PASS：Agent基础问答")

        except Exception as exc:
            print(f"FAIL：Agent基础问答：{exc}")
            errors.append("Agent基础问答")

    except Exception as exc:
        print(f"FAIL：业务模块导入失败：{exc}")
        errors.append("业务模块导入")

    print("\n" + "=" * 65)
    print("检查汇总")
    print("=" * 65)

    if errors:
        print(f"异常项目：{len(errors)}")

        for error in errors:
            print(f"- {error}")

        print("FAIL：Demo尚未通过全部检查。")
        sys.exit(1)

    print("PASS：Demo基础检查全部通过！")


if __name__ == "__main__":
    main()