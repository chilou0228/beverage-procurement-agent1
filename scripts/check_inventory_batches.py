
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent

batches = pd.read_csv(
    PROJECT_ROOT / "data" / "processed" / "inventory_batches.csv"
)

inventory = pd.read_csv(
    PROJECT_ROOT / "data" / "processed" / "inventory_snapshot.csv"
)

products = pd.read_csv(
    PROJECT_ROOT / "data" / "processed" / "products.csv"
)

print("=" * 55)
print("库存批次数据质量检查")
print("=" * 55)

# 1. 检查批次记录数量
assert len(batches) >= 300, "批次记录数量异常"

# 2. 检查批次编号唯一性
assert batches["batch_id"].is_unique, "存在重复批次编号"

# 3. 检查 SKU 覆盖情况
assert batches["sku_id"].nunique() == 300, (
    "批次数据未覆盖全部商品"
)

# 4. 检查必需字段
required_columns = [
    "batch_id", "sku_id", "product_name",
    "category_name", "brand", "production_date",
    "batch_quantity", "remaining_quantity",
    "purchase_cost", "batch_inventory_cost",
    "snapshot_date"
]

assert set(required_columns).issubset(batches.columns)
assert not batches[required_columns].isnull().any().any(), (
    "必需字段存在缺失"
)

# 5. 检查批次库存数量
assert (batches["batch_quantity"] > 0).all()
assert (batches["remaining_quantity"] > 0).all()
assert (
    batches["batch_quantity"] ==
    batches["remaining_quantity"]
).all(), "批次数量与剩余数量不一致"

# 6. 检查批次库存总量
assert (
    batches["remaining_quantity"].sum() ==
    inventory["available_stock"].sum()
), "批次库存总量与库存快照不一致"

# 7. 检查每个 SKU 的批次库存
batch_sum = (
    batches.groupby("sku_id")["remaining_quantity"]
    .sum()
)

inventory_sum = inventory.set_index("sku_id")["available_stock"]

assert batch_sum.sort_index().equals(
    inventory_sum.sort_index().rename("remaining_quantity")
), "部分 SKU 的批次库存与库存快照不一致"

# 8. 检查生产日期和快照日期
batches["production_date"] = pd.to_datetime(
    batches["production_date"]
)

batches["snapshot_date"] = pd.to_datetime(
    batches["snapshot_date"]
)

assert (
    batches["production_date"] <= batches["snapshot_date"]
).all(), "存在晚于快照日期的生产日期"

assert batches["snapshot_date"].nunique() == 1
assert batches["snapshot_date"].iloc[0] == pd.Timestamp(
    "2026-10-23"
)

# 9. 检查有效期逻辑
has_expiry = batches["expiry_date"].notna()

batches["expiry_date"] = pd.to_datetime(
    batches["expiry_date"]
)

assert (
    batches.loc[has_expiry, "expiry_date"] >
    batches.loc[has_expiry, "production_date"]
).all(), "存在不合理的到期日期"

# 10. 检查库存成本
check_df = batches.merge(
    products[["sku_id", "purchase_cost"]],
    on="sku_id",
    how="left",
    suffixes=("_batch", "_product")
)

expected_cost = (
    check_df["remaining_quantity"] *
    check_df["purchase_cost_product"]
)

cost_diff = (
    expected_cost - check_df["batch_inventory_cost"]
).abs()

assert (cost_diff < 0.011).all(), "批次库存成本计算错误"

# 11. 检查 SKU 是否全部关联商品档案
assert batches["sku_id"].isin(products["sku_id"]).all()

# 输出检查结果
checks = [
    "批次记录数量检查",
    "批次编号唯一性检查",
    "SKU 覆盖情况检查",
    "必需字段完整性检查",
    "批次库存数量检查",
    "批次库存总量检查",
    "单 SKU 批次库存一致性检查",
    "生产日期及快照日期检查",
    "有效期逻辑检查",
    "批次库存成本检查",
    "商品档案关联检查"
]

for item in checks:
    print(f"[通过] {item}")

print("\n库存批次数据质量检查全部通过！")
print(f"批次数量：{len(batches)}")
print(f"覆盖 SKU：{batches['sku_id'].nunique()}")
print(f"批次库存总量：{batches['remaining_quantity'].sum():,}")
print(f"有效期管理批次：{has_expiry.sum()}")
print(f"未统一设置有效期批次：{(~has_expiry).sum()}")
