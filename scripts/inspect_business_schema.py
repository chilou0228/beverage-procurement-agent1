
from pathlib import Path
import sqlite3

ROOT_DIR = Path(__file__).resolve().parents[1]
DB_PATH = ROOT_DIR / "data" / "database" / "beverage_agent.db"

tables = [
    "products",
    "sales_daily",
    "inventory_snapshot",
    "inventory_batches",
    "purchase_orders",
    "purchase_order_details",
    "purchase_receipts",
    "promotions",
    "promotion_details",
    "product_supplier_mapping",
    "backup_supplier_recommendations",
    "supplier_ratings_v2"
]

conn = sqlite3.connect(DB_PATH)

try:
    for table in tables:
        print("\n" + "=" * 70)
        print(f"数据表：{table}")
        print("=" * 70)

        cursor = conn.execute(f'PRAGMA table_info("{table}")')

        for row in cursor.fetchall():
            print(f"{row[1]:<35} {row[2]}")

finally:
    conn.close()
