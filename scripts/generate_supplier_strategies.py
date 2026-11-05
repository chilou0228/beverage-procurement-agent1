
from pathlib import Path

import pandas as pd


# =====================================
# 1. 文件路径
# =====================================

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "processed"

RATINGS_FILE = DATA_DIR / "supplier_ratings_v2.csv"
MAPPING_FILE = DATA_DIR / "product_supplier_mapping.csv"

OUTPUT_FILE = DATA_DIR / "supplier_strategies.csv"


# =====================================
# 2. 读取数据
# =====================================

print("=" * 60)
print("开始生成供应商分级合作策略")
print("=" * 60)

ratings = pd.read_csv(
    RATINGS_FILE,
    encoding="utf-8-sig"
)

mapping = pd.read_csv(
    MAPPING_FILE,
    encoding="utf-8-sig"
)


# =====================================
# 3. 统计供应商商品覆盖情况
# =====================================

supplier_products = (
    mapping.groupby("supplier_id")
    .agg(
        product_count=("sku_id", "nunique"),
        category_count=("category_id", "nunique"),
        primary_product_count=(
            "is_primary",
            "sum"
        )
    )
    .reset_index()
)


# =====================================
# 4. 合并数据
# =====================================

result = ratings.merge(
    supplier_products,
    on="supplier_id",
    how="left",
    validate="one_to_one"
)

for col in [
    "product_count",
    "category_count",
    "primary_product_count",
]:
    result[col] = result[col].fillna(0).astype(int)


# =====================================
# 5. 定义合作策略
# =====================================

def get_cooperation_strategy(row):

    grade = row["supplier_grade"]
    score = row["total_score"]
    product_count = row["product_count"]

    if pd.isna(score):
        return pd.Series({
            "cooperation_level": "观察合作",
            "purchase_priority": "低",
            "purchase_share_suggestion": "暂不扩大采购",
            "risk_control_action": "积累有效履约记录，完成评价后再决定合作规模",
            "development_action": "保持基础沟通，观察后续交付表现",
        })

    if grade == "A级":
        return pd.Series({
            "cooperation_level": "战略合作",
            "purchase_priority": "最高",
            "purchase_share_suggestion": "可优先考虑增加采购份额",
            "risk_control_action": "定期复核价格、库存及履约表现，避免单一供应商依赖",
            "development_action": "探索年度合作、联合促销及重点商品资源支持",
        })

    elif grade == "B级":
        return pd.Series({
            "cooperation_level": "稳定合作",
            "purchase_priority": "较高",
            "purchase_share_suggestion": "维持现有采购规模，视需求适度调整",
            "risk_control_action": "持续跟踪到货及时率和订单完成情况",
            "development_action": "推动价格优化、供货稳定性提升及重点商品合作",
        })

    elif grade == "C级":
        return pd.Series({
            "cooperation_level": "审慎合作",
            "purchase_priority": "一般",
            "purchase_share_suggestion": "控制采购份额，优先分配给履约稳定的商品",
            "risk_control_action": "设置阶段性履约观察目标，关注延迟和缺货风险",
            "development_action": "要求供应商提出交付改善方案，定期复盘",
        })

    else:
        return pd.Series({
            "cooperation_level": "风险控制",
            "purchase_priority": "低",
            "purchase_share_suggestion": "逐步降低采购依赖",
            "risk_control_action": "重点监控未交付订单，必要时暂停新增采购",
            "development_action": "评估替代供应商，针对异常订单开展专项沟通",
        })


strategy_columns = result.apply(
    get_cooperation_strategy,
    axis=1
)

result = pd.concat(
    [result, strategy_columns],
    axis=1
)


# =====================================
# 6. 生成供应商管理建议
# =====================================

def get_management_advice(row):

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


result["management_advice"] = result.apply(
    get_management_advice,
    axis=1
)


# =====================================
# 7. 整理输出
# =====================================

output_columns = [
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

result = result[output_columns].copy()

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
# 8. 输出结果
# =====================================

print("\n供应商合作策略生成完成！")

print(f"供应商数量：{len(result)}")

print("\n合作层级分布：")

print(
    result["cooperation_level"]
    .value_counts()
    .to_string()
)

print("\n供应商策略预览：")

preview_columns = [
    "supplier_name",
    "total_score",
    "supplier_grade",
    "cooperation_level",
    "purchase_priority",
]

print(
    result[preview_columns]
    .head(10)
    .to_string(index=False)
)

print(f"\n文件保存位置：{OUTPUT_FILE}")

print("\n注意：采购份额建议为定性决策建议，不代表实际采购比例。")
print("本策略基于模拟业务数据，仅用于项目分析演示。")

print("\n" + "=" * 60)

