
from pathlib import Path

import numpy as np
import pandas as pd


# =====================================
# 1. 文件路径
# =====================================

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "processed"

RATINGS_FILE = DATA_DIR / "supplier_ratings_v2.csv"
SUPPLIERS_FILE = DATA_DIR / "suppliers.csv"

print("=" * 60)
print("开始检查供应商综合评分数据")
print("=" * 60)


# =====================================
# 2. 读取数据
# =====================================

ratings = pd.read_csv(
    RATINGS_FILE,
    encoding="utf-8-sig"
)

suppliers = pd.read_csv(
    SUPPLIERS_FILE,
    encoding="utf-8-sig"
)

errors = []


def check(condition, success_message, error_message):
    if condition:
        print(f"[通过] {success_message}")
    else:
        print(f"[失败] {error_message}")
        errors.append(error_message)


# =====================================
# 3. 检查基础数据
# =====================================

required_columns = [
    "supplier_id",
    "supplier_name",
    "due_order_count",
    "due_quantity",
    "due_received_quantity",
    "fulfillment_rate",
    "due_completed_orders",
    "order_completion_rate",
    "timing_received_quantity",
    "on_time_quantity",
    "on_time_delivery_rate",
    "total_score",
    "supplier_grade",
    "evaluation_status",
    "cooperation_strategy",
]

check(
    all(col in ratings.columns for col in required_columns),
    "评分文件包含全部必要字段",
    "评分文件缺少必要字段"
)

check(
    len(ratings) == 40,
    "供应商记录数量为40",
    f"供应商记录数量异常：{len(ratings)}"
)

check(
    ratings["supplier_id"].is_unique,
    "供应商编号唯一",
    "供应商编号存在重复"
)

check(
    ratings["supplier_id"].notna().all(),
    "供应商编号无缺失",
    "供应商编号存在缺失"
)


# =====================================
# 4. 检查供应商关联
# =====================================

check(
    set(ratings["supplier_id"]) == set(suppliers["supplier_id"]),
    "评分文件与供应商档案完整对应",
    "评分文件与供应商档案不一致"
)


# =====================================
# 5. 检查评分指标范围
# =====================================

rate_columns = [
    "fulfillment_rate",
    "order_completion_rate",
    "on_time_delivery_rate",
]

for col in rate_columns:

    valid_values = ratings[col].dropna()

    check(
        valid_values.between(0, 1).all(),
        f"{col} 均在0至1之间",
        f"{col} 存在超出合理范围的数值"
    )


# =====================================
# 6. 检查履约率计算
# =====================================

valid = ratings["due_quantity"] > 0

expected_fulfillment = (
    ratings.loc[valid, "due_received_quantity"]
    / ratings.loc[valid, "due_quantity"]
)

check(
    np.allclose(
        ratings.loc[valid, "fulfillment_rate"],
        expected_fulfillment,
        atol=0.0001
    ),
    "到期订单履约率计算正确",
    "到期订单履约率计算存在错误"
)


# =====================================
# 7. 检查订单完成率
# =====================================

valid = ratings["due_order_count"] > 0

expected_completion = (
    ratings.loc[valid, "due_completed_orders"]
    / ratings.loc[valid, "due_order_count"]
)

check(
    np.allclose(
        ratings.loc[valid, "order_completion_rate"],
        expected_completion,
        atol=0.0001
    ),
    "到期订单完成率计算正确",
    "到期订单完成率计算存在错误"
)


# =====================================
# 8. 检查按时交付率
# =====================================

valid = ratings["timing_received_quantity"] > 0

expected_timeliness = (
    ratings.loc[valid, "on_time_quantity"]
    / ratings.loc[valid, "timing_received_quantity"]
)

check(
    np.allclose(
        ratings.loc[valid, "on_time_delivery_rate"],
        expected_timeliness,
        atol=0.0001
    ),
    "按时交付率计算正确",
    "按时交付率计算存在错误"
)


# =====================================
# 9. 检查综合评分
# =====================================

weights = {
    "fulfillment_score": 0.40,
    "timeliness_score": 0.35,
    "completion_score": 0.25,
}

score_columns = list(weights.keys())

score_data = ratings[score_columns].copy()

weighted_sum = pd.Series(
    0.0,
    index=ratings.index
)

available_weight = pd.Series(
    0.0,
    index=ratings.index
)

for col, weight in weights.items():

    valid = score_data[col].notna()

    weighted_sum.loc[valid] += (
        score_data.loc[valid, col] * weight
    )

    available_weight.loc[valid] += weight

expected_score = (
    weighted_sum
    / available_weight.replace(0, np.nan)
).round(2)

check(
    np.allclose(
        ratings["total_score"].fillna(-999),
        expected_score.fillna(-999),
        atol=0.01
    ),
    "综合评分计算正确，缺失维度权重已归一化",
    "综合评分与权重计算结果不一致"
)


# =====================================
# 10. 检查供应商等级
# =====================================

def expected_grade(score):

    if pd.isna(score):
        return "待观察"

    if score >= 85:
        return "A级"

    if score >= 70:
        return "B级"

    if score >= 60:
        return "C级"

    return "D级"


expected_grades = ratings["total_score"].apply(
    expected_grade
)

check(
    (
        ratings["supplier_grade"].values
        == expected_grades.values
    ).all(),
    "供应商等级划分正确",
    "供应商等级与综合评分不一致"
)


# =====================================
# 11. 检查待观察供应商
# =====================================

unrated = ratings[
    ratings["total_score"].isna()
]

check(
    (
        unrated["supplier_grade"] == "待观察"
    ).all(),
    "无有效评分样本的供应商标记为待观察",
    "无评分样本的供应商等级标记错误"
)


# =====================================
# 12. 检查合作建议
# =====================================

check(
    ratings["cooperation_strategy"].notna().all(),
    "所有供应商均生成合作建议",
    "部分供应商缺少合作建议"
)

check(
    ratings["evaluation_status"].notna().all(),
    "所有供应商均有评价状态",
    "部分供应商缺少评价状态"
)


# =====================================
# 13. 输出检查结果
# =====================================

print("\n" + "=" * 60)
print("供应商评分质量检查结果")
print("=" * 60)

print(f"检查项目：{len(errors) + 12}")
print(f"失败项目：{len(errors)}")

if errors:

    print("\n发现的问题：")

    for error in errors:
        print(f"- {error}")

    print("\n检查未通过，请根据错误信息修复。")

else:

    print("\n所有检查均已通过！")
    print("供应商综合评分数据质量符合当前模型设定。")

print("\n供应商等级分布：")

print(
    ratings["supplier_grade"]
    .value_counts()
    .to_string()
)

print("\n检查完成。")
print("=" * 60)
