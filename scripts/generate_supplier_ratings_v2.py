
from pathlib import Path

import numpy as np
import pandas as pd


# =====================================
# 1. 路径与基础参数
# =====================================

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "processed"

SUPPLIERS_FILE = DATA_DIR / "suppliers.csv"
ORDERS_FILE = DATA_DIR / "purchase_orders.csv"
DETAILS_FILE = DATA_DIR / "purchase_order_details.csv"
RECEIPTS_FILE = DATA_DIR / "purchase_receipts.csv"

OUTPUT_FILE = DATA_DIR / "supplier_ratings_v2.csv"

# 统计截止日期
CUTOFF_DATE = pd.Timestamp("2026-10-23")

# 评分权重
WEIGHTS = {
    "fulfillment_rate": 0.40,
    "on_time_delivery_rate": 0.35,
    "order_completion_rate": 0.25,
}


# =====================================
# 2. 通用检查函数
# =====================================

def check_columns(df, required_columns, file_name):
    """检查数据表是否包含必要字段。"""

    missing = [
        col for col in required_columns
        if col not in df.columns
    ]

    if missing:
        raise ValueError(
            f"{file_name} 缺少必要字段：{missing}"
        )


def safe_rate(numerator, denominator):
    """安全计算比例，分母为0时返回NaN。"""

    if denominator == 0:
        return np.nan

    return numerator / denominator


# =====================================
# 3. 读取数据
# =====================================

print("=" * 60)
print("开始生成供应商综合评分")
print("=" * 60)

for file_path in [
    SUPPLIERS_FILE,
    ORDERS_FILE,
    DETAILS_FILE,
    RECEIPTS_FILE,
]:
    if not file_path.exists():
        raise FileNotFoundError(
            f"找不到数据文件：{file_path}"
        )

suppliers = pd.read_csv(
    SUPPLIERS_FILE,
    encoding="utf-8-sig"
)

orders = pd.read_csv(
    ORDERS_FILE,
    encoding="utf-8-sig"
)

details = pd.read_csv(
    DETAILS_FILE,
    encoding="utf-8-sig"
)

receipts = pd.read_csv(
    RECEIPTS_FILE,
    encoding="utf-8-sig"
)

print(f"供应商档案：{len(suppliers)} 条")
print(f"采购订单：{len(orders)} 条")
print(f"采购明细：{len(details)} 条")
print(f"到货记录：{len(receipts)} 条")


# =====================================
# 4. 检查字段
# =====================================

check_columns(
    suppliers,
    [
        "supplier_id",
        "supplier_name",
        "region",
        "main_category",
        "supplier_level",
        "status",
    ],
    "suppliers.csv"
)

check_columns(
    orders,
    [
        "order_id",
        "supplier_id",
        "order_date",
        "expected_arrival_date",
    ],
    "purchase_orders.csv"
)

check_columns(
    details,
    [
        "order_id",
        "supplier_id",
        "sku_id",
        "purchase_quantity",
    ],
    "purchase_order_details.csv"
)

check_columns(
    receipts,
    [
        "order_id",
        "supplier_id",
        "sku_id",
        "received_quantity",
        "receipt_date",
    ],
    "purchase_receipts.csv"
)


# =====================================
# 5. 日期与数值处理
# =====================================

orders["order_date"] = pd.to_datetime(
    orders["order_date"],
    errors="raise"
)

orders["expected_arrival_date"] = pd.to_datetime(
    orders["expected_arrival_date"],
    errors="raise"
)

receipts["receipt_date"] = pd.to_datetime(
    receipts["receipt_date"],
    errors="raise"
)

details["purchase_quantity"] = pd.to_numeric(
    details["purchase_quantity"],
    errors="raise"
)

receipts["received_quantity"] = pd.to_numeric(
    receipts["received_quantity"],
    errors="raise"
)

if (
    details["purchase_quantity"] < 0
).any():
    raise ValueError("采购明细中存在负数采购量")

if (
    receipts["received_quantity"] < 0
).any():
    raise ValueError("到货记录中存在负数到货量")


# =====================================
# 6. 关联采购订单与采购明细
# =====================================

# 每条采购明细关联对应订单的预计到货日期
# 这里只从订单表取必要字段，避免重复字段产生_x、_y后缀

order_info = orders[
    [
        "order_id",
        "supplier_id",
        "order_date",
        "expected_arrival_date",
    ]
].copy()

if orders["order_id"].duplicated().any():
    raise ValueError("采购订单主表存在重复订单编号")

detail_data = details.merge(
    order_info,
    on=["order_id", "supplier_id"],
    how="left",
    validate="many_to_one"
)

if detail_data["expected_arrival_date"].isna().any():
    raise ValueError(
        "部分采购明细未能匹配采购订单，请检查订单编号和供应商编号"
    )


# =====================================
# 7. 汇总实际到货数量
# =====================================

receipt_summary = (
    receipts.groupby(
        ["order_id", "supplier_id", "sku_id"],
        as_index=False
    )
    .agg(
        received_quantity=(
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

detail_data["received_quantity"] = (
    detail_data["received_quantity"].fillna(0)
)

# 每条采购明细的待到货数量
detail_data["pending_quantity"] = (
    detail_data["purchase_quantity"]
    - detail_data["received_quantity"]
)

if (detail_data["pending_quantity"] < 0).any():
    raise ValueError(
        "存在累计到货数量超过采购数量的记录，请检查采购数据"
    )


# =====================================
# 8. 识别已到期与未到期订单
# =====================================

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

print("\n订单到期情况：")
print(f"已到预计到货日期的明细：{len(due_details)} 条")
print(f"尚未到预计到货日期的明细：{len(future_details)} 条")


# =====================================
# 9. 计算到期订单履约率
# =====================================

due_stats = (
    due_details.groupby("supplier_id")
    .agg(
        due_quantity=(
            "purchase_quantity",
            "sum"
        ),
        due_received_quantity=(
            "received_quantity",
            "sum"
        ),
        due_order_count=(
            "order_id",
            "nunique"
        )
    )
    .reset_index()
)

due_stats["fulfillment_rate"] = (
    due_stats["due_received_quantity"]
    / due_stats["due_quantity"].replace(0, np.nan)
)


# =====================================
# 10. 计算到期订单完成率
# =====================================

if len(due_details) > 0:

    # 按订单汇总采购量和到货量
    order_completion = (
        due_details.groupby(
            ["supplier_id", "order_id"],
            as_index=False
        )
        .agg(
            ordered_quantity=(
                "purchase_quantity",
                "sum"
            ),
            received_quantity=(
                "received_quantity",
                "sum"
            )
        )
    )

    # 一张订单的全部采购商品均已到货，才视为完成
    order_completion["is_completed"] = (
        order_completion["received_quantity"]
        >= order_completion["ordered_quantity"]
    )

    completion_stats = (
        order_completion.groupby("supplier_id")
        .agg(
            due_completed_orders=(
                "is_completed",
                "sum"
            ),
            due_order_count_check=(
                "order_id",
                "nunique"
            )
        )
        .reset_index()
    )

    completion_stats["order_completion_rate"] = (
        completion_stats["due_completed_orders"]
        / completion_stats["due_order_count_check"].replace(
            0, np.nan
        )
    )

else:

    completion_stats = pd.DataFrame(
        columns=[
            "supplier_id",
            "due_completed_orders",
            "due_order_count_check",
            "order_completion_rate",
        ]
    )


# =====================================
# 11. 计算实际到货及时率
# =====================================

# 先从到货记录中删除可能存在的同名预计日期字段
# 再从采购订单主表中重新关联，确保日期来源一致

receipts_for_timing = receipts.drop(
    columns=["expected_arrival_date"],
    errors="ignore"
).copy()

orders_for_timing = orders[
    [
        "order_id",
        "expected_arrival_date",
    ]
].copy()

receipt_timing = receipts_for_timing.merge(
    orders_for_timing,
    on="order_id",
    how="left",
    validate="many_to_one"
)

if receipt_timing["expected_arrival_date"].isna().any():
    raise ValueError(
        "部分到货记录未能匹配采购订单预计到货日期"
    )

receipt_timing["is_on_time"] = (
    receipt_timing["receipt_date"]
    <= receipt_timing["expected_arrival_date"]
)

receipt_timing["on_time_quantity"] = np.where(
    receipt_timing["is_on_time"],
    receipt_timing["received_quantity"],
    0
)

timing_stats = (
    receipt_timing.groupby("supplier_id")
    .agg(
        timing_received_quantity=(
            "received_quantity",
            "sum"
        ),
        on_time_quantity=(
            "on_time_quantity",
            "sum"
        )
    )
    .reset_index()
)

timing_stats["on_time_delivery_rate"] = (
    timing_stats["on_time_quantity"]
    / timing_stats["timing_received_quantity"].replace(
        0, np.nan
    )
)


# =====================================
# 12. 汇总供应商评分指标
# =====================================

supplier_stats = suppliers[
    ["supplier_id"]
].copy()

supplier_stats = supplier_stats.merge(
    due_stats,
    on="supplier_id",
    how="left"
)

supplier_stats = supplier_stats.merge(
    completion_stats[
        [
            "supplier_id",
            "due_completed_orders",
            "order_completion_rate",
        ]
    ],
    on="supplier_id",
    how="left"
)

supplier_stats = supplier_stats.merge(
    timing_stats[
        [
            "supplier_id",
            "timing_received_quantity",
            "on_time_quantity",
            "on_time_delivery_rate",
        ]
    ],
    on="supplier_id",
    how="left"
)

# 没有到期订单的供应商不计算到期履约率和订单完成率
# 不将其直接记为0分

# 订单数量等统计字段可以用0填充
count_columns = [
    "due_quantity",
    "due_received_quantity",
    "due_order_count",
    "due_completed_orders",
    "timing_received_quantity",
    "on_time_quantity",
]

for col in count_columns:
    if col in supplier_stats.columns:
        supplier_stats[col] = (
            supplier_stats[col].fillna(0)
        )


# =====================================
# 13. 计算供应商综合评分
# =====================================

# 各项指标均转换为百分制
supplier_stats["fulfillment_score"] = (
    supplier_stats["fulfillment_rate"] * 100
)

supplier_stats["timeliness_score"] = (
    supplier_stats["on_time_delivery_rate"] * 100
)

supplier_stats["completion_score"] = (
    supplier_stats["order_completion_rate"] * 100
)

score_columns = {
    "fulfillment_score": WEIGHTS["fulfillment_rate"],
    "timeliness_score": WEIGHTS["on_time_delivery_rate"],
    "completion_score": WEIGHTS["order_completion_rate"],
}

# 缺失维度不参与评分，剩余维度权重自动归一化
weighted_score = pd.Series(
    0.0,
    index=supplier_stats.index
)

available_weight = pd.Series(
    0.0,
    index=supplier_stats.index
)

for col, weight in score_columns.items():

    valid = supplier_stats[col].notna()

    weighted_score.loc[valid] += (
        supplier_stats.loc[valid, col] * weight
    )

    available_weight.loc[valid] += weight

supplier_stats["total_score"] = (
    weighted_score
    / available_weight.replace(0, np.nan)
)

supplier_stats["total_score"] = (
    supplier_stats["total_score"].round(2)
)


# =====================================
# 14. 供应商等级划分
# =====================================

def get_supplier_grade(score):

    if pd.isna(score):
        return "待观察"

    if score >= 85:
        return "A级"

    elif score >= 70:
        return "B级"

    elif score >= 60:
        return "C级"

    else:
        return "D级"


supplier_stats["supplier_grade"] = (
    supplier_stats["total_score"].apply(
        get_supplier_grade
    )
)


# =====================================
# 15. 生成供应商合作建议
# =====================================

def get_supplier_strategy(row):

    if pd.isna(row["total_score"]):
        return "观察合作：当前缺少有效评价样本，建议积累更多履约记录"

    if row["supplier_grade"] == "A级":
        return "重点合作：优先分配采购需求，持续维护战略合作关系"

    if row["supplier_grade"] == "B级":
        return "稳定合作：维持现有采购合作，关注履约表现"

    if row["supplier_grade"] == "C级":
        return "审慎合作：控制采购规模，跟踪交付与履约改善情况"

    return "风险控制：降低采购依赖，优先评估备选供应商"


supplier_stats["cooperation_strategy"] = (
    supplier_stats.apply(
        get_supplier_strategy,
        axis=1
    )
)


# =====================================
# 16. 合并供应商档案并生成评价状态
# =====================================

# 删除供应商档案中的旧版静态及时率字段
suppliers_for_result = suppliers.drop(
    columns=["on_time_delivery_rate"],
    errors="ignore"
).copy()

# 合并新版评分指标
result = suppliers_for_result.merge(
    supplier_stats,
    on="supplier_id",
    how="left",
    validate="one_to_one"
)

# 生成评价样本说明
def get_sample_status(row):

    due_count = row.get("due_order_count", 0)
    timing_quantity = row.get("timing_received_quantity", 0)

    if pd.isna(due_count):
        due_count = 0

    if pd.isna(timing_quantity):
        timing_quantity = 0

    if due_count == 0 and timing_quantity == 0:
        return "暂无有效评价样本"

    if due_count == 0:
        return "仅有实际到货样本"

    if timing_quantity == 0:
        return "仅有到期订单样本"

    return "有有效评价样本"


result["evaluation_status"] = result.apply(
    get_sample_status,
    axis=1
)


# =====================================
# 17. 整理输出字段
# =====================================

output_columns = [
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
    "cooperation_strategy",
]

# 检查输出字段是否齐全
missing_columns = [
    col for col in output_columns
    if col not in result.columns
]

if missing_columns:
    raise ValueError(
        f"输出数据缺少字段：{missing_columns}"
    )

result = result[output_columns].copy()
# =====================================
# 18. 保存结果
# =====================================

result = result.sort_values(
    by=["total_score", "supplier_id"],
    ascending=[False, True],
    na_position="last"
)

result.to_csv(
    OUTPUT_FILE,
    index=False,
    encoding="utf-8-sig"
)


# =====================================
# 19. 输出运行报告
# =====================================

print("\n" + "=" * 60)
print("供应商综合评分生成完成")
print("=" * 60)

print(f"\n评价截止日期：{CUTOFF_DATE.date()}")
print(f"供应商总数：{len(result)}")

print("\n供应商等级分布：")

grade_order = [
    "A级",
    "B级",
    "C级",
    "D级",
    "待观察",
]

grade_counts = (
    result["supplier_grade"]
    .value_counts()
    .reindex(grade_order, fill_value=0)
)

for grade, count in grade_counts.items():
    print(f"{grade}：{count} 家")

valid_scores = result["total_score"].dropna()

if len(valid_scores) > 0:

    print(
        f"\n有效评分供应商：{len(valid_scores)} 家"
    )

    print(
        f"平均综合评分：{valid_scores.mean():.2f}"
    )

    print(
        f"最高综合评分：{valid_scores.max():.2f}"
    )

    print(
        f"最低综合评分：{valid_scores.min():.2f}"
    )

print("\n综合评分 TOP 10：")

top_columns = [
    "supplier_name",
    "main_category",
    "supplier_level",
    "total_score",
    "supplier_grade",
]

print(
    result[top_columns].head(10).to_string(
        index=False
    )
)

print("\n综合评分 BOTTOM 10：")

print(
    result[top_columns]
    .dropna(subset=["total_score"])
    .tail(10)
    .to_string(index=False)
)

print(f"\n文件保存位置：{OUTPUT_FILE}")

print("\n评分口径说明：")
print("1. 仅将预计到货日期不晚于2026-10-23的订单纳入到期履约率和订单完成率。")
print("2. 尚未到期的订单不直接作为未履约订单扣分。")
print("3. 按时交付率按实际到货数量加权计算。")
print("4. 未产生有效评价样本的维度不参与评分，剩余权重自动归一化。")
print("5. 本评分模型基于模拟业务数据，仅用于项目分析演示。")
print("6. 及时率暂不将尚未到货的逾期采购数量纳入分母，解读时需注意。")

print("\n" + "=" * 60)
