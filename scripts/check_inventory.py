
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent

inventory_path = (
    PROJECT_ROOT / "data" / "processed" / "inventory_snapshot.csv"
)

products_path = (
    PROJECT_ROOT / "data" / "processed" / "products.csv"
)

inventory = pd.read_csv(inventory_path)
products = pd.read_csv(products_path)

print("=" * 55)
print("库存快照数据质量检查")
print("=" * 55)

# 1. 检查库存记录数量
assert len(inventory) == 300, "库存记录数量不正确"

# 2. 检查 SKU 唯一性
assert inventory["sku_id"].is_unique, "存在重复 SKU"

# 3. 检查库存快照日期
assert inventory["snapshot_date"].nunique() == 1
assert inventory["snapshot_date"].iloc[0] == "2026-10-23"

# 4. 检查必需字段
required_columns = [
    "snapshot_date",
    "sku_id",
    "product_name",
    "category_name",
    "brand",
    "available_stock",
    "safety_stock",
    "on_order_stock",
    "avg_daily_sales_30d",
    "inventory_coverage_days",
    "inventory_cost"
]

assert set(required_columns).issubset(inventory.columns)

assert not inventory[required_columns].isnull().any().any(), (
    "库存数据存在缺失值"
)

# 5. 检查库存数量不能为负数
quantity_columns = [
    "available_stock",
    "safety_stock",
    "on_order_stock",
    "avg_daily_sales_30d"
]

for column in quantity_columns:
    assert (inventory[column] >= 0).all(), (
        f"{column} 存在负数"
    )

# 6. 检查库存覆盖天数
expected_coverage = (
    inventory["available_stock"] /
    inventory["avg_daily_sales_30d"]
)

coverage_diff = (
    expected_coverage -
    inventory["inventory_coverage_days"]
).abs()

assert (coverage_diff < 0.011).all(), (
    "库存覆盖天数计算不正确"
)

# 7. 检查库存成本计算
product_cost = products[
    ["sku_id", "purchase_cost"]
]

check_df = inventory.merge(
    product_cost,
    on="sku_id",
    how="left"
)

expected_inventory_cost = (
    check_df["available_stock"] *
    check_df["purchase_cost"]
)

cost_diff = (
    expected_inventory_cost -
    check_df["inventory_cost"]
).abs()

assert (cost_diff < 0.011).all(), (
    "库存成本计算不正确"
)

# 8. 检查库存商品是否全部存在于商品档案
assert inventory["sku_id"].isin(products["sku_id"]).all()

# 9. 检查品类和品牌信息
product_info = products[
    ["sku_id", "category_name", "brand"]
]

info_check = inventory.merge(
    product_info,
    on="sku_id",
    how="left",
    suffixes=("_inventory", "_product")
)

assert (
    info_check["category_name_inventory"] ==
    info_check["category_name_product"]
).all(), "库存品类信息不一致"

assert (
    info_check["brand_inventory"] ==
    info_check["brand_product"]
).all(), "库存品牌信息不一致"

print("[通过] 库存记录数量检查")
print("[通过] SKU 唯一性检查")
print("[通过] 库存快照日期检查")
print("[通过] 必需字段完整性检查")
print("[通过] 库存数量非负检查")
print("[通过] 库存覆盖天数计算检查")
print("[通过] 库存成本计算检查")
print("[通过] 商品档案关联检查")
print("[通过] 品类和品牌一致性检查")

print("\n库存数据质量检查全部通过！")
print(f"库存 SKU 数量：{inventory['sku_id'].nunique()}")
print(f"库存总量：{inventory['available_stock'].sum():,}")
print(f"在途库存：{inventory['on_order_stock'].sum():,}")
print(f"缺失值数量：{inventory[required_columns].isnull().sum().sum()}")
print(f"重复 SKU 数量：{inventory['sku_id'].duplicated().sum()}")
