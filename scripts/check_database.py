
from pathlib import Path
import sqlite3
import pandas as pd


# ==================================================
# 1. 数据库路径
# ==================================================

ROOT_DIR = Path(__file__).resolve().parents[1]
DB_PATH = ROOT_DIR / "data" / "database" / "beverage_agent.db"


# ==================================================
# 2. 通用检查函数
# ==================================================

def get_tables(conn):
    """获取数据库中的所有数据表。"""
    sql = """
    SELECT name
    FROM sqlite_master
    WHERE type = 'table'
    AND name NOT LIKE 'sqlite_%'
    ORDER BY name
    """
    return pd.read_sql_query(sql, conn)["name"].tolist()


def get_columns(conn, table):
    """获取指定数据表的字段。"""
    cursor = conn.execute(f'PRAGMA table_info("{table}")')
    return [row[1] for row in cursor.fetchall()]


def check_table_exists(tables, table):
    """检查数据表是否存在。"""
    return table in tables


def check_unique(conn, table, column):
    """检查指定字段是否存在重复值。"""
    sql = f"""
    SELECT COUNT(*) FROM (
        SELECT "{column}"
        FROM "{table}"
        GROUP BY "{column}"
        HAVING COUNT(*) > 1
    )
    """
    return conn.execute(sql).fetchone()[0]


def check_orphans(conn, child_table, child_column,
                  parent_table, parent_column):
    """检查子表中是否存在无法关联到父表的记录。"""
    sql = f"""
    SELECT COUNT(*)
    FROM "{child_table}" AS child
    LEFT JOIN "{parent_table}" AS parent
    ON child."{child_column}" = parent."{parent_column}"
    WHERE child."{child_column}" IS NOT NULL
    AND parent."{parent_column}" IS NULL
    """
    return conn.execute(sql).fetchone()[0]


# ==================================================
# 3. 数据库基础检查
# ==================================================

def main():

    print("=" * 65)
    print("酒水采销 Agent｜SQLite 数据库完整性检查")
    print("=" * 65)

    if not DB_PATH.exists():
        print(f"错误：找不到数据库文件：{DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)

    try:

        tables = get_tables(conn)

        print(f"\n数据库路径：{DB_PATH}")
        print(f"数据表数量：{len(tables)}")

        # ==================================================
        # 4. 数据表数量检查
        # ==================================================

        print("\n【检查1：数据表数量】")
        print("-" * 65)

        expected_tables = 18

        if len(tables) == expected_tables:
            print(f"PASS：数据表数量正确，共 {len(tables)} 张")
        else:
            print(
                f"WARNING：预期 {expected_tables} 张，"
                f"实际 {len(tables)} 张"
            )

        # ==================================================
        # 5. 各表记录数量
        # ==================================================

        print("\n【检查2：各表记录数量】")
        print("-" * 65)

        for table in tables:

            count = conn.execute(
                f'SELECT COUNT(*) FROM "{table}"'
            ).fetchone()[0]

            print(f"{table:<38} {count:>10,} 条")

        # ==================================================
        # 6. 关键字段重复检查
        # ==================================================

        print("\n【检查3：关键字段重复检查】")
        print("-" * 65)

        unique_checks = [
            ("products", "sku_id"),
            ("brands", "brand_id"),
            ("suppliers", "supplier_id"),
            ("purchase_orders", "order_id"),
            ("promotions", "promotion_id"),
        ]

        unique_results = []

        for table, column in unique_checks:

            if not check_table_exists(tables, table):
                print(f"SKIP：缺少数据表 {table}")
                continue

            columns = get_columns(conn, table)

            if column not in columns:
                print(f"SKIP：{table} 不存在字段 {column}")
                continue

            duplicate_count = check_unique(conn, table, column)

            passed = duplicate_count == 0
            unique_results.append(passed)

            status = "PASS" if passed else "FAIL"

            print(
                f"{status}：{table}.{column} "
                f"重复值数量：{duplicate_count}"
            )

        # ==================================================
        # 7. 商品关联完整性检查
        # ==================================================

        print("\n【检查4：商品关联完整性】")
        print("-" * 65)

        product_relations = [
            ("sales_daily", "sku_id"),
            ("inventory_snapshot", "sku_id"),
            ("inventory_batches", "sku_id"),
            ("purchase_order_details", "sku_id"),
            ("competitor_prices", "sku_id"),
            ("promotion_details", "sku_id"),
            ("product_supplier_mapping", "sku_id"),
        ]

        relation_results = []

        for child_table, child_column in product_relations:

            if not check_table_exists(tables, child_table):
                print(f"SKIP：缺少数据表 {child_table}")
                continue

            child_columns = get_columns(conn, child_table)
            parent_columns = get_columns(conn, "products")

            if (
                child_column not in child_columns
                or "sku_id" not in parent_columns
            ):
                print(f"SKIP：{child_table} 缺少关联字段")
                continue

            orphan_count = check_orphans(
                conn,
                child_table,
                child_column,
                "products",
                "sku_id"
            )

            passed = orphan_count == 0
            relation_results.append(passed)

            status = "PASS" if passed else "FAIL"

            print(
                f"{status}：{child_table} → products，"
                f"孤立记录：{orphan_count}"
            )

        # ==================================================
        # 8. 供应商关联完整性检查
        # ==================================================

        print("\n【检查5：供应商关联完整性】")
        print("-" * 65)

        supplier_relations = [
            ("purchase_orders", "supplier_id"),
            ("supplier_performance", "supplier_id"),
            ("supplier_ratings_v2", "supplier_id"),
            ("supplier_strategies", "supplier_id"),
            ("product_supplier_mapping", "supplier_id"),
        ]

        for child_table, child_column in supplier_relations:

            if not check_table_exists(tables, child_table):
                print(f"SKIP：缺少数据表 {child_table}")
                continue

            child_columns = get_columns(conn, child_table)
            parent_columns = get_columns(conn, "suppliers")

            if (
                child_column not in child_columns
                or "supplier_id" not in parent_columns
            ):
                print(f"SKIP：{child_table} 缺少关联字段")
                continue

            orphan_count = check_orphans(
                conn,
                child_table,
                child_column,
                "suppliers",
                "supplier_id"
            )

            passed = orphan_count == 0
            relation_results.append(passed)

            status = "PASS" if passed else "FAIL"

            print(
                f"{status}：{child_table} → suppliers，"
                f"孤立记录：{orphan_count}"
            )

        # ==================================================
        # 9. 采购订单及到货记录关联检查
        # ==================================================

        print("\n【检查6：采购订单及到货记录关联完整性】")
        print("-" * 65)

        order_relations = [
            ("purchase_order_details", "order_id"),
            ("purchase_receipts", "order_id"),
        ]

        for child_table, child_column in order_relations:

            if not check_table_exists(tables, child_table):
                print(f"SKIP：缺少数据表 {child_table}")
                continue

            child_columns = get_columns(conn, child_table)
            parent_columns = get_columns(conn, "purchase_orders")

            if (
                child_column not in child_columns
                or "order_id" not in parent_columns
            ):
                print(f"SKIP：{child_table} 缺少关联字段")
                continue

            orphan_count = check_orphans(
                conn,
                child_table,
                child_column,
                "purchase_orders",
                "order_id"
            )

            passed = orphan_count == 0
            relation_results.append(passed)

            status = "PASS" if passed else "FAIL"

            print(
                f"{status}：{child_table} → purchase_orders，"
                f"孤立记录：{orphan_count}"
            )

        # ==================================================
        # 10. 最终检查结果
        # ==================================================

        print("\n" + "=" * 65)
        print("数据库完整性检查汇总")
        print("=" * 65)

        total_checks = len(unique_results) + len(relation_results)

        passed_checks = (
            sum(unique_results) + sum(relation_results)
        )

        failed_checks = total_checks - passed_checks

        print(f"有效检查项：{total_checks}")
        print(f"通过检查项：{passed_checks}")
        print(f"未通过检查项：{failed_checks}")

        if failed_checks == 0 and total_checks > 0:
            print("\nPASS：所有已执行的完整性检查均通过！")
        else:
            print("\nWARNING：存在未通过的检查，请根据上方结果排查。")

        print("\n注意：SKIP 表示字段或数据表不存在，")
        print("不代表该项已经通过检查。")

    finally:
        conn.close()


if __name__ == "__main__":
    main()

