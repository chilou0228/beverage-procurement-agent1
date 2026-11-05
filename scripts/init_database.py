
import sqlite3
import pandas as pd
from pathlib import Path


# ============================================================
# 1. 基础配置
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[1]

DATA_DIR = BASE_DIR / "data" / "processed"
DATABASE_DIR = BASE_DIR / "data" / "database"

DATABASE_FILE = DATABASE_DIR / "beverage_agent.db"


# ============================================================
# 2. CSV文件与数据库表名
# ============================================================

# 自动读取 processed 文件夹下的全部 CSV 文件
def get_csv_files():

    if not DATA_DIR.exists():
        raise FileNotFoundError(
            f"找不到数据目录：{DATA_DIR}"
        )

    csv_files = sorted(DATA_DIR.glob("*.csv"))

    if not csv_files:
        raise FileNotFoundError(
            f"数据目录中没有找到 CSV 文件：{DATA_DIR}"
        )

    return csv_files


# ============================================================
# 3. 数据库初始化
# ============================================================

def initialize_database():

    DATABASE_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    if DATABASE_FILE.exists():
        print("检测到已有数据库文件，将更新其中对应的数据表。")

    connection = sqlite3.connect(DATABASE_FILE)

    return connection


# ============================================================
# 4. 导入CSV数据
# ============================================================

def import_csv_to_database(connection, csv_files):

    import_results = []

    for csv_file in csv_files:

        table_name = csv_file.stem

        print(f"\n正在导入：{csv_file.name}")

        try:
            df = pd.read_csv(csv_file)

            if df.empty:
                print("  跳过：文件没有数据")
                continue

            # 写入SQLite
            # if_exists='replace'：重新生成对应数据表
            df.to_sql(
                name=table_name,
                con=connection,
                if_exists="replace",
                index=False
            )

            # 记录导入结果
            import_results.append({
                "table_name": table_name,
                "source_file": csv_file.name,
                "row_count": len(df),
                "column_count": len(df.columns),
                "status": "成功"
            })

            print(f"  数据表：{table_name}")
            print(f"  数据行数：{len(df)}")
            print(f"  字段数量：{len(df.columns)}")

        except Exception as e:

            import_results.append({
                "table_name": table_name,
                "source_file": csv_file.name,
                "row_count": 0,
                "column_count": 0,
                "status": f"失败：{str(e)}"
            })

            print(f"  导入失败：{e}")

    connection.commit()

    return pd.DataFrame(import_results)


# ============================================================
# 5. 创建常用查询索引
# ============================================================

def create_indexes(connection):

    index_statements = [
        """
        CREATE INDEX IF NOT EXISTS idx_sales_sku_date
        ON sales_daily (sku_id, date)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_inventory_sku
        ON inventory_snapshot (sku_id)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_purchase_orders_supplier
        ON purchase_orders (supplier_id)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_purchase_details_sku
        ON purchase_order_details (sku_id)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_competitor_prices_sku
        ON competitor_prices (sku_id)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_promotion_details_sku
        ON promotion_details (sku_id)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_supplier_mapping_sku
        ON product_supplier_mapping (sku_id)
        """
    ]

    print("\n开始创建常用查询索引：")

    for statement in index_statements:

        try:
            connection.execute(statement)
            index_name = statement.split("idx_")[1].split()[0]
            print(f"  创建成功：idx_{index_name}")

        except sqlite3.OperationalError as e:

            # 如果对应业务表不存在，则跳过该索引
            print(f"  跳过索引：{e}")

    connection.commit()


# ============================================================
# 6. 数据库检查
# ============================================================

def check_database(connection):

    cursor = connection.cursor()

    cursor.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        AND name NOT LIKE 'sqlite_%'
        ORDER BY name
    """)

    tables = cursor.fetchall()

    print("\n数据库数据表检查：")

    total_rows = 0

    for (table_name,) in tables:

        cursor.execute(
            f'SELECT COUNT(*) FROM "{table_name}"'
        )

        row_count = cursor.fetchone()[0]

        total_rows += row_count

        print(
            f"  {table_name:<35} {row_count:>10,} 行"
        )

    print("\n数据库检查结果：")
    print(f"数据表数量：{len(tables)}")
    print(f"数据总行数：{total_rows:,}")

    return len(tables), total_rows


# ============================================================
# 7. 主程序
# ============================================================

def main():

    print("=" * 60)
    print("开始初始化酒水采销业务数据库")
    print("=" * 60)

    csv_files = get_csv_files()

    print(f"发现CSV文件数量：{len(csv_files)}")

    connection = initialize_database()

    try:

        import_results = import_csv_to_database(
            connection,
            csv_files
        )

        create_indexes(connection)

        table_count, total_rows = check_database(
            connection
        )

        print("\nCSV导入结果汇总：")

        if not import_results.empty:
            print(
                import_results[
                    [
                        "source_file",
                        "row_count",
                        "status"
                    ]
                ].to_string(index=False)
            )

        failed_count = 0

        if not import_results.empty:
            failed_count = (
                import_results["status"]
                .str.startswith("失败")
                .sum()
            )

        print("\n数据库初始化完成！")
        print(f"成功导入数据表：{len(import_results) - failed_count}")
        print(f"导入失败数量：{failed_count}")
        print(f"数据库数据表总数：{table_count}")
        print(f"数据库数据总行数：{total_rows:,}")
        print(f"数据库文件：{DATABASE_FILE}")

        if failed_count > 0:
            print("\n注意：部分CSV文件导入失败，需要检查。")

    finally:

        connection.close()

    print("=" * 60)


if __name__ == "__main__":
    main()

