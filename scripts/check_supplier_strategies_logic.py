
from pathlib import Path

import numpy as np
import pandas as pd


# =====================================
# 1. 文件路径
# =====================================

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "processed"

RATINGS_FILE = DATA_DIR / "supplier_ratings_v2.csv"
MAPPING_FILE = DATA_DIR / "product_supplier_mapping.csv"
STRATEGIES_FILE = DATA_DIR / "supplier_strategies.csv"


# =====================================
# 2. 读取数据
# =====================================

print("=" * 65)
print("酒水采销 Agent｜供应商合作策略业务逻辑检查")
print("=" * 65)

ratings = pd.read_csv(RATINGS_FILE, encoding="utf-8-sig")
mapping = pd.read_csv(MAPPING_FILE, encoding="utf-8-sig")
strategies = pd.read_csv(STRATEGIES_FILE, encoding="utf-8-sig")

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


def compare_column(actual, expected, name):
    """比较两个字段，兼容空值。"""

    actual = actual.reset_index(drop=True)
    expected = expected.reset_index(drop=True)

    if len(actual) != len(expected):
        check(name, False, "记录数量不一致")
        return

    both_null = actual.isna() & expected.isna()

    equal = actual.eq(expected) | both_null

    check(
        name,
        bool(equal.all()),
        f"异常数量：{int((~equal).sum())}"
    )


# =====================================
# 3. 基础信息
# =====================================

print(f"\n供应商评分记录：{len(ratings)}")
print(f"商品供应商关联记录：{len(mapping)}")
print(f"合作策略记录：{len(strategies)}")


# =====================================
# 4. 输出字段检查
# =====================================

print("\n【检查1：策略表字段完整性】")
print("-" * 65)

required_columns = [
    "supplier_id",
    "supplier_name",
    "main_category",
    "supplier_level",
    "total_score",
    "supplier_grade",
    "evaluation_status",
    "product_count",
    "category_count",
    "primary_product_count",
    "cooperation_level",
    "purchase_priority",
    "purchase_share_suggestion",
    "risk_control_action",
    "development_action",
    "management_advice",
]

missing_columns = [
    col for col in required_columns
    if col not in strategies.columns
]

check(
    "策略表包含全部必要字段",
    len(missing_columns) == 0,
    f"缺失字段：{missing_columns}"
)

if missing_columns:
    print("\n策略表缺少必要字段，无法继续检查。")
    raise SystemExit(1)

check(
    "supplier_id 不存在空值",
    strategies["supplier_id"].notna().all(),
    f"异常数量：{strategies['supplier_id'].isna().sum()}"
)

for col in [
    "supplier_name",
    "cooperation_level",
    "purchase_priority",
    "purchase_share_suggestion",
    "risk_control_action",
    "development_action",
    "management_advice",
]:
    check(
        f"{col} 不存在空值",
        strategies[col].notna().all(),
        f"异常数量：{strategies[col].isna().sum()}"
    )


# =====================================
# 5. 供应商覆盖与唯一性
# =====================================

print("\n【检查2：供应商覆盖与唯一性】")
print("-" * 65)

check(
    "策略记录数量与评分记录数量一致",
    len(strategies) == len(ratings),
    f"策略记录：{len(strategies)}，评分记录：{len(ratings)}"
)

check(
    "策略表 supplier_id 唯一",
    strategies["supplier_id"].is_unique,
    f"重复数量：{strategies['supplier_id'].duplicated().sum()}"
)

check(
    "策略表完整覆盖评分表供应商",
    set(strategies["supplier_id"]) == set(ratings["supplier_id"]),
    "供应商ID集合不一致"
)


# =====================================
# 6. 重新计算供应商商品覆盖情况
# =====================================

print("\n【检查3：供应商商品覆盖统计】")
print("-" * 65)

expected_products = (
    mapping.groupby("supplier_id")
    .agg(
        product_count=("sku_id", "nunique"),
        category_count=("category_id", "nunique"),
        primary_product_count=("is_primary", "sum")
    )
    .reset_index()
)

expected = ratings[["supplier_id"]].merge(
    expected_products,
    on="supplier_id",
    how="left",
    validate="one_to_one"
)

for col in [
    "product_count",
    "category_count",
    "primary_product_count",
]:
    expected[col] = expected[col].fillna(0).astype(int)

check_data = strategies.merge(
    expected,
    on="supplier_id",
    how="left",
    suffixes=("", "_expected"),
    validate="one_to_one"
)

for col in [
    "product_count",
    "category_count",
    "primary_product_count",
]:
    compare_column(
        check_data[col],
        check_data[f"{col}_expected"],
        f"{col} 与商品供应商关联表重新统计结果一致"
    )

check(
    "主供应商品数量不超过关联商品数量",
    (
        strategies["primary_product_count"]
        <= strategies["product_count"]
    ).all(),
    "存在主供应商品数量大于关联商品数量的记录"
)

check(
    "供应商品类数量不超过商品数量",
    (
        strategies["category_count"]
        <= strategies["product_count"]
    ).all(),
    "存在品类数量大于商品数量的记录"
)


# =====================================
# 7. 供应商基础信息一致性
# =====================================

print("\n【检查4：供应商基础信息一致性】")
print("-" * 65)

rating_data = ratings[
    [
        "supplier_id",
        "supplier_name",
        "main_category",
        "supplier_level",
        "total_score",
        "supplier_grade",
        "evaluation_status",
    ]
]

check_data = strategies.merge(
    rating_data,
    on="supplier_id",
    how="left",
    suffixes=("", "_expected"),
    validate="one_to_one"
)

for col in [
    "supplier_name",
    "main_category",
    "supplier_level",
    "total_score",
    "supplier_grade",
    "evaluation_status",
]:
    compare_column(
        check_data[col],
        check_data[f"{col}_expected"],
        f"{col} 与供应商评分表一致"
    )


# =====================================
# 8. 重新计算合作策略
# =====================================

print("\n【检查5：合作层级与采购优先级】")
print("-" * 65)


def get_expected_strategy(row):

    grade = row["supplier_grade"]
    score = row["total_score"]

    if pd.isna(score):
        return pd.Series({
            "cooperation_level_expected": "观察合作",
            "purchase_priority_expected": "低",
            "purchase_share_suggestion_expected": "暂不扩大采购",
            "risk_control_action_expected": "积累有效履约记录，完成评价后再决定合作规模",
            "development_action_expected": "保持基础沟通，观察后续交付表现",
        })

    if grade == "A级":
        return pd.Series({
            "cooperation_level_expected": "战略合作",
            "purchase_priority_expected": "最高",
            "purchase_share_suggestion_expected": "可优先考虑增加采购份额",
            "risk_control_action_expected": "定期复核价格、库存及履约表现，避免单一供应商依赖",
            "development_action_expected": "探索年度合作、联合促销及重点商品资源支持",
        })

    elif grade == "B级":
        return pd.Series({
            "cooperation_level_expected": "稳定合作",
            "purchase_priority_expected": "较高",
            "purchase_share_suggestion_expected": "维持现有采购规模，视需求适度调整",
            "risk_control_action_expected": "持续跟踪到货及时率和订单完成情况",
            "development_action_expected": "推动价格优化、供货稳定性提升及重点商品合作",
        })

    elif grade == "C级":
        return pd.Series({
            "cooperation_level_expected": "审慎合作",
            "purchase_priority_expected": "一般",
            "purchase_share_suggestion_expected": "控制采购份额，优先分配给履约稳定的商品",
            "risk_control_action_expected": "设置阶段性履约观察目标，关注延迟和缺货风险",
            "development_action_expected": "要求供应商提出交付改善方案，定期复盘",
        })

    else:
        return pd.Series({
            "cooperation_level_expected": "风险控制",
            "purchase_priority_expected": "低",
            "purchase_share_suggestion_expected": "逐步降低采购依赖",
            "risk_control_action_expected": "重点监控未交付订单，必要时暂停新增采购",
            "development_action_expected": "评估替代供应商，针对异常订单开展专项沟通",
        })


expected_strategy = check_data.apply(
    get_expected_strategy,
    axis=1
)

check_data = pd.concat(
    [check_data, expected_strategy],
    axis=1
)

strategy_mapping = {
    "cooperation_level": "cooperation_level_expected",
    "purchase_priority": "purchase_priority_expected",
    "purchase_share_suggestion": "purchase_share_suggestion_expected",
    "risk_control_action": "risk_control_action_expected",
    "development_action": "development_action_expected",
}

for actual_col, expected_col in strategy_mapping.items():
    compare_column(
        check_data[actual_col],
        check_data[expected_col],
        f"{actual_col} 与供应商评分等级对应策略一致"
    )


# =====================================
# 9. 重新计算管理建议
# =====================================

print("\n【检查6：供应商管理建议】")
print("-" * 65)


def get_expected_advice(row):

    advice = []

    if row["product_count"] == 0:
        advice.append("暂无关联商品，需核实合作关系")

    if row["category_count"] > 1:
        advice.append("具备跨品类供货能力，可评估组合采购")

    if row["supplier_grade"] == "D级":
        advice.append("建议核查异常到货及订单履约原因")

    if row["supplier_grade"] == "B级":
        advice.append("可作为重点备选或稳定供货来源")

    if row["supplier_grade"] == "A级":
        advice.append("可纳入重点供应商资源池")

    if row["supplier_grade"] == "待观察":
        advice.append("当前样本不足，暂不作能力定性")

    if not advice:
        advice.append("按照常规供应商管理周期持续跟踪")

    return "；".join(advice)


expected_advice = check_data.apply(
    get_expected_advice,
    axis=1
)

compare_column(
    check_data["management_advice"],
    expected_advice,
    "management_advice 与重新计算结果一致"
)


# =====================================
# 10. 合作策略与评分等级对应关系
# =====================================

print("\n【检查7：合作策略与评分等级对应关系】")
print("-" * 65)

expected_level_mapping = {
    "A级": "战略合作",
    "B级": "稳定合作",
    "C级": "审慎合作",
    "D级": "风险控制",
    "待观察": "观察合作",
}

expected_priority_mapping = {
    "A级": "最高",
    "B级": "较高",
    "C级": "一般",
    "D级": "低",
    "待观察": "低",
}

expected_level = strategies["supplier_grade"].map(
    expected_level_mapping
)

expected_priority = strategies["supplier_grade"].map(
    expected_priority_mapping
)

compare_column(
    strategies["cooperation_level"],
    expected_level,
    "合作层级与供应商等级对应关系正确"
)

compare_column(
    strategies["purchase_priority"],
    expected_priority,
    "采购优先级与供应商等级对应关系正确"
)


# =====================================
# 11. 策略字段取值检查
# =====================================

print("\n【检查8：策略字段取值范围】")
print("-" * 65)

valid_levels = {
    "战略合作",
    "稳定合作",
    "审慎合作",
    "风险控制",
    "观察合作",
}

valid_priorities = {
    "最高",
    "较高",
    "一般",
    "低",
}

check(
    "合作层级不存在未知取值",
    set(strategies["cooperation_level"]).issubset(valid_levels),
    f"未知取值：{set(strategies['cooperation_level']) - valid_levels}"
)

check(
    "采购优先级不存在未知取值",
    set(strategies["purchase_priority"]).issubset(valid_priorities),
    f"未知取值：{set(strategies['purchase_priority']) - valid_priorities}"
)


# =====================================
# 12. 排序检查
# =====================================

print("\n【检查9：策略表排序】")
print("-" * 65)

sorted_expected = strategies.sort_values(
    by=["total_score", "supplier_id"],
    ascending=[False, True],
    na_position="last"
).reset_index(drop=True)

sorted_actual = strategies.reset_index(drop=True)

check(
    "策略表按照综合评分降序、供应商ID升序排列",
    sorted_actual["supplier_id"].equals(
        sorted_expected["supplier_id"]
    ),
    "实际排序与预期排序不一致"
)


# =====================================
# 13. 输出字段检查
# =====================================

print("\n【检查10：最终输出字段与记录】")
print("-" * 65)

check(
    "输出字段顺序与生成脚本一致",
    list(strategies.columns) == required_columns,
    "字段顺序或字段数量不一致"
)

check(
    "策略表不存在重复记录",
    not strategies.duplicated().any(),
    f"重复记录数量：{strategies.duplicated().sum()}"
)


# =====================================
# 14. 汇总
# =====================================

print("\n" + "=" * 65)
print("供应商合作策略业务逻辑检查汇总")
print("=" * 65)

print(f"检查项目数量：{check_count}")
print(f"通过项目数量：{check_count - len(errors)}")
print(f"异常项目数量：{len(errors)}")

print("\n合作层级分布：")
print(strategies["cooperation_level"].value_counts().to_string())

print("\n采购优先级分布：")
print(strategies["purchase_priority"].value_counts().to_string())

print("\n评分等级与合作层级对应情况：")
print(
    strategies.groupby(
        ["supplier_grade", "cooperation_level"],
        dropna=False
    ).size().to_string()
)

if errors:
    print("\n发现以下异常项目：")
    for item in errors:
        print(f"- {item}")

    print("\nFAIL：供应商合作策略业务逻辑检查未全部通过！")

else:
    print("\nPASS：所有供应商合作策略业务逻辑检查均通过！")

print("=" * 65)
