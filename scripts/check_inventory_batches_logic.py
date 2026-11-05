from pathlib import Path
import pandas as pd

# ==================================================
# 1. 读取数据
# ==================================================

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

print("=" * 65)
print("酒水采销 Agent｜库存批次业务逻辑检查")
print("=" * 65)

print(f"\n库存批次数量：{len(batches):,}")
print(f"库存商品数量：{batches['sku_id'].nunique():,}")


# ==================================================
# 2. 检查辅助函数
# ==================================================

total_checks = 0
passed_checks = 0
failed_checks = 0


def check_result(name, condition, abnormal_count=0):
    global total_checks, passed_checks, failed_checks

    total_checks += 1

    if condition:
        passed_checks += 1
        print(f"PASS：{name}，异常数量：{abnormal_count}")
    else:
        failed_checks += 1
        print(f"FAIL：{name}，异常数量：{abnormal_count}")


# ==================================================
# 检查1：批次基础字段空值检查
# ==================================================

print("\n【检查1：批次基础字段空值检查】")
print("-" * 65)

required_columns = [
    "batch_id",
    "sku_id",
    "product_name",
    "category_name",
    "brand",
    "production_date",
    "batch_quantity",
    "remaining_quantity",
    "purchase_cost",
    "batch_inventory_cost",
    "snapshot_date"
]

for column in required_columns:

    missing_count = batches[column].isna().sum()

    check_result(
        f"{column} 空值检查",
        missing_count == 0,
        missing_count
    )


# ==================================================
# 检查2：批次库存数值检查
# ==================================================

print("\n【检查2：批次库存数值检查】")
print("-" * 65)

numeric_columns = [
    "batch_quantity",
    "remaining_quantity",
    "purchase_cost",
    "batch_inventory_cost"
]

for column in numeric_columns:

    abnormal_count = (batches[column] < 0).sum()

    check_result(
        f"{column} 非负检查",
        abnormal_count == 0,
        abnormal_count
    )


# ==================================================
# 检查3：批次数量关系检查
# ==================================================

print("\n【检查3：批次数量关系检查】")
print("-" * 65)

quantity_error_count = (
    batches["remaining_quantity"]
    > batches["batch_quantity"]
).sum()

check_result(
    "批次剩余数量不超过批次原始数量",
    quantity_error_count == 0,
    quantity_error_count
)

zero_quantity_count = (
    batches["batch_quantity"] <= 0
).sum()

check_result(
    "批次原始数量大于0",
    zero_quantity_count == 0,
    zero_quantity_count
)


# ==================================================
# 检查4：批次库存成本检查
# ==================================================

print("\n【检查4：批次库存成本检查】")
print("-" * 65)

expected_cost = (
    batches["remaining_quantity"]
    * batches["purchase_cost"]
).round(2)

cost_diff = (
    batches["batch_inventory_cost"] - expected_cost
).abs()

cost_error_count = (cost_diff > 0.02).sum()

check_result(
    "批次库存成本 = 剩余数量 × 采购成本",
    cost_error_count == 0,
    cost_error_count
)


# ==================================================
# 检查5：生产日期与库存快照日期检查
# ==================================================

print("\n【检查5：生产日期与库存快照日期检查】")
print("-" * 65)

batches["production_date"] = pd.to_datetime(
    batches["production_date"],
    errors="coerce"
)

batches["snapshot_date"] = pd.to_datetime(
    batches["snapshot_date"],
    errors="coerce"
)

invalid_production_date = (
    batches["production_date"].isna().sum()
)

invalid_snapshot_date = (
    batches["snapshot_date"].isna().sum()
)

check_result(
    "生产日期格式检查",
    invalid_production_date == 0,
    invalid_production_date
)

check_result(
    "批次快照日期格式检查",
    invalid_snapshot_date == 0,
    invalid_snapshot_date
)

if invalid_production_date == 0 and invalid_snapshot_date == 0:

    future_production_count = (
        batches["production_date"]
        > batches["snapshot_date"]
    ).sum()

    check_result(
        "生产日期不晚于库存快照日期",
        future_production_count == 0,
        future_production_count
    )

    production_age = (
        batches["snapshot_date"] - batches["production_date"]
    ).dt.days

    abnormal_age_count = (
        (production_age < 1) | (production_age > 180)
    ).sum()

    check_result(
        "生产日期距离快照日期为1至180天",
        abnormal_age_count == 0,
        abnormal_age_count
    )


# ==================================================
# 检查6：批次效期逻辑检查
# ==================================================

print("\n【检查6：批次效期逻辑检查】")
print("-" * 65)

batches["expiry_date"] = pd.to_datetime(
    batches["expiry_date"],
    errors="coerce"
)

shelf_life_rules = {
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

expected_shelf_life = batches["category_name"].map(
    shelf_life_rules
)

shelf_life_diff = (
    batches["shelf_life_months"].fillna(-1)
    != expected_shelf_life.fillna(-1)
)

shelf_life_error_count = shelf_life_diff.sum()

check_result(
    "批次保质期与品类模拟规则一致",
    shelf_life_error_count == 0,
    shelf_life_error_count
)

expiry_required = expected_shelf_life.notna()

expiry_missing_count = (
    expiry_required & batches["expiry_date"].isna()
).sum()

check_result(
    "有模拟保质期的品类均设置到期日期",
    expiry_missing_count == 0,
    expiry_missing_count
)

expiry_unexpected_count = (
    (~expiry_required) & batches["expiry_date"].notna()
).sum()

check_result(
    "无统一模拟保质期的品类不推算到期日期",
    expiry_unexpected_count == 0,
    expiry_unexpected_count
)

valid_expiry = (
    expiry_required
    & batches["expiry_date"].notna()
    & batches["production_date"].notna()
)

expected_expiry = pd.Series(
    pd.NaT,
    index=batches.index
)

expected_expiry.loc[valid_expiry] = [
    production_date + pd.DateOffset(months=int(months))
    for production_date, months in zip(
        batches.loc[valid_expiry, "production_date"],
        expected_shelf_life.loc[valid_expiry]
    )
]

expiry_diff = (
    batches.loc[valid_expiry, "expiry_date"]
    != expected_expiry.loc[valid_expiry]
)

expiry_error_count = expiry_diff.sum()

check_result(
    "到期日期 = 生产日期 + 模拟保质期",
    expiry_error_count == 0,
    expiry_error_count
)


# ==================================================
# 检查7：批次唯一性检查
# ==================================================

print("\n【检查7：批次唯一性检查】")
print("-" * 65)

duplicate_batch_count = batches["batch_id"].duplicated().sum()

check_result(
    "批次ID不存在重复",
    duplicate_batch_count == 0,
    duplicate_batch_count
)


# ==================================================
# 检查8：批次与库存快照数量一致性
# ==================================================

print("\n【检查8：批次与库存快照数量一致性】")
print("-" * 65)

batch_summary = (
    batches.groupby("sku_id")["remaining_quantity"]
    .sum()
    .reset_index()
    .rename(columns={
        "remaining_quantity": "batch_total_stock"
    })
)

stock_check = inventory.merge(
    batch_summary,
    on="sku_id",
    how="left"
)

stock_check["batch_total_stock"] = (
    stock_check["batch_total_stock"].fillna(0)
)

stock_diff = (
    stock_check["available_stock"]
    - stock_check["batch_total_stock"]
).abs()

stock_error_count = (stock_diff > 0).sum()

check_result(
    "SKU批次剩余数量之和 = 库存快照可用库存",
    stock_error_count == 0,
    stock_error_count
)


# ==================================================
# 检查9：商品档案关联检查
# ==================================================

print("\n【检查9：商品档案关联检查】")
print("-" * 65)

product_skus = set(products["sku_id"])
batch_skus = set(batches["sku_id"])

unknown_skus = batch_skus - product_skus
missing_skus = product_skus - batch_skus

check_result(
    "批次SKU均存在于商品档案",
    len(unknown_skus) == 0,
    len(unknown_skus)
)

check_result(
    "所有有库存的SKU均有批次记录",
    len(missing_skus) == 0,
    len(missing_skus)
)


# ==================================================
# 检查10：商品采购成本一致性
# ==================================================

print("\n【检查10：商品采购成本一致性】")
print("-" * 65)

cost_check = batches.merge(
    products[["sku_id", "purchase_cost"]],
    on="sku_id",
    how="left",
    suffixes=("_batch", "_product"),
    validate="many_to_one"
)

purchase_cost_diff = (
    cost_check["purchase_cost_batch"]
    - cost_check["purchase_cost_product"]
).abs()

purchase_cost_error_count = (
    purchase_cost_diff > 0.02
).sum()

check_result(
    "批次采购成本与商品档案一致",
    purchase_cost_error_count == 0,
    purchase_cost_error_count
)


# ==================================================
# 11. 检查结果汇总
# ==================================================

print("\n" + "=" * 65)
print("库存批次业务逻辑检查汇总")
print("=" * 65)

print(f"检查项目数量：{total_checks}")
print(f"通过项目数量：{passed_checks}")
print(f"异常项目数量：{failed_checks}")

if failed_checks == 0:
    print("\nPASS：所有库存批次业务逻辑检查均通过！")
else:
    print("\nFAIL：存在未通过的库存批次业务逻辑检查，请根据上方结果排查。")

print("=" * 65)