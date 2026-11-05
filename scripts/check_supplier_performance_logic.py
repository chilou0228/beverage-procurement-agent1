from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ==================================================
# 1. 读取数据
# ==================================================

suppliers = pd.read_csv(
    PROJECT_ROOT / "data" / "processed" / "suppliers.csv"
)

orders = pd.read_csv(
    PROJECT_ROOT / "data" / "processed" / "purchase_orders.csv"
)

receipts = pd.read_csv(
    PROJECT_ROOT / "data" / "processed" / "purchase_receipts.csv"
)

performance = pd.read_csv(
    PROJECT_ROOT / "data" / "processed" / "supplier_performance.csv"
)

receipts["receipt_date"] = pd.to_datetime(
    receipts["receipt_date"],
    errors="coerce"
)

receipts["expected_arrival_date"] = pd.to_datetime(
    receipts["expected_arrival_date"],
    errors="coerce"
)

print("=" * 65)
print("酒水采销 Agent｜供应商绩效业务逻辑检查")
print("=" * 65)

print(f"\n供应商档案：{len(suppliers)}")
print(f"采购订单：{len(orders)}")
print(f"到货记录：{len(receipts)}")
print(f"供应商绩效记录：{len(performance)}")


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
# 检查1：供应商绩效字段完整性
# ==================================================

print("\n【检查1：供应商绩效字段完整性】")
print("-" * 65)

required_columns = [
    "supplier_id",
    "supplier_name",
    "region",
    "main_category",
    "original_supplier_level",
    "order_count",
    "purchase_amount",
    "ordered_quantity",
    "received_quantity",
    "fulfillment_rate",
    "completed_orders",
    "partial_orders",
    "pending_orders",
    "order_completion_rate",
    "on_time_quantity",
    "late_quantity",
    "on_time_delivery_rate",
    "avg_weighted_late_days"
]

for column in required_columns:

    missing_count = performance[column].isna().sum()

    check_result(
        f"字段 {column} 不存在空值",
        missing_count == 0,
        missing_count
    )


# ==================================================
# 检查2：供应商数量和唯一性
# ==================================================

print("\n【检查2：供应商数量和唯一性】")
print("-" * 65)

check_result(
    "绩效记录供应商数量与供应商档案一致",
    len(performance) == len(suppliers),
    abs(len(performance) - len(suppliers))
)

duplicate_count = (
    performance["supplier_id"].duplicated().sum()
)

check_result(
    "供应商绩效表 supplier_id 唯一",
    duplicate_count == 0,
    duplicate_count
)

missing_supplier_ids = (
    set(suppliers["supplier_id"])
    - set(performance["supplier_id"])
)

extra_supplier_ids = (
    set(performance["supplier_id"])
    - set(suppliers["supplier_id"])
)

check_result(
    "绩效表覆盖全部供应商档案",
    len(missing_supplier_ids) == 0
    and len(extra_supplier_ids) == 0,
    len(missing_supplier_ids) + len(extra_supplier_ids)
)


# ==================================================
# 检查3：供应商基础信息一致性
# ==================================================

print("\n【检查3：供应商基础信息一致性】")
print("-" * 65)

supplier_reference = suppliers[
    [
        "supplier_id",
        "supplier_name",
        "region",
        "main_category",
        "supplier_level"
    ]
].rename(
    columns={
        "supplier_level": "original_supplier_level"
    }
)

supplier_check = performance.merge(
    supplier_reference,
    on="supplier_id",
    how="left",
    suffixes=("_performance", "_source"),
    validate="one_to_one"
)

for column in [
    "supplier_name",
    "region",
    "main_category",
    "original_supplier_level"
]:

    diff = (
        supplier_check[f"{column}_performance"]
        != supplier_check[f"{column}_source"]
    )

    error_count = diff.fillna(True).sum()

    check_result(
        f"供应商基础字段 {column} 与档案一致",
        error_count == 0,
        error_count
    )


# ==================================================
# 检查4：采购订单数量和金额汇总
# ==================================================

print("\n【检查4：采购订单汇总检查】")
print("-" * 65)

order_summary = (
    orders.groupby("supplier_id")
    .agg(
        calculated_order_count=("order_id", "nunique"),
        calculated_purchase_amount=("order_amount", "sum"),
        calculated_ordered_quantity=("ordered_quantity", "sum"),
        calculated_received_quantity=("received_quantity", "sum"),
        calculated_completed_orders=(
            "order_status",
            lambda x: (x == "已完成").sum()
        ),
        calculated_partial_orders=(
            "order_status",
            lambda x: (x == "部分到货").sum()
        ),
        calculated_pending_orders=(
            "order_status",
            lambda x: (x == "运输中").sum()
        )
    )
    .reset_index()
)

order_check = performance.merge(
    order_summary,
    on="supplier_id",
    how="left",
    validate="one_to_one"
)

calculated_columns = [
    "calculated_order_count",
    "calculated_purchase_amount",
    "calculated_ordered_quantity",
    "calculated_received_quantity",
    "calculated_completed_orders",
    "calculated_partial_orders",
    "calculated_pending_orders"
]

for column in calculated_columns:
    order_check[column] = order_check[column].fillna(0)

comparison_pairs = [
    ("order_count", "calculated_order_count"),
    ("purchase_amount", "calculated_purchase_amount"),
    ("ordered_quantity", "calculated_ordered_quantity"),
    ("received_quantity", "calculated_received_quantity"),
    ("completed_orders", "calculated_completed_orders"),
    ("partial_orders", "calculated_partial_orders"),
    ("pending_orders", "calculated_pending_orders")
]

for actual_column, expected_column in comparison_pairs:

    diff = (
        order_check[actual_column]
        - order_check[expected_column]
    ).abs()

    if actual_column == "purchase_amount":
        error_count = (diff > 0.01).sum()
    else:
        error_count = (diff > 0).sum()

    check_result(
        f"{actual_column} 与采购订单重新汇总结果一致",
        error_count == 0,
        error_count
    )


# ==================================================
# 检查5：履约率计算逻辑
# ==================================================

print("\n【检查5：供应商履约率计算】")
print("-" * 65)

calculated_fulfillment = (
    performance["received_quantity"]
    / performance["ordered_quantity"].replace(0, pd.NA)
).fillna(0)

fulfillment_diff = (
    performance["fulfillment_rate"]
    - calculated_fulfillment
).abs()

fulfillment_error_count = (
    fulfillment_diff > 1e-8
).sum()

check_result(
    "履约率 = 累计到货量 / 累计采购量",
    fulfillment_error_count == 0,
    fulfillment_error_count
)


# ==================================================
# 检查6：订单完成率计算逻辑
# ==================================================

print("\n【检查6：供应商订单完成率计算】")
print("-" * 65)

calculated_completion = (
    performance["completed_orders"]
    / performance["order_count"].replace(0, pd.NA)
).fillna(0)

completion_diff = (
    performance["order_completion_rate"]
    - calculated_completion
).abs()

completion_error_count = (
    completion_diff > 1e-8
).sum()

check_result(
    "订单完成率 = 已完成订单数 / 全部订单数",
    completion_error_count == 0,
    completion_error_count
)


# ==================================================
# 检查7：重新计算到货及时性
# ==================================================

print("\n【检查7：到货及时性重新计算】")
print("-" * 65)

receipts["delay_days"] = (
    receipts["receipt_date"]
    - receipts["expected_arrival_date"]
).dt.days

receipts["calculated_on_time_quantity"] = (
    receipts["received_quantity"].where(
        receipts["delay_days"] <= 0,
        0
    )
)

receipts["calculated_late_quantity"] = (
    receipts["received_quantity"].where(
        receipts["delay_days"] > 0,
        0
    )
)

receipts["calculated_late_days"] = (
    receipts["delay_days"].clip(lower=0)
)

receipt_summary = (
    receipts.groupby("supplier_id")
    .apply(
        lambda group: pd.Series({
            "calculated_on_time_quantity":
                group["calculated_on_time_quantity"].sum(),

            "calculated_late_quantity":
                group["calculated_late_quantity"].sum(),

            "calculated_weighted_late_days": (
                (
                    group["calculated_late_days"]
                    * group["received_quantity"]
                ).sum()
                / group["received_quantity"].sum()
                if group["received_quantity"].sum() > 0
                else 0
            )
        }),
        include_groups=False
    )
    .reset_index()
)

receipt_check = performance.merge(
    receipt_summary,
    on="supplier_id",
    how="left",
    validate="one_to_one"
)

receipt_numeric_columns = [
    "calculated_on_time_quantity",
    "calculated_late_quantity",
    "calculated_weighted_late_days"
]

receipt_check[receipt_numeric_columns] = (
    receipt_check[receipt_numeric_columns].fillna(0)
)

receipt_comparisons = [
    ("on_time_quantity", "calculated_on_time_quantity"),
    ("late_quantity", "calculated_late_quantity"),
    ("avg_weighted_late_days", "calculated_weighted_late_days")
]

for actual_column, expected_column in receipt_comparisons:

    diff = (
        receipt_check[actual_column]
        - receipt_check[expected_column]
    ).abs()

    tolerance = 1e-8

    error_count = (diff > tolerance).sum()

    check_result(
        f"{actual_column} 与到货记录重新计算结果一致",
        error_count == 0,
        error_count
    )


# ==================================================
# 检查8：到货及时率计算
# ==================================================

print("\n【检查8：到货及时率计算】")
print("-" * 65)

calculated_on_time_rate = (
    performance["on_time_quantity"]
    / performance["received_quantity"].replace(0, pd.NA)
).fillna(0)

on_time_rate_diff = (
    performance["on_time_delivery_rate"]
    - calculated_on_time_rate
).abs()

on_time_rate_error_count = (
    on_time_rate_diff > 1e-8
).sum()

check_result(
    "到货及时率 = 按时到货数量 / 累计到货数量",
    on_time_rate_error_count == 0,
    on_time_rate_error_count
)


# ==================================================
# 检查9：供应商绩效指标合理性
# ==================================================

print("\n【检查9：供应商绩效指标合理性】")
print("-" * 65)

rate_columns = [
    "fulfillment_rate",
    "order_completion_rate",
    "on_time_delivery_rate"
]

for column in rate_columns:

    abnormal_count = (
        (
            performance[column] < 0
        )
        |
        (
            performance[column] > 1
        )
    ).sum()

    check_result(
        f"{column} 处于0至1之间",
        abnormal_count == 0,
        abnormal_count
    )

quantity_columns = [
    "order_count",
    "ordered_quantity",
    "received_quantity",
    "completed_orders",
    "partial_orders",
    "pending_orders",
    "on_time_quantity",
    "late_quantity"
]

for column in quantity_columns:

    abnormal_count = (
        performance[column] < 0
    ).sum()

    check_result(
        f"{column} 不存在负数",
        abnormal_count == 0,
        abnormal_count
    )

check_result(
    "供应商按时到货数量不超过累计到货数量",
    (
        performance["on_time_quantity"]
        <= performance["received_quantity"]
    ).all(),
    (
        performance["on_time_quantity"]
        > performance["received_quantity"]
    ).sum()
)

check_result(
    "供应商延迟到货数量不超过累计到货数量",
    (
        performance["late_quantity"]
        <= performance["received_quantity"]
    ).all(),
    (
        performance["late_quantity"]
        > performance["received_quantity"]
    ).sum()
)

check_result(
    "按时到货数量与延迟到货数量之和等于累计到货数量",
    (
        performance["on_time_quantity"]
        + performance["late_quantity"]
        == performance["received_quantity"]
    ).all(),
    (
        (
            performance["on_time_quantity"]
            + performance["late_quantity"]
        )
        != performance["received_quantity"]
    ).sum()
)


# ==================================================
# 检查10：采购订单状态数量汇总
# ==================================================

print("\n【检查10：订单状态数量汇总】")
print("-" * 65)

status_total = (
    performance["completed_orders"]
    + performance["partial_orders"]
    + performance["pending_orders"]
)

status_error_count = (
    status_total != performance["order_count"]
).sum()

check_result(
    "已完成、部分到货、运输中订单数之和等于订单总数",
    status_error_count == 0,
    status_error_count
)


# ==================================================
# 检查11：全局汇总一致性
# ==================================================

print("\n【检查11：供应商绩效全局汇总】")
print("-" * 65)

check_result(
    "供应商采购总量与采购订单主表一致",
    performance["ordered_quantity"].sum()
    == orders["ordered_quantity"].sum(),
    abs(
        performance["ordered_quantity"].sum()
        - orders["ordered_quantity"].sum()
    )
)

check_result(
    "供应商累计到货量与到货记录一致",
    performance["received_quantity"].sum()
    == receipts["received_quantity"].sum(),
    abs(
        performance["received_quantity"].sum()
        - receipts["received_quantity"].sum()
    )
)

check_result(
    "供应商订单总数与采购订单主表一致",
    performance["order_count"].sum()
    == orders["order_id"].nunique(),
    abs(
        performance["order_count"].sum()
        - orders["order_id"].nunique()
    )
)


# ==================================================
# 12. 输出汇总
# ==================================================

print("\n" + "=" * 65)
print("供应商绩效业务逻辑检查汇总")
print("=" * 65)

print(f"检查项目数量：{total_checks}")
print(f"通过项目数量：{passed_checks}")
print(f"异常项目数量：{failed_checks}")

print("\n供应商绩效汇总：")
print(f"供应商数量：{len(performance)}")
print(f"有采购订单的供应商：{(performance['order_count'] > 0).sum()}")
print(f"采购总量：{performance['ordered_quantity'].sum():,}")
print(f"累计到货量：{performance['received_quantity'].sum():,}")

total_ordered = performance["ordered_quantity"].sum()
total_received = performance["received_quantity"].sum()

overall_rate = (
    total_received / total_ordered
    if total_ordered > 0
    else 0
)

print(f"整体阶段性履约率：{overall_rate:.2%}")

if failed_checks == 0:
    print("\nPASS：所有供应商绩效业务逻辑检查均通过！")
else:
    print("\nFAIL：存在未通过的检查，请根据上方结果排查。")

print("=" * 65)
