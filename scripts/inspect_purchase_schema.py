
from pathlib import Path
import sqlite3

ROOT_DIR = Path(__file__).resolve().parents[1]
DB_PATH = ROOT_DIR / "data" / "database" / "beverage_agent.db"

conn = sqlite3.connect(DB_PATH)

tables = [
    "purchase_orders",
    "purchase_order_details",
    "purchase_receipts"
]

try:
    for table in tables:
        print("\n" + "=" * 60)
        print(f"数据表：{table}")
        print("=" * 60)

        cursor = conn.execute(f'PRAGMA table_info("{table}")')

        for row in cursor.fetchall():
            column_id = row[0]
            column_name = row[1]
            column_type = row[2]
            not_null = row[3]
            primary_key = row[5]

            print(
                f"字段：{column_name:<30}"
                f"类型：{column_type:<12}"
                f"主键：{primary_key}"
            )

finally:
    conn.close()

