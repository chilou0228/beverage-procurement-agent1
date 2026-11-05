from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ==================================================
# 1. 读取数据
# ==================================================

orders = pd.read_csv(
    PROJECT_ROOT / "data" / "processed" / "purchase_orders.csv"
)

details = pd.read_csv(
    PROJECT_ROOT / "data" / "processed" / "purchase_order_details.csv"
)

receipts = pd.read_csv(
    PROJECT_ROOT / "data" / "processed" / "purchase_receipts.csv"
)

print("=" * 65)
print("酒水采销 Agent｜采购订单状态业务逻辑检查")
print("=" * 65)

print(f"\n采购订单数量：{len(orders):,}")
print(f"采购明细数量：{len(details):,}")
print(f"到货记录数量：{len(receipts):,}")


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
# 检查1：订单主表关键字段
# ==================================================

print("\n【检查1：订单主表关键字段】")
print("-" * 65)

required_columns = [
    "order_id",
    "supplier_id",
    "supplier_name",
    "ordered_quantity",
    "received_quantity",
    "pending_quantity",
    "order_status"
]

for column in required_columns:

    missing_count = orders[column].isna().sum()

    check_result(
        f"订单主表字段 {column} 不存在空值",
        missing_count == 0,
        missing_count
    )


# ==================================================
# 检查2：订单ID唯一性
# ==================================================

print("\n【检查2：订单ID唯一性】")
print("-" * 65)

duplicate_order_count = (
    orders["order_id"].duplicated().sum()
)

check_result(
    "采购订单主表 order_id 唯一",
    duplicate_order_count == 0,
    duplicate_order_count
)


# ==================================================
# 检查3：根据订单明细重新计算采购总量
# ==================================================

print("\n【检查3：采购数量汇总检查】")
print("-" * 65)

ordered_summary = (
    details.groupby("order_id")
    .agg(
        calculated_ordered_quantity=(
            "purchase_quantity",
            "sum"
        )
    )
    .reset_index()
)

ordered_check = orders.merge(
    ordered_summary,
    on="order_id",
    how="left",
    validate="one_to_one"
)

ordered_check["calculated_ordered_quantity"] = (
    ordered_check["calculated_ordered_quantity"]
    .fillna(0)
)

ordered_diff = (
    ordered_check["ordered_quantity"]
    != ordered_check["calculated_ordered_quantity"]
)

ordered_error_count = ordered_diff.sum()

check_result(
    "订单主表采购总量与订单明细汇总一致",
    ordered_error_count == 0,
    ordered_error_count
)


# ==================================================
# 检查4：根据到货记录重新计算累计到货量
# ==================================================

print("\n【检查4：实际到货数量汇总检查】")
print("-" * 65)

received_summary = (
    receipts.groupby("order_id")
    .agg(
        calculated_received_quantity=(
            "received_quantity",
            "sum"
        )
    )
    .reset_index()
)

received_check = orders.merge(
    received_summary,
    on="order_id",
    how="left",
    validate="one_to_one"
)

received_check["calculated_received_quantity"] = (
    received_check["calculated_received_quantity"]
    .fillna(0)
)

received_diff = (
    received_check["received_quantity"]
    != received_check["calculated_received_quantity"]
)

received_error_count = received_diff.sum()

check_result(
    "订单主表累计到货量与到货记录汇总一致",
    received_error_count == 0,
    received_error_count
)


# ==================================================
# 检查5：待到货数量计算逻辑
# ==================================================

print("\n【检查5：待到货数量计算逻辑】")
print("-" * 65)

calculated_pending = (
    orders["ordered_quantity"]
    - orders["received_quantity"]
)

pending_diff = (
    orders["pending_quantity"]
    != calculated_pending
)

pending_error_count = pending_diff.sum()

check_result(
    "待到货数量 = 采购总量 - 累计到货量",
    pending_error_count == 0,
    pending_error_count
)


# ==================================================
# 检查6：数量合理性检查
# ==================================================

print("\n【检查6：订单数量合理性检查】")
print("-" * 65)

quantity_columns = [
    "ordered_quantity",
    "received_quantity",
    "pending_quantity"
]

for column in quantity_columns:

    abnormal_count = (
        orders[column] < 0
    ).sum()

    check_result(
        f"{column} 不存在负数",
        abnormal_count == 0,
        abnormal_count
    )

over_received_count = (
    orders["received_quantity"]
    > orders["ordered_quantity"]
).sum()

check_result(
    "累计到货量不超过采购总量",
    over_received_count == 0,
    over_received_count
)


# ==================================================
# 检查7：订单状态判定逻辑
# ==================================================

print("\n【检查7：订单状态判定逻辑】")
print("-" * 65)


def calculate_expected_status(row):

    if row["received_quantity"] == 0:
        return "运输中"

    elif row["received_quantity"] < row["ordered_quantity"]:
        return "部分到货"

    else:
        return "已完成"


expected_status = orders.apply(
    calculate_expected_status,
    axis=1
)

status_diff = (
    orders["order_status"] != expected_status
)

status_error_count = status_diff.sum()

check_result(
    "订单状态与累计到货数量判定规则一致",
    status_error_count == 0,
    status_error_count
)


# ==================================================
# 检查8：订单状态取值范围
# ==================================================

print("\n【检查8：订单状态取值范围】")
print("-" * 65)

valid_status = [
    "已完成",
    "部分到货",
    "运输中"
]

invalid_status_count = (
    ~orders["order_status"].isin(valid_status)
).sum()

check_result(
    "订单状态仅包含规定的三种状态",
    invalid_status_count == 0,
    invalid_status_count
)


# ==================================================
# 检查9：订单状态与数量关系
# ==================================================

print("\n【检查9：订单状态与数量关系】")
print("-" * 65)

completed_error = (
    (
        orders["order_status"] == "已完成"
    )
    &
    (
        orders["received_quantity"]
        != orders["ordered_quantity"]
    )
).sum()

check_result(
    "已完成订单的累计到货量等于采购总量",
    completed_error == 0,
    completed_error
)

partial_error = (
    (
        orders["order_status"] == "部分到货"
    )
    &
    (
        (
            orders["received_quantity"] <= 0
        )
        |
        (
            orders["received_quantity"]
            >= orders["ordered_quantity"]
        )
    )
).sum()

check_result(
    "部分到货订单的到货量大于0且小于采购总量",
    partial_error == 0,
    partial_error
)

transport_error = (
    (
        orders["order_status"] == "运输中"
    )
    &
    (
        orders["received_quantity"] != 0
    )
).sum()

check_result(
    "运输中订单的累计到货量为0",
    transport_error == 0,
    transport_error
)


# ==================================================
# 检查10：采购订单与到货记录关联
# ==================================================

print("\n【检查10：采购订单与到货记录关联】")
print("-" * 65)

receipt_order_check = receipts.merge(
    orders[
        ["order_id", "supplier_id", "supplier_name"]
    ],
    on="order_id",
    how="left",
    suffixes=("_receipt", "_order"),
    indicator=True,
    validate="many_to_one"
)

orphan_count = (
    receipt_order_check["_merge"] != "both"
).sum()

check_result(
    "所有到货记录均能关联更新后的采购订单",
    orphan_count == 0,
    orphan_count
)

valid_receipts = receipt_order_check[
    receipt_order_check["_merge"] == "both"
]

supplier_diff = (
    valid_receipts["supplier_id_receipt"]
    != valid_receipts["supplier_id_order"]
)

supplier_error_count = supplier_diff.sum()

check_result(
    "到货记录与订单主表供应商ID一致",
    supplier_error_count == 0,
    supplier_error_count
)


# ==================================================
# 检查11：订单汇总数量与全局数量一致
# ==================================================

print("\n【检查11：全局采购数量汇总】")
print("-" * 65)

total_ordered = orders["ordered_quantity"].sum()
total_received = orders["received_quantity"].sum()
total_pending = orders["pending_quantity"].sum()

detail_total = details["purchase_quantity"].sum()
receipt_total = receipts["received_quantity"].sum()

check_result(
    "订单主表采购总量与采购明细总量一致",
    total_ordered == detail_total,
    abs(total_ordered - detail_total)
)

check_result(
    "订单主表累计到货量与到货记录总量一致",
    total_received == receipt_total,
    abs(total_received - receipt_total)
)

check_result(
    "全局待到货量 = 采购总量 - 累计到货量",
    total_pending == total_ordered - total_received,
    abs(total_pending - (total_ordered - total_received))
)


# ==================================================
# 12. 输出结果
# ==================================================

print("\n" + "=" * 65)
print("采购订单状态业务逻辑检查汇总")
print("=" * 65)

print(f"检查项目数量：{total_checks}")
print(f"通过项目数量：{passed_checks}")
print(f"异常项目数量：{failed_checks}")

print("\n采购数量汇总：")
print(f"采购总量：{total_ordered:,}")
print(f"累计到货量：{total_received:,}")
print(f"待到货量：{total_pending:,}")

print("\n订单状态分布：")
print(
    orders["order_status"]
    .value_counts()
    .to_string()
)

if failed_checks == 0:
    print("\nPASS：所有采购订单状态业务逻辑检查均通过！")
else:
    print("\nFAIL：存在未通过的检查，请根据上方结果排查。")

print("=" * 65)
