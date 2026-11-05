
from pathlib import Path
import random
import pandas as pd

random.seed(42)

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 读取商品档案和库存快照
products = pd.read_csv(
    PROJECT_ROOT / "data" / "processed" / "products.csv"
)

inventory = pd.read_csv(
    PROJECT_ROOT / "data" / "processed" / "inventory_snapshot.csv"
)

# 合并商品信息与库存信息
df = inventory.merge(
    products[["sku_id", "purchase_cost", "subcategory"]],
    on="sku_id",
    how="left"
)

# 不同品类模拟保质期（月）
shelf_life_months = {
    "白酒": None,
    "葡萄酒": None,
    "洋酒": None,
    "啤酒": 12,
    "黄酒": 24,
    "养生酒/保健酒": None,
    "清酒/烧酒": 12,
    "果酒/米酒": 12,
    "鸡尾酒/预调酒": 12,
    "其他酒类": None
}

# 说明：
# None 表示不在模拟系统中统一推算保质期，
# 应以商品标签、生产商说明和实际储存条件为准。
# 有明确模拟保质期的品类，仅用于练习批次效期管理。

snapshot_date = pd.Timestamp("2026-10-23")

records = []

for _, row in df.iterrows():

    sku_id = row["sku_id"]
    total_stock = int(row["available_stock"])

    if total_stock <= 0:
        continue

    # 每个 SKU 模拟 1 至 3 个库存批次
    batch_count = random.randint(1, 3)

    # 将总库存拆分到不同批次，确保批次数量之和等于总库存
    if batch_count == 1:
        batch_quantities = [total_stock]
    else:
        remaining = total_stock
        batch_quantities = []

        for i in range(batch_count - 1):
            quantity = random.randint(
                1,
                max(1, remaining - (batch_count - i - 1))
            )
            batch_quantities.append(quantity)
            remaining -= quantity

        batch_quantities.append(remaining)

    # 获取品类模拟保质期
    shelf_life = shelf_life_months.get(
        row["category_name"]
    )

    for batch_index, quantity in enumerate(batch_quantities, start=1):

        # 模拟生产日期：距离库存快照日期 1 至 180 天
        production_days_ago = random.randint(1, 180)

        production_date = (
            snapshot_date -
            pd.Timedelta(days=production_days_ago)
        )

        # 默认不推算到期日
        expiry_date = None

        if shelf_life is not None:
            expiry_date = (
                production_date +
                pd.DateOffset(months=shelf_life)
            )

        batch_id = f"{sku_id}-B{batch_index:02d}"

        batch_cost = round(
            quantity * float(row["purchase_cost"]),
            2
        )

        records.append({
            "batch_id": batch_id,
            "sku_id": sku_id,
            "product_name": row["product_name"],
            "category_name": row["category_name"],
            "brand": row["brand"],
            "production_date": production_date.strftime("%Y-%m-%d"),
            "expiry_date": (
                expiry_date.strftime("%Y-%m-%d")
                if expiry_date is not None else None
            ),
            "shelf_life_months": shelf_life,
            "batch_quantity": quantity,
            "remaining_quantity": quantity,
            "purchase_cost": round(float(row["purchase_cost"]), 2),
            "batch_inventory_cost": batch_cost,
            "snapshot_date": snapshot_date.strftime("%Y-%m-%d")
        })

# 生成批次数据
batches = pd.DataFrame(records)

# 保存文件
output_path = (
    PROJECT_ROOT /
    "data" /
    "processed" /
    "inventory_batches.csv"
)

batches.to_csv(
    output_path,
    index=False,
    encoding="utf-8-sig"
)

print("=" * 55)
print("库存批次数据生成完成")
print("=" * 55)

print(f"库存商品数量：{batches['sku_id'].nunique()}")
print(f"库存批次数量：{len(batches)}")
print(f"批次库存总量：{batches['remaining_quantity'].sum():,}")

print("\n各品类批次数量：")
print(
    batches.groupby("category_name")["batch_id"]
    .count()
    .sort_values(ascending=False)
)

print("\n效期管理情况：")
print(
    batches.assign(
        has_expiry=batches["expiry_date"].notna()
    ).groupby("has_expiry")["batch_id"].count()
)

print("\n最早生产的10个批次：")
print(
    batches.sort_values("production_date")[
        ["batch_id", "sku_id", "category_name",
         "production_date", "expiry_date",
         "remaining_quantity"]
    ].head(10).to_string(index=False)
)

print(f"\n文件保存位置：{output_path}")

