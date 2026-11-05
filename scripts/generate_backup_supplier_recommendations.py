
from pathlib import Path

import numpy as np
import pandas as pd


# =====================================
# 1. 路径配置
# =====================================

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "processed"

MAPPING_FILE = DATA_DIR / "product_supplier_mapping.csv"
RATINGS_FILE = DATA_DIR / "supplier_ratings_v2.csv"

OUTPUT_FILE = DATA_DIR / "backup_supplier_recommendations.csv"


# =====================================
# 2. 读取数据
# =====================================

print("=" * 60)
print("开始生成备选供应商推荐")
print("=" * 60)

mapping = pd.read_csv(
    MAPPING_FILE,
    encoding="utf-8-sig"
)

ratings = pd.read_csv(
    RATINGS_FILE,
    encoding="utf-8-sig"
)


# =====================================
# 3. 检查必要字段
# =====================================

required_mapping_columns = [
    "sku_id",
    "product_name",
    "category_name",
    "supplier_id",
    "supplier_name",
    "is_primary",
    "supplier_quote_cost",
    "avg_lead_time_days",
    "supplier_status",
]

required_rating_columns = [
    "supplier_id",
    "total_score",
    "supplier_grade",
    "evaluation_status",
]

for col in required_mapping_columns:
    if col not in mapping.columns:
        raise ValueError(
            f"商品供应商关联表缺少字段：{col}"
        )

for col in required_rating_columns:
    if col not in ratings.columns:
        raise ValueError(
            f"供应商评分表缺少字段：{col}"
        )


# =====================================
# 4. 数据类型处理
# =====================================

mapping["supplier_quote_cost"] = pd.to_numeric(
    mapping["supplier_quote_cost"],
    errors="raise"
)

mapping["avg_lead_time_days"] = pd.to_numeric(
    mapping["avg_lead_time_days"],
    errors="raise"
)

ratings["total_score"] = pd.to_numeric(
    ratings["total_score"],
    errors="coerce"
)

# 统一处理主供应商标识
mapping["is_primary"] = (
    mapping["is_primary"]
    .astype(str)
    .str.lower()
    .isin(["true", "1", "yes"])
)

# 检查报价和交期
if (mapping["supplier_quote_cost"] <= 0).any():
    raise ValueError("发现无效供应商报价")

if (mapping["avg_lead_time_days"] <= 0).any():
    raise ValueError("发现无效供应商交期")


# =====================================
# 5. 关联供应商评分
# =====================================

mapping = mapping.merge(
    ratings[
        [
            "supplier_id",
            "total_score",
            "supplier_grade",
            "evaluation_status",
        ]
    ],
    on="supplier_id",
    how="left",
    validate="many_to_one"
)

# 没有评分的供应商不直接视为优秀或合格
mapping["rating_available"] = (
    mapping["total_score"].notna()
)


# =====================================
# 6. 计算单项竞争力得分
# =====================================

def calculate_recommendation(group):

    group = group.copy()

    # 采购报价越低，竞争力得分越高
    min_cost = group["supplier_quote_cost"].min()

    group["price_score"] = (
        min_cost / group["supplier_quote_cost"] * 100
    )

    # 交期越短，竞争力得分越高
    min_lead_time = group["avg_lead_time_days"].min()

    group["lead_time_score"] = (
        min_lead_time
        / group["avg_lead_time_days"]
        * 100
    )

    # 供应商综合评分
    group["supplier_score"] = group["total_score"]

    # 当前无评分样本时，不伪造评分
    # 对可用维度重新分配权重
    dimensions = {
        "supplier_score": 0.60,
        "price_score": 0.25,
        "lead_time_score": 0.15,
    }

    weighted_sum = pd.Series(
        0.0,
        index=group.index
    )

    available_weight = pd.Series(
        0.0,
        index=group.index
    )

    for col, weight in dimensions.items():

        valid = group[col].notna()

        weighted_sum.loc[valid] += (
            group.loc[valid, col] * weight
        )

        available_weight.loc[valid] += weight

    group["recommendation_score"] = (
        weighted_sum
        / available_weight.replace(0, np.nan)
    ).round(2)

    return group


# =====================================
# 7. 逐商品比较主供应商与备选供应商
# =====================================

results = []

for sku_id, group in mapping.groupby("sku_id"):

    group = group.copy()

    # 每个商品必须有两家供应商
    if len(group) != 2:
        raise ValueError(
            f"商品 {sku_id} 的供应商数量不是2家"
        )

    if group["is_primary"].sum() != 1:
        raise ValueError(
            f"商品 {sku_id} 没有唯一主供应商"
        )

    group = calculate_recommendation(group)

    primary = group[
        group["is_primary"]
    ].iloc[0]

    backup = group[
        ~group["is_primary"]
    ].iloc[0]

    # 仅从正常状态供应商中选择
    available_candidates = group[
        group["supplier_status"]
        .astype(str)
        .str.lower()
        .isin(["active", "正常", "启用","合作中"])
    ].copy()

    if len(available_candidates) == 0:
        recommended = None
        recommendation_reason = "两家供应商均不可用，建议人工核查"
        decision = "暂不推荐"

    else:

        # 优先选择综合得分较高的可用供应商
        available_candidates = (
            available_candidates
            .sort_values(
                by="recommendation_score",
                ascending=False,
                na_position="last"
            )
        )

        recommended = available_candidates.iloc[0]

        if recommended["supplier_id"] == primary["supplier_id"]:
            decision = "维持主供应商"
            recommendation_reason = (
                "主供应商综合竞争力较高，建议维持当前合作"
            )
        else:
            decision = "建议考虑备选供应商"
            recommendation_reason = (
                "备选供应商综合竞争力高于主供应商，可进一步评估替换"
            )

    # =================================
    # 8. 计算成本和交期变化
    # =================================

    cost_difference = (
        backup["supplier_quote_cost"]
        - primary["supplier_quote_cost"]
    )

    lead_time_difference = (
        backup["avg_lead_time_days"]
        - primary["avg_lead_time_days"]
    )

    cost_change_rate = (
        cost_difference
        / primary["supplier_quote_cost"]
        * 100
    )

    # =================================
    # 9. 生成结果
    # =================================

    row = {
        "sku_id": sku_id,
        "product_name": primary["product_name"],
        "category_name": primary["category_name"],

        "primary_supplier_id": primary["supplier_id"],
        "primary_supplier_name": primary["supplier_name"],
        "primary_supplier_score": primary["total_score"],
        "primary_supplier_grade": primary["supplier_grade"],
        "primary_quote_cost": primary["supplier_quote_cost"],
        "primary_lead_time_days": primary["avg_lead_time_days"],

        "backup_supplier_id": backup["supplier_id"],
        "backup_supplier_name": backup["supplier_name"],
        "backup_supplier_score": backup["total_score"],
        "backup_supplier_grade": backup["supplier_grade"],
        "backup_quote_cost": backup["supplier_quote_cost"],
        "backup_lead_time_days": backup["avg_lead_time_days"],

        "backup_cost_difference": round(cost_difference, 2),
        "backup_cost_change_rate": round(cost_change_rate, 2),
        "backup_lead_time_difference": round(
            lead_time_difference, 2
        ),

        "recommended_supplier_id": (
            recommended["supplier_id"]
            if recommended is not None else None
        ),

        "recommended_supplier_name": (
            recommended["supplier_name"]
            if recommended is not None else None
        ),

        "recommended_supplier_score": (
            recommended["recommendation_score"]
            if recommended is not None else np.nan
        ),

        "decision": decision,
        "recommendation_reason": recommendation_reason,
    }

    results.append(row)


# =====================================
# 10. 汇总输出
# =====================================

result = pd.DataFrame(results)

result = result.sort_values(
    by=["category_name", "sku_id"]
)

result.to_csv(
    OUTPUT_FILE,
    index=False,
    encoding="utf-8-sig"
)


# =====================================
# 11. 输出运行报告
# =====================================

print("\n备选供应商推荐生成完成！")

print(f"商品数量：{len(result)}")

print("\n推荐决策分布：")

print(
    result["decision"]
    .value_counts()
    .to_string()
)

print("\n推荐结果预览：")

preview_columns = [
    "product_name",
    "primary_supplier_name",
    "backup_supplier_name",
    "recommended_supplier_name",
    "decision",
]

print(
    result[preview_columns]
    .head(10)
    .to_string(index=False)
)

print(f"\n文件保存位置：{OUTPUT_FILE}")

print("\n评分口径：")
print("1. 供应商综合评分权重60%。")
print("2. 采购报价竞争力权重25%。")
print("3. 供货交期竞争力权重15%。")
print("4. 缺失的供应商评分维度不参与计算，其他维度权重自动归一化。")
print("5. 推荐结果仅作为采购决策辅助，不自动替换主供应商。")
print("6. 本项目使用模拟数据，推荐结果仅用于演示。")

print("\n" + "=" * 60)
