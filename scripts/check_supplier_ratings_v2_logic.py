
from pathlib import Path
import numpy as np
import pandas as pd

# ==================================================
# 1. 路径与基础参数
# ==================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "processed"

CUTOFF_DATE = pd.Timestamp("2026-10-23")

WEIGHTS = {
    "fulfillment_score": 0.40,
    "timeliness_score": 0.35,
    "completion_score": 0.25
}

suppliers = pd.read_csv(DATA_DIR / "suppliers.csv")
orders = pd.read_csv(DATA_DIR / "purchase_orders.csv")
details = pd.read_csv(DATA_DIR / "purchase_order_details.csv")
receipts = pd.read_csv(DATA_DIR / "purchase_receipts.csv")
ratings = pd.read_csv(DATA_DIR / "supplier_ratings_v2.csv")

print("=" * 65)
print("酒水采销 Agent｜供应商综合评分业务逻辑检查")
print("=" * 65)

print(f"\n供应商档案：{len(suppliers)}")
print(f"采购订单：{len(orders)}")
print(f"采购明细：{len(details)}")
print(f"到货记录：{len(receipts)}")
print(f"评分记录：{len(ratings)}")


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


def compare_numeric(actual, expected, tolerance=1e-8):
    actual = pd.to_numeric(actual, errors="coerce")
    expected = pd.to_numeric(expected, errors="coerce")

    both_nan = actual.isna() & expected.isna()
    both_valid = actual.notna() & expected.notna()

    equal = both_nan.copy()

    equal.loc[both_valid] = (
        (actual.loc[both_valid] - expected.loc[both_valid]).abs()
        <= tolerance
    )

    return equal


# ==================================================
# 3. 基础字段检查
# ==================================================

print("\n【检查1：评分表字段完整性】")
print("-" * 65)

required_columns = [
    "supplier_id",
    "supplier_name",
    "region",
    "main_category",
    "supplier_level",
    "status",
    "due_order_count",
    "due_quantity",
    "due_received_quantity",
    "fulfillment_rate",
    "due_completed_orders",
    "order_completion_rate",
    "timing_received_quantity",
    "on_time_quantity",
    "on_time_delivery_rate",
    "fulfillment_score",
    "timeliness_score",
    "completion_score",
    "total_score",
    "supplier_grade",
    "evaluation_status",
    "cooperation_strategy"
]

missing_columns = [
    col for col in required_columns
    if col not in ratings.columns
]

check_result(
    "评分表包含全部必要字段",
    len(missing_columns) == 0,
    len(missing_columns)
)

if missing_columns:
    raise ValueError(
        f"评分表缺少字段：{missing_columns}"
    )

for column in [
    "supplier_id",
    "supplier_name",
    "supplier_grade",
    "evaluation_status",
    "cooperation_strategy"
]:
    missing_count = ratings[column].isna().sum()

    check_result(
        f"{column} 不存在空值",
        missing_count == 0,
        missing_count
    )


# ==================================================
# 4. 供应商数量和唯一性检查
# ==================================================

print("\n【检查2：供应商覆盖与唯一性】")
print("-" * 65)

check_result(
    "评分记录数量与供应商档案数量一致",
    len(ratings) == len(suppliers),
    abs(len(ratings) - len(suppliers))
)

duplicate_count = ratings["supplier_id"].duplicated().sum()

check_result(
    "评分表 supplier_id 唯一",
    duplicate_count == 0,
    duplicate_count
)

missing_ids = (
    set(suppliers["supplier_id"])
    - set(ratings["supplier_id"])
)

extra_ids = (
    set(ratings["supplier_id"])
    - set(suppliers["supplier_id"])
)

check_result(
    "评分表完整覆盖供应商档案",
    len(missing_ids) == 0 and len(extra_ids) == 0,
    len(missing_ids) + len(extra_ids)
)


# ==================================================
# 5. 供应商基础信息检查
# ==================================================

print("\n【检查3：供应商基础信息一致性】")
print("-" * 65)

supplier_reference = suppliers[
    [
        "supplier_id",
        "supplier_name",
        "region",
        "main_category",
        "supplier_level",
        "status"
    ]
]

supplier_check = ratings.merge(
    supplier_reference,
    on="supplier_id",
    how="left",
    suffixes=("_result", "_source"),
    validate="one_to_one"
)

for column in [
    "supplier_name",
    "region",
    "main_category",
    "supplier_level",
    "status"
]:
    diff = (
        supplier_check[f"{column}_result"]
        != supplier_check[f"{column}_source"]
    )

    error_count = diff.fillna(True).sum()

    check_result(
        f"评分表 {column} 与供应商档案一致",
        error_count == 0,
        error_count
    )


# ==================================================
# 6. 日期与数量处理
# ==================================================

print("\n【检查4：基础数据日期和数量处理】")
print("-" * 65)

orders["expected_arrival_date"] = pd.to_datetime(
    orders["expected_arrival_date"],
    errors="coerce"
)

details["purchase_quantity"] = pd.to_numeric(
    details["purchase_quantity"],
    errors="coerce"
)

receipts["received_quantity"] = pd.to_numeric(
    receipts["received_quantity"],
    errors="coerce"
)

receipts["receipt_date"] = pd.to_datetime(
    receipts["receipt_date"],
    errors="coerce"
)

check_result(
    "采购订单预计到货日期不存在无效值",
    orders["expected_arrival_date"].notna().all(),
    orders["expected_arrival_date"].isna().sum()
)

check_result(
    "采购明细采购数量不存在无效值",
    details["purchase_quantity"].notna().all(),
    details["purchase_quantity"].isna().sum()
)

check_result(
    "到货记录到货数量不存在无效值",
    receipts["received_quantity"].notna().all(),
    receipts["received_quantity"].isna().sum()
)

check_result(
    "到货记录实际日期不存在无效值",
    receipts["receipt_date"].notna().all(),
    receipts["receipt_date"].isna().sum()
)


# ==================================================
# 7. 重新关联采购明细与订单
# ==================================================

print("\n【检查5：采购明细与订单关联】")
print("-" * 65)

order_info = orders[
    [
        "order_id",
        "supplier_id",
        "order_date",
        "expected_arrival_date"
    ]
].copy()

duplicate_order_count = orders["order_id"].duplicated().sum()

check_result(
    "采购订单主表 order_id 唯一",
    duplicate_order_count == 0,
    duplicate_order_count
)

detail_data = details.merge(
    order_info,
    on=["order_id", "supplier_id"],
    how="left",
    validate="many_to_one",
    indicator=True
)

unmatched_detail_count = (
    detail_data["_merge"] != "both"
).sum()

check_result(
    "采购明细均能关联对应订单",
    unmatched_detail_count == 0,
    unmatched_detail_count
)

detail_data = detail_data.drop(columns=["_merge"])


# ==================================================
# 8. 重新计算累计到货数量
# ==================================================

print("\n【检查6：采购明细与到货记录关联】")
print("-" * 65)

receipt_summary = (
    receipts.groupby(
        ["order_id", "supplier_id", "sku_id"],
        as_index=False
    )
    .agg(
        calculated_received_quantity=(
            "received_quantity",
            "sum"
        )
    )
)

detail_data = detail_data.merge(
    receipt_summary,
    on=["order_id", "supplier_id", "sku_id"],
    how="left",
    validate="one_to_one"
)

detail_data["calculated_received_quantity"] = (
    detail_data["calculated_received_quantity"].fillna(0)
)

over_received = (
    detail_data["calculated_received_quantity"]
    > detail_data["purchase_quantity"]
)

check_result(
    "采购明细累计到货量不超过采购数量",
    over_received.sum() == 0,
    over_received.sum()
)

orphan_receipt = receipts.merge(
    details[
        ["order_id", "supplier_id", "sku_id"]
    ].drop_duplicates(),
    on=["order_id", "supplier_id", "sku_id"],
    how="left",
    indicator=True
)

orphan_receipt_count = (
    orphan_receipt["_merge"] != "both"
).sum()

check_result(
    "全部到货记录均能关联采购明细",
    orphan_receipt_count == 0,
    orphan_receipt_count
)


# ==================================================
# 9. 重新识别到期和未到期订单
# ==================================================

print("\n【检查7：到期订单划分】")
print("-" * 65)

detail_data["is_due"] = (
    detail_data["expected_arrival_date"]
    <= CUTOFF_DATE
)

due_details = detail_data[
    detail_data["is_due"]
].copy()

future_details = detail_data[
    ~detail_data["is_due"]
].copy()

print(f"重新计算的到期明细：{len(due_details)}")
print(f"重新计算的未到期明细：{len(future_details)}")

check_result(
    "到期明细和未到期明细合计等于全部明细",
    len(due_details) + len(future_details) == len(details),
    abs(len(details) - len(due_details) - len(future_details))
)


# ==================================================
# 10. 重新计算到期履约率
# ==================================================

print("\n【检查8：到期订单履约率】")
print("-" * 65)

due_stats = (
    due_details.groupby("supplier_id")
    .agg(
        calc_due_quantity=("purchase_quantity", "sum"),
        calc_due_received_quantity=(
            "calculated_received_quantity",
            "sum"
        ),
        calc_due_order_count=("order_id", "nunique")
    )
    .reset_index()
)

due_stats["calc_fulfillment_rate"] = (
    due_stats["calc_due_received_quantity"]
    / due_stats["calc_due_quantity"].replace(0, np.nan)
)

check_data = ratings.merge(
    due_stats,
    on="supplier_id",
    how="left",
    validate="one_to_one"
)

count_columns = [
    "calc_due_quantity",
    "calc_due_received_quantity",
    "calc_due_order_count"
]

for column in count_columns:
    check_data[column] = check_data[column].fillna(0)

for actual_column, expected_column in [
    ("due_quantity", "calc_due_quantity"),
    ("due_received_quantity", "calc_due_received_quantity"),
    ("due_order_count", "calc_due_order_count")
]:
    equal = compare_numeric(
        check_data[actual_column],
        check_data[expected_column]
    )

    check_result(
        f"{actual_column} 与重新计算结果一致",
        equal.all(),
        (~equal).sum()
    )

equal = compare_numeric(
    check_data["fulfillment_rate"],
    check_data["calc_fulfillment_rate"]
)

check_result(
    "到期履约率 = 到期累计到货量 / 到期采购量",
    equal.all(),
    (~equal).sum()
)


# ==================================================
# 11. 重新计算到期订单完成率
# ==================================================

print("\n【检查9：到期订单完成率】")
print("-" * 65)

order_completion = (
    due_details.groupby(
        ["supplier_id", "order_id"],
        as_index=False
    )
    .agg(
        calc_ordered_quantity=("purchase_quantity", "sum"),
        calc_received_quantity=(
            "calculated_received_quantity",
            "sum"
        )
    )
)

order_completion["calc_is_completed"] = (
    order_completion["calc_received_quantity"]
    >= order_completion["calc_ordered_quantity"]
)

completion_stats = (
    order_completion.groupby("supplier_id")
    .agg(
        calc_due_completed_orders=(
            "calc_is_completed",
            "sum"
        ),
        calc_completion_order_count=(
            "order_id",
            "nunique"
        )
    )
    .reset_index()
)

completion_stats["calc_order_completion_rate"] = (
    completion_stats["calc_due_completed_orders"]
    / completion_stats["calc_completion_order_count"].replace(
        0, np.nan
    )
)

check_data = check_data.merge(
    completion_stats,
    on="supplier_id",
    how="left",
    validate="one_to_one"
)

check_data["calc_due_completed_orders"] = (
    check_data["calc_due_completed_orders"].fillna(0)
)

check_data["calc_completion_order_count"] = (
    check_data["calc_completion_order_count"].fillna(0)
)

for actual_column, expected_column in [
    ("due_completed_orders", "calc_due_completed_orders")
]:
    equal = compare_numeric(
        check_data[actual_column],
        check_data[expected_column]
    )

    check_result(
        f"{actual_column} 与重新计算结果一致",
        equal.all(),
        (~equal).sum()
    )

equal = compare_numeric(
    check_data["order_completion_rate"],
    check_data["calc_order_completion_rate"]
)

check_result(
    "到期订单完成率计算正确",
    equal.all(),
    (~equal).sum()
)

check_result(
    "到期订单完成数不超过到期订单数",
    (
        check_data["due_completed_orders"]
        <= check_data["due_order_count"]
    ).all(),
    (
        check_data["due_completed_orders"]
        > check_data["due_order_count"]
    ).sum()
)


# ==================================================
# 12. 重新计算到货及时率
# ==================================================

print("\n【检查10：到货及时率】")
print("-" * 65)

timing_orders = orders[
    ["order_id", "expected_arrival_date"]
].copy()

receipt_timing = receipts.drop(
    columns=["expected_arrival_date"],
    errors="ignore"
).merge(
    timing_orders,
    on="order_id",
    how="left",
    validate="many_to_one"
)

receipt_timing["calc_is_on_time"] = (
    receipt_timing["receipt_date"]
    <= receipt_timing["expected_arrival_date"]
)

receipt_timing["calc_on_time_quantity"] = np.where(
    receipt_timing["calc_is_on_time"],
    receipt_timing["received_quantity"],
    0
)

timing_stats = (
    receipt_timing.groupby("supplier_id")
    .agg(
        calc_timing_received_quantity=(
            "received_quantity",
            "sum"
        ),
        calc_on_time_quantity=(
            "calc_on_time_quantity",
            "sum"
        )
    )
    .reset_index()
)

timing_stats["calc_on_time_delivery_rate"] = (
    timing_stats["calc_on_time_quantity"]
    / timing_stats["calc_timing_received_quantity"].replace(
        0, np.nan
    )
)

check_data = check_data.merge(
    timing_stats,
    on="supplier_id",
    how="left",
    validate="one_to_one"
)

for column in [
    "calc_timing_received_quantity",
    "calc_on_time_quantity"
]:
    check_data[column] = check_data[column].fillna(0)

for actual_column, expected_column in [
    ("timing_received_quantity", "calc_timing_received_quantity"),
    ("on_time_quantity", "calc_on_time_quantity")
]:
    equal = compare_numeric(
        check_data[actual_column],
        check_data[expected_column]
    )

    check_result(
        f"{actual_column} 与重新计算结果一致",
        equal.all(),
        (~equal).sum()
    )

equal = compare_numeric(
    check_data["on_time_delivery_rate"],
    check_data["calc_on_time_delivery_rate"]
)

check_result(
    "到货及时率 = 按时到货数量 / 实际到货数量",
    equal.all(),
    (~equal).sum()
)


# ==================================================
# 13. 重新计算三个评分维度
# ==================================================

print("\n【检查11：评分维度计算】")
print("-" * 65)

check_data["calc_fulfillment_score"] = (
    check_data["calc_fulfillment_rate"] * 100
)

check_data["calc_timeliness_score"] = (
    check_data["calc_on_time_delivery_rate"] * 100
)

check_data["calc_completion_score"] = (
    check_data["calc_order_completion_rate"] * 100
)

for actual_column, expected_column in [
    ("fulfillment_score", "calc_fulfillment_score"),
    ("timeliness_score", "calc_timeliness_score"),
    ("completion_score", "calc_completion_score")
]:
    equal = compare_numeric(
        check_data[actual_column],
        check_data[expected_column]
    )

    check_result(
        f"{actual_column} 与对应比例指标一致",
        equal.all(),
        (~equal).sum()
    )


# ==================================================
# 14. 重新计算综合评分和权重归一化
# ==================================================

print("\n【检查12：综合评分和权重归一化】")
print("-" * 65)

score_mapping = {
    "fulfillment_score": "calc_fulfillment_score",
    "timeliness_score": "calc_timeliness_score",
    "completion_score": "calc_completion_score"
}

weighted_sum = pd.Series(
    0.0,
    index=check_data.index
)

available_weight = pd.Series(
    0.0,
    index=check_data.index
)

for score_name, weight in WEIGHTS.items():

    score = check_data[score_mapping[score_name]]

    valid = score.notna()

    weighted_sum.loc[valid] += (
        score.loc[valid] * weight
    )

    available_weight.loc[valid] += weight

check_data["calc_total_score"] = (
    weighted_sum
    / available_weight.replace(0, np.nan)
).round(2)

equal = compare_numeric(
    ratings["total_score"].reset_index(drop=True),
    check_data["calc_total_score"].reset_index(drop=True)
)

check_result(
    "综合评分与独立计算结果一致",
    equal.all(),
    (~equal).sum()
)

check_result(
    "有效综合评分处于0至100之间",
    ratings["total_score"].dropna().between(0, 100).all(),
    (
        ~ratings["total_score"].dropna().between(0, 100)
    ).sum()
)

no_dimension_count = available_weight.eq(0).sum()

check_result(
    "没有任何有效评分维度的供应商综合评分为空",
    ratings.loc[
        available_weight.eq(0),
        "total_score"
    ].isna().all(),
    (
        ~ratings.loc[
            available_weight.eq(0),
            "total_score"
        ].isna()
    ).sum()
)


# ==================================================
# 15. 重新计算供应商等级
# ==================================================

print("\n【检查13：供应商等级划分】")
print("-" * 65)


def calculate_grade(score):

    if pd.isna(score):
        return "待观察"

    if score >= 85:
        return "A级"

    elif score >= 70:
        return "B级"

    elif score >= 60:
        return "C级"

    return "D级"


expected_grade = check_data["calc_total_score"].apply(
    calculate_grade
)

grade_diff = (
    ratings["supplier_grade"].reset_index(drop=True)
    != expected_grade.reset_index(drop=True)
)

check_result(
    "供应商等级与综合评分区间一致",
    grade_diff.sum() == 0,
    grade_diff.sum()
)


# ==================================================
# 16. 重新计算合作策略
# ==================================================

print("\n【检查14：供应商合作策略】")
print("-" * 65)


def calculate_strategy(row):

    if pd.isna(row["calc_total_score"]):
        return "观察合作：当前缺少有效评价样本，建议积累更多履约记录"

    grade = calculate_grade(row["calc_total_score"])

    if grade == "A级":
        return "重点合作：优先分配采购需求，持续维护战略合作关系"

    if grade == "B级":
        return "稳定合作：维持现有采购合作，关注履约表现"

    if grade == "C级":
        return "审慎合作：控制采购规模，跟踪交付与履约改善情况"

    return "风险控制：降低采购依赖，优先评估备选供应商"


expected_strategy = check_data.apply(
    calculate_strategy,
    axis=1
)

strategy_diff = (
    ratings["cooperation_strategy"].reset_index(drop=True)
    != expected_strategy.reset_index(drop=True)
)

check_result(
    "供应商合作策略与评分等级一致",
    strategy_diff.sum() == 0,
    strategy_diff.sum()
)


# ==================================================
# 17. 重新计算评价样本状态
# ==================================================

print("\n【检查15：评价样本状态】")
print("-" * 65)


def calculate_sample_status(row):

    due_count = row["calc_due_order_count"]
    timing_quantity = row["calc_timing_received_quantity"]

    if due_count == 0 and timing_quantity == 0:
        return "暂无有效评价样本"

    if due_count == 0:
        return "仅有实际到货样本"

    if timing_quantity == 0:
        return "仅有到期订单样本"

    return "有有效评价样本"


expected_sample_status = check_data.apply(
    calculate_sample_status,
    axis=1
)

sample_diff = (
    ratings["evaluation_status"].reset_index(drop=True)
    != expected_sample_status.reset_index(drop=True)
)

check_result(
    "评价样本状态与实际数据情况一致",
    sample_diff.sum() == 0,
    sample_diff.sum()
)


# ==================================================
# 18. 综合评分排序检查
# ==================================================

print("\n【检查16：评分排序检查】")
print("-" * 65)

expected_sorted = ratings.sort_values(
    by=["total_score", "supplier_id"],
    ascending=[False, True],
    na_position="last"
)["supplier_id"].reset_index(drop=True)

actual_sorted = ratings["supplier_id"].reset_index(drop=True)

sort_diff = (
    actual_sorted != expected_sorted
)

check_result(
    "评分表按照综合评分降序、供应商ID升序排列",
    sort_diff.sum() == 0,
    sort_diff.sum()
)


# ==================================================
# 19. 输出检查结果
# ==================================================

print("\n" + "=" * 65)
print("供应商综合评分业务逻辑检查汇总")
print("=" * 65)

print(f"检查项目数量：{total_checks}")
print(f"通过项目数量：{passed_checks}")
print(f"异常项目数量：{failed_checks}")

print("\n供应商评分概况：")

print(f"供应商总数：{len(ratings)}")

print(
    f"有效评分供应商："
    f"{ratings['total_score'].notna().sum()}"
)

print(
    f"待观察供应商："
    f"{(ratings['supplier_grade'] == '待观察').sum()}"
)

print("\n供应商等级分布：")

print(
    ratings["supplier_grade"]
    .value_counts()
    .to_string()
)

print("\n综合评分统计：")

print(
    ratings["total_score"]
    .describe()
    .round(2)
    .to_string()
)

if failed_checks == 0:
    print("\nPASS：所有供应商综合评分业务逻辑检查均通过！")
else:
    print("\nFAIL：存在未通过的检查，请根据上方结果排查。")

print("=" * 65)

