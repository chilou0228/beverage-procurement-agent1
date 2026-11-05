from pathlib import Path
import pandas as pd

# ==================================================
# 1. 路径与数据读取
# ==================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

inventory = pd.read_csv(
    PROJECT_ROOT / "data" / "processed" / "inventory_snapshot.csv"
)

products = pd.read_csv(
    PROJECT_ROOT / "data" / "processed" / "products.csv"
)

print("=" * 65)
print("酒水采销 Agent｜库存快照业务逻辑检查")
print("=" * 65)

print(f"\n库存记录数量：{len(inventory):,}")
print(f"商品档案数量：{len(products):,}")


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
        print(
            f"PASS：{name}，异常数量：{abnormal_count}"
        )
    else:
        failed_checks += 1
        print(
            f"FAIL：{name}，异常数量：{abnormal_count}"
        )


# ==================================================
# 检查1：库存基础字段空值检查
# ==================================================

print("\n【检查1：库存基础字段空值检查】")
print("-" * 65)

required_columns = [
    "snapshot_date",
    "sku_id",
    "available_stock",
    "safety_stock",
    "on_order_stock",
    "avg_daily_sales_30d",
    "inventory_coverage_days",
    "inventory_cost"
]

for column in required_columns:
    missing_count = inventory[column].isna().sum()

    check_result(
        f"{column} 空值检查",
        missing_count == 0,
        missing_count
    )


# ==================================================
# 检查2：库存数值非负检查
# ==================================================

print("\n【检查2：库存数值非负检查】")
print("-" * 65)

numeric_columns = [
    "available_stock",
    "safety_stock",
    "on_order_stock",
    "avg_daily_sales_30d",
    "inventory_coverage_days",
    "inventory_cost"
]

for column in numeric_columns:
    abnormal_count = (inventory[column] < 0).sum()

    check_result(
        f"{column} 非负检查",
        abnormal_count == 0,
        abnormal_count
    )


# ==================================================
# 检查3：库存成本计算检查
# ==================================================

print("\n【检查3：库存成本计算检查】")
print("-" * 65)

inventory_check = inventory.merge(
    products[["sku_id", "purchase_cost"]],
    on="sku_id",
    how="left",
    validate="many_to_one"
)

expected_cost = (
    inventory_check["available_stock"]
    * inventory_check["purchase_cost"]
).round(2)

cost_diff = (
    inventory_check["inventory_cost"] - expected_cost
).abs()

cost_error_count = (cost_diff > 0.02).sum()

check_result(
    "库存成本 = 可用库存 × 商品采购成本",
    cost_error_count == 0,
    cost_error_count
)


# ==================================================
# 检查4：库存覆盖天数计算检查
# ==================================================

print("\n【检查4：库存覆盖天数计算检查】")
print("-" * 65)

expected_coverage = (
    inventory["available_stock"]
    / inventory["avg_daily_sales_30d"]
).round(2)

valid_coverage = (
    inventory["avg_daily_sales_30d"] > 0
)

coverage_diff = (
    inventory.loc[valid_coverage, "inventory_coverage_days"]
    - expected_coverage[valid_coverage]
).abs()

coverage_error_count = (
    coverage_diff > 0.02
).sum()

check_result(
    "库存覆盖天数 = 可用库存 ÷ 最近30天日均销量",
    coverage_error_count == 0,
    coverage_error_count
)


# ==================================================
# 检查5：库存快照日期检查
# ==================================================

print("\n【检查5：库存快照日期检查】")
print("-" * 65)

snapshot_dates = pd.to_datetime(
    inventory["snapshot_date"],
    errors="coerce"
)

invalid_date_count = snapshot_dates.isna().sum()

check_result(
    "库存快照日期格式检查",
    invalid_date_count == 0,
    invalid_date_count
)

if invalid_date_count == 0:
    unique_dates = snapshot_dates.dt.strftime(
        "%Y-%m-%d"
    ).nunique()

    check_result(
        "所有商品使用同一个库存快照日期",
        unique_dates == 1,
        unique_dates - 1
    )

    print(
        f"库存快照日期：{snapshot_dates.min().date()}"
    )


# ==================================================
# 检查6：SKU唯一性检查
# ==================================================

print("\n【检查6：SKU唯一性检查】")
print("-" * 65)

duplicate_count = inventory["sku_id"].duplicated().sum()

check_result(
    "同一SKU不存在重复库存记录",
    duplicate_count == 0,
    duplicate_count
)


# ==================================================
# 检查7：商品档案关联检查
# ==================================================

print("\n【检查7：商品档案关联检查】")
print("-" * 65)

product_skus = set(products["sku_id"])
inventory_skus = set(inventory["sku_id"])

unknown_skus = inventory_skus - product_skus
missing_skus = product_skus - inventory_skus

check_result(
    "库存SKU均存在于商品档案",
    len(unknown_skus) == 0,
    len(unknown_skus)
)

check_result(
    "商品档案中的SKU均有库存记录",
    len(missing_skus) == 0,
    len(missing_skus)
)


# ==================================================
# 检查8：库存覆盖天数范围检查
# ==================================================

print("\n【检查8：库存覆盖天数范围检查】")
print("-" * 65)

# 生成脚本中设定的随机覆盖天数范围为3至90天。
# 因为库存数量经过取整、日均销量经过保留两位小数，
# 所以实际覆盖天数允许有少量偏差。

coverage_abnormal = (
    (inventory["inventory_coverage_days"] < 2.5)
    | (inventory["inventory_coverage_days"] > 90.5)
).sum()

check_result(
    "库存覆盖天数处于合理模拟范围",
    coverage_abnormal == 0,
    coverage_abnormal
)


# ==================================================
# 9. 检查结果汇总
# ==================================================

print("\n" + "=" * 65)
print("库存快照业务逻辑检查汇总")
print("=" * 65)

print(f"检查项目数量：{total_checks}")
print(f"通过项目数量：{passed_checks}")
print(f"异常项目数量：{failed_checks}")

if failed_checks == 0:
    print("\nPASS：所有库存快照业务逻辑检查均通过！")
else:
    print("\nFAIL：存在未通过的库存业务逻辑检查，请根据上方结果排查。")

print("=" * 65)
