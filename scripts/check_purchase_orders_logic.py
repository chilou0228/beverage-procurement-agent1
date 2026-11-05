from pathlib import Path
import pandas as pd

# ==================================================
# 1. 读取数据
# ==================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

orders = pd.read_csv(
    PROJECT_ROOT / "data" / "processed" / "purchase_orders.csv"
)

details = pd.read_csv(
    PROJECT_ROOT / "data" / "processed" / "purchase_order_details.csv"
)

suppliers = pd.read_csv(
    PROJECT_ROOT / "data" / "processed" / "suppliers.csv"
)

mapping = pd.read_csv(
    PROJECT_ROOT / "data" / "processed" / "product_supplier_mapping.csv"
)

print("=" * 65)
print("酒水采销 Agent｜采购订单业务逻辑检查")
print("=" * 65)

print(f"\n采购订单数量：{len(orders):,}")
print(f"采购订单明细数量：{len(details):,}")
print(f"涉及供应商数量：{orders['supplier_id'].nunique():,}")


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
# 检查1：采购订单基础字段检查
# ==================================================

print("\n【检查1：采购订单基础字段检查】")
print("-" * 65)

order_required_columns = [
    "order_id",
    "supplier_id",
    "supplier_name",
    "order_date",
    "expected_arrival_date",
    "lead_time_days",
    "total_quantity",
    "order_amount",
    "order_status"
]

for column in order_required_columns:

    missing_count = orders[column].isna().sum()

    check_result(
        f"订单主表 {column} 空值检查",
        missing_count == 0,
        missing_count
    )


# ==================================================
# 检查2：采购订单明细基础字段检查
# ==================================================

print("\n【检查2：采购订单明细基础字段检查】")
print("-" * 65)

detail_required_columns = [
    "order_id",
    "supplier_id",
    "supplier_name",
    "sku_id",
    "product_name",
    "category_name",
    "brand",
    "purchase_quantity",
    "unit_purchase_cost",
    "subtotal"
]

for column in detail_required_columns:

    missing_count = details[column].isna().sum()

    check_result(
        f"订单明细 {column} 空值检查",
        missing_count == 0,
        missing_count
    )


# ==================================================
# 检查3：采购订单数值检查
# ==================================================

print("\n【检查3：采购订单数值检查】")
print("-" * 65)

order_numeric_columns = [
    "lead_time_days",
    "total_quantity",
    "order_amount"
]

for column in order_numeric_columns:

    abnormal_count = (orders[column] < 0).sum()

    check_result(
        f"订单主表 {column} 非负检查",
        abnormal_count == 0,
        abnormal_count
    )

detail_numeric_columns = [
    "purchase_quantity",
    "unit_purchase_cost",
    "subtotal"
]

for column in detail_numeric_columns:

    abnormal_count = (details[column] < 0).sum()

    check_result(
        f"订单明细 {column} 非负检查",
        abnormal_count == 0,
        abnormal_count
    )

zero_quantity_count = (
    details["purchase_quantity"] <= 0
).sum()

check_result(
    "采购明细数量必须大于0",
    zero_quantity_count == 0,
    zero_quantity_count
)


# ==================================================
# 检查4：采购订单金额计算检查
# ==================================================

print("\n【检查4：采购订单金额计算检查】")
print("-" * 65)

expected_subtotal = (
    details["purchase_quantity"]
    * details["unit_purchase_cost"]
).round(2)

subtotal_diff = (
    details["subtotal"] - expected_subtotal
).abs()

subtotal_error_count = (
    subtotal_diff > 0.02
).sum()

check_result(
    "订单明细金额 = 采购数量 × 单位采购报价",
    subtotal_error_count == 0,
    subtotal_error_count
)

detail_summary = (
    details.groupby("order_id")
    .agg(
        detail_total_quantity=(
            "purchase_quantity", "sum"
        ),
        detail_total_amount=(
            "subtotal", "sum"
        )
    )
    .reset_index()
)

order_check = orders.merge(
    detail_summary,
    on="order_id",
    how="left",
    validate="one_to_one"
)

order_check["detail_total_quantity"] = (
    order_check["detail_total_quantity"].fillna(0)
)

order_check["detail_total_amount"] = (
    order_check["detail_total_amount"].fillna(0)
)

quantity_diff = (
    order_check["total_quantity"]
    - order_check["detail_total_quantity"]
).abs()

quantity_error_count = (
    quantity_diff > 0
).sum()

check_result(
    "订单总数量 = 所有商品明细采购数量之和",
    quantity_error_count == 0,
    quantity_error_count
)

amount_diff = (
    order_check["order_amount"]
    - order_check["detail_total_amount"]
).abs()

amount_error_count = (
    amount_diff > 0.02
).sum()

check_result(
    "订单总金额 = 所有商品明细金额之和",
    amount_error_count == 0,
    amount_error_count
)


# ==================================================
# 检查5：采购订单日期检查
# ==================================================

print("\n【检查5：采购订单日期检查】")
print("-" * 65)

orders["order_date"] = pd.to_datetime(
    orders["order_date"],
    errors="coerce"
)

orders["expected_arrival_date"] = pd.to_datetime(
    orders["expected_arrival_date"],
    errors="coerce"
)

invalid_order_date = orders["order_date"].isna().sum()

invalid_arrival_date = (
    orders["expected_arrival_date"].isna().sum()
)

check_result(
    "订单日期格式检查",
    invalid_order_date == 0,
    invalid_order_date
)

check_result(
    "预计到货日期格式检查",
    invalid_arrival_date == 0,
    invalid_arrival_date
)

if invalid_order_date == 0:

    date_abnormal = (
        (orders["order_date"] < pd.Timestamp("2026-07-26"))
        | (orders["order_date"] > pd.Timestamp("2026-10-23"))
    ).sum()

    check_result(
        "订单日期处于2026-07-26至2026-10-23范围内",
        date_abnormal == 0,
        date_abnormal
    )

if invalid_order_date == 0 and invalid_arrival_date == 0:

    negative_date_diff = (
        orders["expected_arrival_date"]
        < orders["order_date"]
    ).sum()

    check_result(
        "预计到货日期不早于订单日期",
        negative_date_diff == 0,
        negative_date_diff
    )


# ==================================================
# 检查6：供应商交期检查
# ==================================================

print("\n【检查6：供应商交期检查】")
print("-" * 65)

supplier_info = suppliers[
    ["supplier_id", "supplier_name", "avg_lead_time_days"]
].copy()

order_supplier_check = orders.merge(
    supplier_info,
    on="supplier_id",
    how="left",
    suffixes=("_order", "_supplier"),
    validate="many_to_one"
)

unknown_supplier_count = (
    order_supplier_check["supplier_name_supplier"].isna()
).sum()

check_result(
    "订单供应商均存在于供应商档案",
    unknown_supplier_count == 0,
    unknown_supplier_count
)

supplier_name_diff = (
    order_supplier_check["supplier_name_order"]
    != order_supplier_check["supplier_name_supplier"]
)

supplier_name_error_count = (
    supplier_name_diff.fillna(True)
).sum()

check_result(
    "订单供应商名称与供应商档案一致",
    supplier_name_error_count == 0,
    supplier_name_error_count
)

lead_time_diff = (
    order_supplier_check["lead_time_days"]
    - order_supplier_check["avg_lead_time_days"]
).abs()

lead_time_error_count = (
    lead_time_diff > 0
).sum()

check_result(
    "订单交期与供应商平均交期一致",
    lead_time_error_count == 0,
    lead_time_error_count
)

if invalid_order_date == 0 and invalid_arrival_date == 0:

    expected_arrival = (
        orders["order_date"]
        + pd.to_timedelta(
            orders["lead_time_days"],
            unit="D"
        )
    )

    arrival_diff = (
        orders["expected_arrival_date"]
        != expected_arrival
    )

    arrival_error_count = arrival_diff.sum()

    check_result(
        "预计到货日期 = 订单日期 + 供应商交期",
        arrival_error_count == 0,
        arrival_error_count
    )


# ==================================================
# 检查7：商品与主供应商关系检查
# ==================================================

print("\n【检查7：商品与主供应商关系检查】")
print("-" * 65)

primary_mapping = mapping[
    mapping["is_primary"].astype(str).str.lower().isin(
        ["true", "1"]
    )
].copy()

# 每个SKU只允许有一个主供应商
primary_count = (
    primary_mapping.groupby("sku_id")
    .size()
)

duplicate_primary_count = (
    primary_count > 1
).sum()

check_result(
    "每个SKU最多只有一个主供应商",
    duplicate_primary_count == 0,
    duplicate_primary_count
)

# 订单明细关联主供应商报价
primary_info = primary_mapping[
    [
        "sku_id",
        "supplier_id",
        "supplier_quote_cost"
    ]
].copy()

detail_mapping_check = details.merge(
    primary_info,
    on=["sku_id", "supplier_id"],
    how="left",
    indicator=True
)

mapping_error_count = (
    detail_mapping_check["_merge"] != "both"
).sum()

check_result(
    "订单商品均由对应的主供应商提供",
    mapping_error_count == 0,
    mapping_error_count
)

# 检查采购报价
valid_mapping = detail_mapping_check[
    detail_mapping_check["_merge"] == "both"
]

quote_diff = (
    valid_mapping["unit_purchase_cost"]
    - valid_mapping["supplier_quote_cost"]
).abs()

quote_error_count = (
    quote_diff > 0.02
).sum()

check_result(
    "订单采购报价与主供应商报价一致",
    quote_error_count == 0,
    quote_error_count
)


# ==================================================
# 检查8：订单明细与订单主表关联检查
# ==================================================

print("\n【检查8：订单明细与订单主表关联检查】")
print("-" * 65)

order_ids = set(orders["order_id"])
detail_order_ids = set(details["order_id"])

orphan_details = detail_order_ids - order_ids
orders_without_details = order_ids - detail_order_ids

check_result(
    "订单明细均能关联订单主表",
    len(orphan_details) == 0,
    len(orphan_details)
)

check_result(
    "每张订单至少有一条商品明细",
    len(orders_without_details) == 0,
    len(orders_without_details)
)

detail_supplier_check = details.merge(
    orders[["order_id", "supplier_id"]],
    on="order_id",
    how="left",
    suffixes=("_detail", "_order"),
    validate="many_to_one"
)

detail_supplier_diff = (
    detail_supplier_check["supplier_id_detail"]
    != detail_supplier_check["supplier_id_order"]
)

detail_supplier_error_count = (
    detail_supplier_diff.fillna(True)
).sum()

check_result(
    "订单明细供应商与订单主表供应商一致",
    detail_supplier_error_count == 0,
    detail_supplier_error_count
)


# ==================================================
# 检查9：订单ID与商品明细唯一性检查
# ==================================================

print("\n【检查9：订单ID与商品明细唯一性检查】")
print("-" * 65)

duplicate_order_count = (
    orders["order_id"].duplicated().sum()
)

check_result(
    "订单ID不存在重复",
    duplicate_order_count == 0,
    duplicate_order_count
)

duplicate_detail_count = (
    details.duplicated(
        subset=["order_id", "sku_id"]
    ).sum()
)

check_result(
    "同一订单内同一SKU不存在重复明细",
    duplicate_detail_count == 0,
    duplicate_detail_count
)


# ==================================================
# 检查10：订单状态检查
# ==================================================

print("\n【检查10：订单状态检查】")
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
    "订单状态属于预设状态范围",
    invalid_status_count == 0,
    invalid_status_count
)


# ==================================================
# 11. 检查结果汇总
# ==================================================

print("\n" + "=" * 65)
print("采购订单业务逻辑检查汇总")
print("=" * 65)

print(f"检查项目数量：{total_checks}")
print(f"通过项目数量：{passed_checks}")
print(f"异常项目数量：{failed_checks}")

if failed_checks == 0:
    print("\nPASS：所有采购订单业务逻辑检查均通过！")
else:
    print("\nFAIL：存在未通过的采购订单业务逻辑检查，请根据上方结果排查。")

print("=" * 65)
