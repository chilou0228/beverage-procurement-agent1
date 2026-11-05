from pathlib import Path
import pandas as pd

# ==================================================
# 1. 读取数据
# ==================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

receipts = pd.read_csv(
    PROJECT_ROOT / "data" / "processed" / "purchase_receipts.csv"
)

orders = pd.read_csv(
    PROJECT_ROOT / "data" / "processed" / "purchase_orders.csv"
)

details = pd.read_csv(
    PROJECT_ROOT / "data" / "processed" / "purchase_order_details.csv"
)

print("=" * 65)
print("酒水采销 Agent｜采购到货业务逻辑检查")
print("=" * 65)

print(f"\n到货记录数量：{len(receipts):,}")
print(f"采购订单数量：{len(orders):,}")
print(f"采购订单明细数量：{len(details):,}")


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
# 检查1：到货记录基础字段空值检查
# ==================================================

print("\n【检查1：到货记录基础字段空值检查】")
print("-" * 65)

required_columns = [
    "receipt_id",
    "order_id",
    "supplier_id",
    "supplier_name",
    "sku_id",
    "product_name",
    "category_name",
    "ordered_quantity",
    "received_quantity",
    "receipt_date",
    "expected_arrival_date"
]

for column in required_columns:

    missing_count = receipts[column].isna().sum()

    check_result(
        f"{column} 空值检查",
        missing_count == 0,
        missing_count
    )


# ==================================================
# 检查2：到货数量数值检查
# ==================================================

print("\n【检查2：到货数量数值检查】")
print("-" * 65)

numeric_columns = [
    "ordered_quantity",
    "received_quantity"
]

for column in numeric_columns:

    abnormal_count = (receipts[column] < 0).sum()

    check_result(
        f"{column} 非负检查",
        abnormal_count == 0,
        abnormal_count
    )

zero_received_count = (
    receipts["received_quantity"] <= 0
).sum()

check_result(
    "到货记录中的实际到货数量必须大于0",
    zero_received_count == 0,
    zero_received_count
)


# ==================================================
# 检查3：到货记录日期格式检查
# ==================================================

print("\n【检查3：到货记录日期格式检查】")
print("-" * 65)

receipts["receipt_date"] = pd.to_datetime(
    receipts["receipt_date"],
    errors="coerce"
)

receipts["expected_arrival_date"] = pd.to_datetime(
    receipts["expected_arrival_date"],
    errors="coerce"
)

invalid_receipt_date = (
    receipts["receipt_date"].isna().sum()
)

invalid_expected_date = (
    receipts["expected_arrival_date"].isna().sum()
)

check_result(
    "实际到货日期格式检查",
    invalid_receipt_date == 0,
    invalid_receipt_date
)

check_result(
    "预计到货日期格式检查",
    invalid_expected_date == 0,
    invalid_expected_date
)


# ==================================================
# 检查4：到货日期合理性检查
# ==================================================

print("\n【检查4：到货日期合理性检查】")
print("-" * 65)

orders_date_check = orders[
    ["order_id", "order_date"]
].copy()

orders_date_check["order_date"] = pd.to_datetime(
    orders_date_check["order_date"],
    errors="coerce"
)

receipt_date_check = receipts.merge(
    orders_date_check,
    on="order_id",
    how="left",
    validate="many_to_one"
)

early_receipt_count = (
    receipt_date_check["receipt_date"]
    < receipt_date_check["order_date"]
).sum()

check_result(
    "实际到货日期不早于采购订单日期",
    early_receipt_count == 0,
    early_receipt_count
)

late_receipt_count = (
    receipts["receipt_date"] > pd.Timestamp("2026-10-23")
).sum()

check_result(
    "实际到货日期不晚于模拟截止日期2026-10-23",
    late_receipt_count == 0,
    late_receipt_count
)


# ==================================================
# 检查5：到货数量与采购订单明细一致性检查
# ==================================================

print("\n【检查5：到货数量与采购订单明细一致性检查】")
print("-" * 65)

detail_reference = details[
    [
        "order_id",
        "sku_id",
        "supplier_id",
        "purchase_quantity"
    ]
].copy()

receipt_detail_check = receipts.merge(
    detail_reference,
    on=["order_id", "sku_id"],
    how="left",
    suffixes=("_receipt", "_detail"),
    indicator=True,
    validate="many_to_one"
)

unknown_detail_count = (
    receipt_detail_check["_merge"] != "both"
).sum()

check_result(
    "到货记录均能关联对应采购订单商品明细",
    unknown_detail_count == 0,
    unknown_detail_count
)

valid_receipt_detail = receipt_detail_check[
    receipt_detail_check["_merge"] == "both"
].copy()

ordered_quantity_diff = (
    valid_receipt_detail["ordered_quantity"]
    - valid_receipt_detail["purchase_quantity"]
).abs()

ordered_quantity_error_count = (
    ordered_quantity_diff > 0
).sum()

check_result(
    "到货记录采购数量与订单明细一致",
    ordered_quantity_error_count == 0,
    ordered_quantity_error_count
)

supplier_diff = (
    valid_receipt_detail["supplier_id_receipt"]
    != valid_receipt_detail["supplier_id_detail"]
)

supplier_error_count = (
    supplier_diff.fillna(True)
).sum()

check_result(
    "到货供应商与订单商品明细供应商一致",
    supplier_error_count == 0,
    supplier_error_count
)


# ==================================================
# 检查6：累计到货数量不能超过采购数量
# ==================================================

print("\n【检查6：累计到货数量上限检查】")
print("-" * 65)

receipt_summary = (
    receipts.groupby(
        ["order_id", "sku_id"]
    )["received_quantity"]
    .sum()
    .reset_index()
    .rename(columns={
        "received_quantity": "total_received_quantity"
    })
)

quantity_check = details.merge(
    receipt_summary,
    on=["order_id", "sku_id"],
    how="left"
)

quantity_check["total_received_quantity"] = (
    quantity_check["total_received_quantity"].fillna(0)
)

over_received_count = (
    quantity_check["total_received_quantity"]
    > quantity_check["purchase_quantity"]
).sum()

check_result(
    "订单商品累计到货数量不超过采购数量",
    over_received_count == 0,
    over_received_count
)


# ==================================================
# 检查7：分批到货检查
# ==================================================

print("\n【检查7：分批到货检查】")
print("-" * 65)

receipt_group_count = (
    receipts.groupby(
        ["order_id", "sku_id"]
    ).size()
)

split_delivery_count = (
    receipt_group_count > 1
).sum()

check_result(
    "存在分批到货记录",
    split_delivery_count > 0,
    0 if split_delivery_count > 0 else 1
)

print(
    f"发生分批到货的订单-SKU组合数量："
    f"{split_delivery_count}"
)


# ==================================================
# 检查8：到货记录唯一性检查
# ==================================================

print("\n【检查8：到货记录唯一性检查】")
print("-" * 65)

duplicate_receipt_count = (
    receipts["receipt_id"].duplicated().sum()
)

check_result(
    "到货记录ID不存在重复",
    duplicate_receipt_count == 0,
    duplicate_receipt_count
)


# ==================================================
# 检查9：订单与供应商关联检查
# ==================================================

print("\n【检查9：订单与供应商关联检查】")
print("-" * 65)

order_reference = orders[
    ["order_id", "supplier_id", "supplier_name"]
].copy()

receipt_order_check = receipts.merge(
    order_reference,
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
    "到货记录均能关联采购订单主表",
    orphan_count == 0,
    orphan_count
)

valid_order_receipts = receipt_order_check[
    receipt_order_check["_merge"] == "both"
]

supplier_id_diff = (
    valid_order_receipts["supplier_id_receipt"]
    != valid_order_receipts["supplier_id_order"]
)

supplier_id_error_count = (
    supplier_id_diff.fillna(True)
).sum()

check_result(
    "到货记录供应商ID与订单主表一致",
    supplier_id_error_count == 0,
    supplier_id_error_count
)

supplier_name_diff = (
    valid_order_receipts["supplier_name_receipt"]
    != valid_order_receipts["supplier_name_order"]
)

supplier_name_error_count = (
    supplier_name_diff.fillna(True)
).sum()

check_result(
    "到货记录供应商名称与订单主表一致",
    supplier_name_error_count == 0,
    supplier_name_error_count
)


# ==================================================
# 检查10：预计到货日期与订单主表一致性检查
# ==================================================

print("\n【检查10：预计到货日期一致性检查】")
print("-" * 65)

valid_date_receipts = valid_order_receipts.copy()

valid_date_receipts["expected_arrival_date_order"] = (
    pd.to_datetime(
        valid_date_receipts["order_id"].map(
            orders.set_index("order_id")[
                "expected_arrival_date"
            ]
        ),
        errors="coerce"
    )
)

expected_date_diff = (
    valid_date_receipts["expected_arrival_date"]
    != valid_date_receipts["expected_arrival_date_order"]
)

expected_date_error_count = (
    expected_date_diff.fillna(True)
).sum()

check_result(
    "到货记录预计日期与订单主表一致",
    expected_date_error_count == 0,
    expected_date_error_count
)


# ==================================================
# 检查11：到货日期与预计日期关系检查
# ==================================================

print("\n【检查11：实际到货日期与预计日期关系检查】")
print("-" * 65)

valid_date_receipts = valid_date_receipts[
    valid_date_receipts["receipt_date"].notna()
    & valid_date_receipts["expected_arrival_date"].notna()
]

delay_days = (
    valid_date_receipts["receipt_date"]
    - valid_date_receipts["expected_arrival_date"]
).dt.days

abnormal_delay_count = (
    (delay_days < -2) | (delay_days > 7)
).sum()

check_result(
    "实际到货日期处于预计日期提前2天至延迟7天范围",
    abnormal_delay_count == 0,
    abnormal_delay_count
)


# ==================================================
# 检查12：到货记录商品信息检查
# ==================================================

print("\n【检查12：到货记录商品信息检查】")
print("-" * 65)

product_reference = details[
    [
        "order_id",
        "sku_id",
        "product_name",
        "category_name"
    ]
].drop_duplicates(
    subset=["order_id", "sku_id"]
)

product_check = receipts.merge(
    product_reference,
    on=["order_id", "sku_id"],
    how="left",
    suffixes=("_receipt", "_detail"),
    validate="many_to_one"
)

product_name_diff = (
    product_check["product_name_receipt"]
    != product_check["product_name_detail"]
)

product_name_error_count = (
    product_name_diff.fillna(True)
).sum()

check_result(
    "到货商品名称与订单明细一致",
    product_name_error_count == 0,
    product_name_error_count
)

category_diff = (
    product_check["category_name_receipt"]
    != product_check["category_name_detail"]
)

category_error_count = (
    category_diff.fillna(True)
).sum()

check_result(
    "到货商品品类与订单明细一致",
    category_error_count == 0,
    category_error_count
)


# ==================================================
# 13. 检查结果汇总
# ==================================================

print("\n" + "=" * 65)
print("采购到货业务逻辑检查汇总")
print("=" * 65)

print(f"检查项目数量：{total_checks}")
print(f"通过项目数量：{passed_checks}")
print(f"异常项目数量：{failed_checks}")

if failed_checks == 0:
    print("\nPASS：所有采购到货业务逻辑检查均通过！")
else:
    print("\nFAIL：存在未通过的采购到货业务逻辑检查，请根据上方结果排查。")

print("=" * 65)