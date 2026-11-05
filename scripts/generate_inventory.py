
from pathlib import Path
import random
import pandas as pd

random.seed(42)

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 读取商品档案和销售数据
products = pd.read_csv(
    PROJECT_ROOT / "data" / "processed" / "products.csv"
)

sales = pd.read_csv(
    PROJECT_ROOT / "data" / "processed" / "sales_daily.csv"
)

# 库存快照日期
snapshot_date = pd.Timestamp("2026-10-23")

sales["date"] = pd.to_datetime(sales["date"])

# 计算最近30天日均销量
recent_sales = sales[
    sales["date"] > snapshot_date - pd.Timedelta(days=30)
]

avg_sales = (
    recent_sales.groupby("sku_id")["sales_volume"]
    .mean()
    .reset_index()
    .rename(columns={"sales_volume": "avg_daily_sales_30d"})
)

# 合并商品档案与销量
inventory = products.merge(
    avg_sales,
    on="sku_id",
    how="left"
)

records = []

for _, product in inventory.iterrows():

    sku_id = product["sku_id"]
    avg_daily_sales = float(product["avg_daily_sales_30d"])

    # 根据最近30天日均销量模拟库存覆盖天数
    coverage_days = random.uniform(3, 90)

    # 当前可用库存
    available_stock = int(
        round(avg_daily_sales * coverage_days)
    )

    # 安全库存：约7至15天的销量
    safety_days = random.randint(7, 15)

    safety_stock = int(
        round(avg_daily_sales * safety_days)
    )

    # 在途库存
    on_order_stock = random.choice([0, 0, 0, 20, 50, 100, 200])

    # 库存成本
    inventory_cost = round(
        available_stock * float(product["purchase_cost"]),
        2
    )

     # 统一日均销量精度，确保保存的数据和计算口径一致
    avg_daily_sales_rounded = round(avg_daily_sales, 2)

    records.append({
        "snapshot_date": snapshot_date.strftime("%Y-%m-%d"),
        "sku_id": sku_id,
        "product_name": product["product_name"],
        "category_name": product["category_name"],
        "brand": product["brand"],
        "available_stock": available_stock,
        "safety_stock": safety_stock,
        "on_order_stock": on_order_stock,
        "avg_daily_sales_30d": avg_daily_sales_rounded,
        "inventory_coverage_days": round(
            available_stock / avg_daily_sales_rounded, 2
        ) if avg_daily_sales_rounded > 0 else None,
        "inventory_cost": inventory_cost
    })

# 转换为 DataFrame
inventory_df = pd.DataFrame(records)

# 保存库存快照
output_path = (
    PROJECT_ROOT /
    "data" /
    "processed" /
    "inventory_snapshot.csv"
)

inventory_df.to_csv(
    output_path,
    index=False,
    encoding="utf-8-sig"
)

print("=" * 55)
print("当前库存快照生成完成")
print("=" * 55)

print(f"库存商品数量：{len(inventory_df)}")
print(f"库存快照日期：{snapshot_date.date()}")
print(f"库存总量：{inventory_df['available_stock'].sum():,}")
print(f"在途库存总量：{inventory_df['on_order_stock'].sum():,}")
print(f"库存成本总额：¥{inventory_df['inventory_cost'].sum():,.2f}")

print("\n库存覆盖天数分布：")
print(
    inventory_df["inventory_coverage_days"]
    .describe()
    .round(2)
)

print("\n库存覆盖天数最低的10个商品：")
print(
    inventory_df.nsmallest(
        10, "inventory_coverage_days"
    )[
        ["sku_id", "product_name", "available_stock",
         "avg_daily_sales_30d", "inventory_coverage_days"]
    ].to_string(index=False)
)

print(f"\n文件保存位置：{output_path}")

