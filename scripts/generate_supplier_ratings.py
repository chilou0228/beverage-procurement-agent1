
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 读取供应商绩效数据
performance = pd.read_csv(
    PROJECT_ROOT / "data" / "processed" / "supplier_performance.csv"
)

print("=" * 55)
print("供应商综合评分与分级")
print("=" * 55)

# 1. 设置评价权重
WEIGHT_FULFILLMENT = 0.40
WEIGHT_ON_TIME = 0.35
WEIGHT_COMPLETION = 0.25

# 2. 计算各维度得分（满分100分）
performance["fulfillment_score"] = (
    performance["fulfillment_rate"] * 100
)

performance["on_time_score"] = (
    performance["on_time_delivery_rate"] * 100
)

performance["completion_score"] = (
    performance["order_completion_rate"] * 100
)

# 3. 计算综合评分
performance["comprehensive_score"] = (
    performance["fulfillment_score"] * WEIGHT_FULFILLMENT
    + performance["on_time_score"] * WEIGHT_ON_TIME
    + performance["completion_score"] * WEIGHT_COMPLETION
).round(2)

# 4. 供应商等级划分
def classify_supplier(score):

    if score >= 85:
        return "A级"

    elif score >= 70:
        return "B级"

    elif score >= 60:
        return "C级"

    else:
        return "D级"


performance["evaluated_level"] = (
    performance["comprehensive_score"]
    .apply(classify_supplier)
)

# 5. 生成合作建议
def generate_suggestion(row):

    if row["order_count"] == 0:
        return "暂无采购记录，建议先进行小批量合作测试"

    if row["received_quantity"] == 0:
        return "暂无实际到货，建议跟进订单交付进度"

    if row["evaluated_level"] == "A级":
        return "优先合作，可考虑增加采购份额"

    elif row["evaluated_level"] == "B级":
        return "保持稳定合作，持续跟踪交付表现"

    elif row["evaluated_level"] == "C级":
        return "要求改善交付表现，适当控制采购份额"

    else:
        return "重点关注交付风险，建议评估备选供应商"

performance["cooperation_suggestion"] = (
    performance.apply(generate_suggestion, axis=1)
)

# 6. 添加评价说明
performance["evaluation_note"] = (
    "基于模拟采购订单及到货数据计算；"
    "评价周期截至2026-10-23，非真实供应商评级"
)

# 7. 整理字段
output_columns = [
    "supplier_id",
    "supplier_name",
    "region",
    "main_category",
    "original_supplier_level",
    "order_count",
    "purchase_amount",
    "fulfillment_rate",
    "on_time_delivery_rate",
    "order_completion_rate",
    "fulfillment_score",
    "on_time_score",
    "completion_score",
    "comprehensive_score",
    "evaluated_level",
    "cooperation_suggestion",
    "evaluation_note"
]

ratings = performance[output_columns].copy()

# 8. 保存评分结果
output_path = (
    PROJECT_ROOT /
    "data" /
    "processed" /
    "supplier_ratings.csv"
)

ratings.to_csv(
    output_path,
    index=False,
    encoding="utf-8-sig"
)

# 9. 输出评分结果
print("\n供应商等级分布：")
print(
    ratings["evaluated_level"]
    .value_counts()
    .sort_index()
)

print("\n综合评分 TOP10：")
print(
    ratings.sort_values(
        "comprehensive_score",
        ascending=False
    )[
        [
            "supplier_name",
            "comprehensive_score",
            "evaluated_level",
            "cooperation_suggestion"
        ]
    ].head(10).to_string(index=False)
)

print("\n综合评分 BOTTOM10：")
print(
    ratings.sort_values(
        "comprehensive_score",
        ascending=True
    )[
        [
            "supplier_name",
            "comprehensive_score",
            "evaluated_level",
            "cooperation_suggestion"
        ]
    ].head(10).to_string(index=False)
)

print(
    f"\n平均综合评分："
    f"{ratings['comprehensive_score'].mean():.2f}"
)

print(f"\n文件保存位置：{output_path}")
