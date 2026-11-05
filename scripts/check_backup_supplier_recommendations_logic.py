
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

print("=" * 65)
print("酒水采销 Agent｜备选供应商推荐业务逻辑检查")
print("=" * 65)

mapping = pd.read_csv(MAPPING_FILE, encoding="utf-8-sig")
ratings = pd.read_csv(RATINGS_FILE, encoding="utf-8-sig")
result = pd.read_csv(OUTPUT_FILE, encoding="utf-8-sig")

errors = []
check_count = 0


def check(name, condition, detail=""):
    global check_count
    check_count += 1

    if condition:
        print(f"PASS：{name}，异常数量：0")
    else:
        print(f"FAIL：{name}，{detail}")
        errors.append(name)


def compare_column(actual, expected, name, tolerance=0.01):
    actual = pd.to_numeric(actual, errors="coerce").reset_index(drop=True)
    expected = pd.to_numeric(expected, errors="coerce").reset_index(drop=True)

    if len(actual) != len(expected):
        check(name, False, "记录数量不一致")
        return

    both_null = actual.isna() & expected.isna()
    equal = np.isclose(
        actual.fillna(0),
        expected.fillna(0),
        atol=tolerance,
        rtol=0
    ) | both_null

    check(
        name,
        bool(equal.all()),
        f"异常数量：{int((~equal).sum())}"
    )


def compare_text(actual, expected, name):
    actual = actual.fillna("__NULL__").astype(str).reset_index(drop=True)
    expected = expected.fillna("__NULL__").astype(str).reset_index(drop=True)

    if len(actual) != len(expected):
        check(name, False, "记录数量不一致")
        return

    mismatch = actual != expected

    check(
        name,
        not mismatch.any(),
        f"异常数量：{int(mismatch.sum())}"
    )


# =====================================
# 3. 基础数据
# =====================================

print(f"\n商品供应商关联记录：{len(mapping)}")
print(f"供应商评分记录：{len(ratings)}")
print(f"推荐结果记录：{len(result)}")


# =====================================
# 4. 必要字段检查
# =====================================

print("\n【检查1：推荐结果字段完整性】")
print("-" * 65)

required_columns = [
    "sku_id",
    "product_name",
    "category_name",
    "primary_supplier_id",
    "primary_supplier_name",
    "primary_supplier_score",
    "primary_supplier_grade",
    "primary_quote_cost",
    "primary_lead_time_days",
    "backup_supplier_id",
    "backup_supplier_name",
    "backup_supplier_score",
    "backup_supplier_grade",
    "backup_quote_cost",
    "backup_lead_time_days",
    "backup_cost_difference",
    "backup_cost_change_rate",
    "backup_lead_time_difference",
    "recommended_supplier_id",
    "recommended_supplier_name",
    "recommended_supplier_score",
    "decision",
    "recommendation_reason",
]

missing = [c for c in required_columns if c not in result.columns]

check(
    "推荐结果包含全部必要字段",
    len(missing) == 0,
    f"缺失字段：{missing}"
)

if missing:
    raise SystemExit("推荐结果缺少必要字段，停止检查。")


# =====================================
# 5. 商品覆盖与唯一性
# =====================================

print("\n【检查2：商品覆盖与唯一性】")
print("-" * 65)

check(
    "推荐记录数量与商品SKU数量一致",
    len(result) == mapping["sku_id"].nunique(),
    f"推荐记录：{len(result)}，商品数量：{mapping['sku_id'].nunique()}"
)

check(
    "推荐结果每个SKU唯一",
    result["sku_id"].is_unique,
    f"重复SKU数量：{result['sku_id'].duplicated().sum()}"
)

check(
    "推荐结果完整覆盖全部SKU",
    set(result["sku_id"]) == set(mapping["sku_id"]),
    "SKU集合不一致"
)


# =====================================
# 6. 主备供应商关系
# =====================================

print("\n【检查3：主备供应商关系】")
print("-" * 65)

mapping_check = mapping.copy()

mapping_check["is_primary"] = (
    mapping_check["is_primary"]
    .astype(str)
    .str.lower()
    .isin(["true", "1", "yes"])
)

group_stats = mapping_check.groupby("sku_id").agg(
    supplier_count=("supplier_id", "nunique"),
    primary_count=("is_primary", "sum")
)

check(
    "每个SKU均关联两家不同供应商",
    (group_stats["supplier_count"] == 2).all(),
    f"异常SKU数量：{int((group_stats['supplier_count'] != 2).sum())}"
)

check(
    "每个SKU均有且只有一家主供应商",
    (group_stats["primary_count"] == 1).all(),
    f"异常SKU数量：{int((group_stats['primary_count'] != 1).sum())}"
)


# =====================================
# 7. 独立重算推荐结果
# =====================================

print("\n【检查4：推荐评分与权重计算】")
print("-" * 65)

ratings_check = ratings[
    ["supplier_id", "total_score", "supplier_grade", "evaluation_status"]
].copy()

ratings_check["total_score"] = pd.to_numeric(
    ratings_check["total_score"],
    errors="coerce"
)

mapping_check = mapping_check.merge(
    ratings_check,
    on="supplier_id",
    how="left",
    validate="many_to_one"
)

mapping_check["rating_available"] = (
    mapping_check["total_score"].notna()
)

expected_rows = []

allowed_status = ["active", "正常", "启用", "合作中"]

for sku_id, group in mapping_check.groupby("sku_id"):

    group = group.copy()

    min_cost = group["supplier_quote_cost"].min()
    min_lead = group["avg_lead_time_days"].min()

    group["price_score"] = (
        min_cost / group["supplier_quote_cost"] * 100
    )

    group["lead_time_score"] = (
        min_lead / group["avg_lead_time_days"] * 100
    )

    group["supplier_score"] = group["total_score"]

    dimensions = {
        "supplier_score": 0.60,
        "price_score": 0.25,
        "lead_time_score": 0.15,
    }

    weighted_sum = pd.Series(0.0, index=group.index)
    available_weight = pd.Series(0.0, index=group.index)

    for col, weight in dimensions.items():
        valid = group[col].notna()

        weighted_sum.loc[valid] += group.loc[valid, col] * weight
        available_weight.loc[valid] += weight

    group["recommendation_score"] = (
        weighted_sum /
        available_weight.replace(0, np.nan)
    ).round(2)

    primary = group[group["is_primary"]].iloc[0]
    backup = group[~group["is_primary"]].iloc[0]

    candidates = group[
        group["supplier_status"].astype(str).str.lower().isin(
            [s.lower() for s in allowed_status]
        )
    ].copy()

    if len(candidates) == 0:
        recommended = None
        decision = "暂不推荐"
        reason = "两家供应商均不可用，建议人工核查"

    else:
        candidates = candidates.sort_values(
            by="recommendation_score",
            ascending=False,
            na_position="last"
        )

        recommended = candidates.iloc[0]

        if recommended["supplier_id"] == primary["supplier_id"]:
            decision = "维持主供应商"
            reason = "主供应商综合竞争力较高，建议维持当前合作"
        else:
            decision = "建议考虑备选供应商"
            reason = "备选供应商综合竞争力高于主供应商，可进一步评估替换"

    cost_diff = (
        backup["supplier_quote_cost"] -
        primary["supplier_quote_cost"]
    )

    lead_diff = (
        backup["avg_lead_time_days"] -
        primary["avg_lead_time_days"]
    )

    expected_rows.append({
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

        "backup_cost_difference": round(cost_diff, 2),
        "backup_cost_change_rate": round(
            cost_diff / primary["supplier_quote_cost"] * 100,
            2
        ),
        "backup_lead_time_difference": round(lead_diff, 2),

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
        "recommendation_reason": reason,
    })


expected = pd.DataFrame(expected_rows)

# 按生成脚本的排序方式整理
expected = expected.sort_values(
    by=["category_name", "sku_id"]
).reset_index(drop=True)

actual = result.sort_values(
    by=["category_name", "sku_id"]
).reset_index(drop=True)


# =====================================
# 8. 主供应商和备选供应商信息核对
# =====================================

print("\n【检查5：主备供应商信息一致性】")
print("-" * 65)

text_columns = [
    "product_name",
    "category_name",
    "primary_supplier_id",
    "primary_supplier_name",
    "primary_supplier_grade",
    "backup_supplier_id",
    "backup_supplier_name",
    "backup_supplier_grade",
]

for col in text_columns:
    compare_text(
        actual[col],
        expected[col],
        f"{col} 与关联数据重新计算结果一致"
    )

numeric_columns = [
    "primary_supplier_score",
    "primary_quote_cost",
    "primary_lead_time_days",
    "backup_supplier_score",
    "backup_quote_cost",
    "backup_lead_time_days",
]

for col in numeric_columns:
    compare_column(
        actual[col],
        expected[col],
        f"{col} 与关联数据重新计算结果一致"
    )


# =====================================
# 9. 成本与交期变化计算
# =====================================

print("\n【检查6：报价和交期变化计算】")
print("-" * 65)

for col in [
    "backup_cost_difference",
    "backup_cost_change_rate",
    "backup_lead_time_difference",
]:
    compare_column(
        actual[col],
        expected[col],
        f"{col} 计算正确"
    )


# =====================================
# 10. 推荐评分及推荐对象核对
# =====================================

print("\n【检查7：推荐对象与综合评分】")
print("-" * 65)

compare_text(
    actual["recommended_supplier_id"],
    expected["recommended_supplier_id"],
    "推荐供应商ID与独立计算结果一致"
)

compare_text(
    actual["recommended_supplier_name"],
    expected["recommended_supplier_name"],
    "推荐供应商名称与独立计算结果一致"
)

compare_column(
    actual["recommended_supplier_score"],
    expected["recommended_supplier_score"],
    "推荐供应商综合竞争力得分计算正确"
)


# =====================================
# 11. 推荐决策与原因核对
# =====================================

print("\n【检查8：推荐决策与原因】")
print("-" * 65)

compare_text(
    actual["decision"],
    expected["decision"],
    "推荐决策与独立计算结果一致"
)

compare_text(
    actual["recommendation_reason"],
    expected["recommendation_reason"],
    "推荐原因与决策结果一致"
)


# =====================================
# 12. 供应商状态筛选
# =====================================

print("\n【检查9：供应商合作状态筛选】")
print("-" * 65)

status_lookup = mapping_check[
    ["sku_id", "supplier_id", "supplier_status"]
].copy()

recommended_status = actual[
    ["sku_id", "recommended_supplier_id"]
].merge(
    status_lookup,
    left_on=["sku_id", "recommended_supplier_id"],
    right_on=["sku_id", "supplier_id"],
    how="left"
)

has_recommendation = actual["recommended_supplier_id"].notna()

valid_recommended_status = recommended_status[
    recommended_status["recommended_supplier_id"].notna()
]["supplier_status"].astype(str).str.lower().isin(
    [s.lower() for s in allowed_status]
)

check(
    "推荐供应商均处于允许合作状态",
    valid_recommended_status.all(),
    f"异常数量：{int((~valid_recommended_status).sum())}"
)

check(
    "暂不推荐的商品没有推荐供应商ID",
    actual.loc[
        actual["decision"] == "暂不推荐",
        "recommended_supplier_id"
    ].isna().all(),
    "存在暂不推荐但仍有推荐供应商ID的记录"
)


# =====================================
# 13. 推荐结果取值与唯一性
# =====================================

print("\n【检查10：推荐结果合理性】")
print("-" * 65)

valid_decisions = {
    "维持主供应商",
    "建议考虑备选供应商",
    "暂不推荐",
}

check(
    "决策字段不存在未知取值",
    set(actual["decision"]).issubset(valid_decisions),
    f"未知取值：{set(actual['decision']) - valid_decisions}"
)

check(
    "推荐结果不存在重复SKU",
    actual["sku_id"].is_unique,
    f"重复数量：{actual['sku_id'].duplicated().sum()}"
)

# 维持主供应商时，推荐ID必须与主供应商一致
keep_primary = actual["decision"] == "维持主供应商"

check(
    "维持主供应商决策对应的推荐对象正确",
    (
        actual.loc[keep_primary, "recommended_supplier_id"]
        == actual.loc[keep_primary, "primary_supplier_id"]
    ).all(),
    "存在推荐对象不是主供应商的记录"
)

# 考虑备选供应商时，推荐ID必须与备选供应商一致
consider_backup = actual["decision"] == "建议考虑备选供应商"

check(
    "考虑备选供应商决策对应的推荐对象正确",
    (
        actual.loc[consider_backup, "recommended_supplier_id"]
        == actual.loc[consider_backup, "backup_supplier_id"]
    ).all(),
    "存在推荐对象不是备选供应商的记录"
)


# =====================================
# 14. 最终排序
# =====================================

print("\n【检查11：推荐结果排序】")
print("-" * 65)

sorted_expected = actual.sort_values(
    by=["category_name", "sku_id"]
).reset_index(drop=True)

check(
    "推荐结果按照品类和SKU排序",
    actual["sku_id"].equals(sorted_expected["sku_id"]),
    "实际排序与预期不一致"
)


# =====================================
# 15. 汇总
# =====================================

print("\n" + "=" * 65)
print("备选供应商推荐业务逻辑检查汇总")
print("=" * 65)

print(f"检查项目数量：{check_count}")
print(f"通过项目数量：{check_count - len(errors)}")
print(f"异常项目数量：{len(errors)}")

print("\n推荐决策分布：")
print(actual["decision"].value_counts().to_string())

print("\n推荐供应商状态分布：")
print(
    recommended_status[
        recommended_status["recommended_supplier_id"].notna()
    ]["supplier_status"].value_counts().to_string()
)

print("\n推荐结果概况：")
print(f"商品数量：{len(actual)}")
print(f"维持主供应商：{(actual['decision'] == '维持主供应商').sum()}")
print(f"建议考虑备选供应商：{(actual['decision'] == '建议考虑备选供应商').sum()}")
print(f"暂不推荐：{(actual['decision'] == '暂不推荐').sum()}")

if errors:
    print("\n异常项目：")
    for item in errors:
        print(f"- {item}")

    print("\nFAIL：备选供应商推荐业务逻辑检查未全部通过！")
else:
    print("\nPASS：所有备选供应商推荐业务逻辑检查均通过！")

print("=" * 65)
