
import re
from pathlib import Path

import numpy as np
import pandas as pd


# ============================================================
# 1. 路径配置与业务规则
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data" / "processed"

PRODUCT_FILE = DATA_DIR / "products.csv"
PROMOTION_FILE = DATA_DIR / "promotions.csv"
DETAIL_FILE = DATA_DIR / "promotion_details.csv"

ACTIVITY_COUNT = 60

PROMOTION_TYPES = {
    "限时折扣",
    "满减活动",
    "多件优惠",
    "组合套餐",
    "买赠活动",
}

PROMOTION_SCENES = {
    "日常促销",
    "周末促销",
    "节日营销",
    "季节性营销",
    "品类主题活动",
}

CATEGORY_DISCOUNT_RULES = {
    "白酒": (0.88, 0.98),
    "葡萄酒": (0.80, 0.95),
    "洋酒": (0.82, 0.96),
    "啤酒": (0.75, 0.95),
    "黄酒": (0.82, 0.96),
    "养生酒/保健酒": (0.85, 0.97),
    "清酒/烧酒": (0.82, 0.96),
    "果酒/米酒": (0.78, 0.94),
    "鸡尾酒/预调酒": (0.75, 0.93),
    "其他酒类": (0.80, 0.96),
}

DEFAULT_DISCOUNT_RULE = (0.80, 0.97)

errors = []
check_count = 0


# ============================================================
# 2. 检查函数
# ============================================================

def check(name, condition, detail=""):
    global check_count

    check_count += 1

    if condition:
        print(f"PASS：{name}，异常数量：0")
    else:
        print(f"FAIL：{name}，{detail}")
        errors.append(name)


def compare_text(actual, expected, name):
    actual = (
        actual.fillna("__NULL__")
        .astype(str)
        .reset_index(drop=True)
    )

    expected = (
        expected.fillna("__NULL__")
        .astype(str)
        .reset_index(drop=True)
    )

    if len(actual) != len(expected):
        check(name, False, "记录数量不一致")
        return

    mismatch = actual != expected

    check(
        name,
        not mismatch.any(),
        f"异常数量：{int(mismatch.sum())}"
    )


def compare_numeric(actual, expected, name, tolerance=0.011):
    actual = pd.to_numeric(
        actual, errors="coerce"
    ).reset_index(drop=True)

    expected = pd.to_numeric(
        expected, errors="coerce"
    ).reset_index(drop=True)

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


# ============================================================
# 3. 读取数据
# ============================================================

print("=" * 65)
print("酒水采销 Agent｜促销活动业务逻辑检查")
print("=" * 65)

products = pd.read_csv(
    PRODUCT_FILE,
    encoding="utf-8-sig"
)

promotions = pd.read_csv(
    PROMOTION_FILE,
    encoding="utf-8-sig"
)

details = pd.read_csv(
    DETAIL_FILE,
    encoding="utf-8-sig"
)

print(f"\n商品档案数量：{len(products)}")
print(f"促销活动数量：{len(promotions)}")
print(f"促销商品明细数量：{len(details)}")


# ============================================================
# 4. 必要字段完整性
# ============================================================

print("\n【检查1：促销主表与明细字段完整性】")
print("-" * 65)

promotion_columns = [
    "promotion_id",
    "promotion_name",
    "promotion_type",
    "promotion_scene",
    "start_date",
    "end_date",
    "duration_days",
    "promotion_status",
    "data_type",
]

detail_columns = [
    "promotion_detail_id",
    "promotion_id",
    "sku_id",
    "product_name",
    "category_name",
    "original_price",
    "purchase_cost",
    "discount_rate",
    "promotion_price",
    "original_unit_profit",
    "promotion_unit_profit",
    "original_gross_margin",
    "promotion_gross_margin",
    "target_quantity",
    "expected_sales_lift",
    "estimated_budget",
    "profit_warning",
    "data_type",
]

missing_promotion = [
    col for col in promotion_columns
    if col not in promotions.columns
]

missing_detail = [
    col for col in detail_columns
    if col not in details.columns
]

check(
    "促销主表包含全部必要字段",
    len(missing_promotion) == 0,
    f"缺失字段：{missing_promotion}"
)

check(
    "促销明细表包含全部必要字段",
    len(missing_detail) == 0,
    f"缺失字段：{missing_detail}"
)

if missing_promotion or missing_detail:
    raise SystemExit("必要字段缺失，停止检查。")

check(
    "促销主表必要字段不存在空值",
    not promotions[promotion_columns].isna().any().any(),
    f"空值数量：{int(promotions[promotion_columns].isna().sum().sum())}"
)

check(
    "促销明细必要字段不存在空值",
    not details[detail_columns].isna().any().any(),
    f"空值数量：{int(details[detail_columns].isna().sum().sum())}"
)


# ============================================================
# 5. 促销活动数量与ID唯一性
# ============================================================

print("\n【检查2：促销活动数量与ID唯一性】")
print("-" * 65)

check(
    "促销活动数量为60场",
    len(promotions) == ACTIVITY_COUNT,
    f"实际数量：{len(promotions)}"
)

check(
    "promotion_id 不存在重复",
    promotions["promotion_id"].is_unique,
    f"重复数量：{promotions['promotion_id'].duplicated().sum()}"
)

expected_promotion_ids = {
    f"PROMO{i:04d}"
    for i in range(1, ACTIVITY_COUNT + 1)
}

check(
    "促销活动ID连续且完整",
    set(promotions["promotion_id"]) == expected_promotion_ids,
    "促销活动ID缺失或存在未知ID"
)

check(
    "promotion_detail_id 不存在重复",
    details["promotion_detail_id"].is_unique,
    f"重复数量：{details['promotion_detail_id'].duplicated().sum()}"
)

detail_id_valid = details["promotion_detail_id"].astype(str).str.fullmatch(
    r"PDET\d{6}"
)

check(
    "促销明细ID符合PDET加六位数字格式",
    detail_id_valid.all(),
    f"异常数量：{int((~detail_id_valid).sum())}"
)

detail_id_numbers = pd.to_numeric(
    details["promotion_detail_id"]
    .astype(str)
    .str.replace("PDET", "", regex=False),
    errors="coerce"
)

check(
    "促销明细ID连续且不存在缺失",
    (
        detail_id_numbers.notna().all()
        and set(detail_id_numbers.astype(int))
        == set(range(1, len(details) + 1))
    ),
    "促销明细ID编号不连续"
)


# ============================================================
# 6. 促销类型与活动场景
# ============================================================

print("\n【检查3：促销类型与活动场景】")
print("-" * 65)

check(
    "促销类型均属于预设类型",
    promotions["promotion_type"].isin(
        PROMOTION_TYPES
    ).all(),
    f"未知类型：{set(promotions['promotion_type']) - PROMOTION_TYPES}"
)

check(
    "促销场景均属于预设场景",
    promotions["promotion_scene"].isin(
        PROMOTION_SCENES
    ).all(),
    f"未知场景：{set(promotions['promotion_scene']) - PROMOTION_SCENES}"
)

check(
    "促销状态均为模拟待执行",
    promotions["promotion_status"].eq("模拟待执行").all(),
    "存在其他促销状态"
)

check(
    "促销主表数据类型均为simulated",
    promotions["data_type"].eq("simulated").all(),
    "存在非模拟数据标识"
)

check(
    "促销明细数据类型均为simulated",
    details["data_type"].eq("simulated").all(),
    "存在非模拟数据标识"
)


# ============================================================
# 7. 促销活动日期与持续时间
# ============================================================

print("\n【检查4：促销活动日期与持续时间】")
print("-" * 65)

promotions["start_date"] = pd.to_datetime(
    promotions["start_date"],
    errors="coerce"
)

promotions["end_date"] = pd.to_datetime(
    promotions["end_date"],
    errors="coerce"
)

check(
    "促销开始日期不存在无效值",
    promotions["start_date"].notna().all(),
    f"异常数量：{int(promotions['start_date'].isna().sum())}"
)

check(
    "促销结束日期不存在无效值",
    promotions["end_date"].notna().all(),
    f"异常数量：{int(promotions['end_date'].isna().sum())}"
)

valid_dates = (
    promotions["start_date"].notna()
    & promotions["end_date"].notna()
)

date_order_valid = (
    promotions.loc[valid_dates, "end_date"]
    >= promotions.loc[valid_dates, "start_date"]
).all()

check(
    "促销结束日期不早于开始日期",
    date_order_valid,
    "存在结束日期早于开始日期的活动"
)

expected_duration = (
    promotions["end_date"] - promotions["start_date"]
).dt.days + 1

compare_numeric(
    promotions["duration_days"],
    expected_duration,
    "活动持续天数等于结束日期减开始日期加1",
    tolerance=0
)

check(
    "促销活动持续时间为3至15天",
    pd.to_numeric(
        promotions["duration_days"],
        errors="coerce"
    ).between(3, 15).all(),
    "存在不符合持续时间设定的活动"
)

start_boundary = pd.Timestamp("2026-10-01")
end_boundary = pd.Timestamp("2027-09-30")

check(
    "促销开始日期处于设定年度范围",
    promotions["start_date"].between(
        start_boundary,
        end_boundary
    ).all(),
    "存在超出设定日期范围的活动"
)

check(
    "促销结束日期不超过设定年度末日",
    (promotions["end_date"] <= end_boundary).all(),
    "存在结束日期超过2027-09-30的活动"
)


# ============================================================
# 8. 活动主表名称一致性
# ============================================================

print("\n【检查5：促销活动名称】")
print("-" * 65)

promotion_number = pd.to_numeric(
    promotions["promotion_id"]
    .astype(str)
    .str.extract(r"PROMO(\d{4})")[0],
    errors="coerce"
)

expected_names = pd.Series(
    [
        f"{scene}-{ptype}-{int(number):03d}"
        if pd.notna(number) else None
        for scene, ptype, number in zip(
            promotions["promotion_scene"],
            promotions["promotion_type"],
            promotion_number
        )
    ],
    index=promotions.index
)

compare_text(
    promotions["promotion_name"],
    expected_names,
    "促销活动名称与场景、类型及ID一致"
)


# ============================================================
# 9. 促销明细与活动主表关联
# ============================================================

print("\n【检查6：促销明细与活动主表关联】")
print("-" * 65)

check(
    "全部促销明细均能关联活动主表",
    details["promotion_id"].isin(
        promotions["promotion_id"]
    ).all(),
    f"孤立明细数量：{int((~details['promotion_id'].isin(promotions['promotion_id'])).sum())}"
)

detail_counts = details.groupby("promotion_id").size()

check(
    "60场活动均有对应商品明细",
    set(detail_counts.index) == set(promotions["promotion_id"]),
    "存在没有商品明细的活动"
)

check(
    "每场活动选择5至20个商品",
    detail_counts.between(5, 20).all(),
    f"异常活动数量：{int((~detail_counts.between(5, 20)).sum())}"
)

check(
    "同一场活动不存在重复SKU",
    not details.duplicated(
        subset=["promotion_id", "sku_id"]
    ).any(),
    f"重复组合数量：{int(details.duplicated(subset=['promotion_id', 'sku_id']).sum())}"
)


# ============================================================
# 10. 促销明细与商品档案关联
# ============================================================

print("\n【检查7：促销明细与商品档案关联】")
print("-" * 65)

product_info = products[
    [
        "sku_id",
        "product_name",
        "category_name",
        "selling_price",
        "purchase_cost",
    ]
].copy()

for col in ["selling_price", "purchase_cost"]:
    product_info[col] = pd.to_numeric(
        product_info[col],
        errors="coerce"
    )

merged = details.merge(
    product_info,
    on="sku_id",
    how="left",
    suffixes=("", "_expected"),
    validate="many_to_one"
)

check(
    "全部促销SKU均能关联商品档案",
    merged["selling_price"].notna().all(),
    f"孤立SKU数量：{int(merged['selling_price'].isna().sum())}"
)

compare_text(
    merged["product_name"],
    merged["product_name_expected"],
    "促销商品名称与商品档案一致"
)

compare_text(
    merged["category_name"],
    merged["category_name_expected"],
    "促销商品品类与商品档案一致"
)


# ============================================================
# 11. 促销价格及采购成本
# ============================================================

print("\n【检查8：原价与采购成本一致性】")
print("-" * 65)

numeric_columns = [
    "original_price",
    "purchase_cost",
    "discount_rate",
    "promotion_price",
    "original_unit_profit",
    "promotion_unit_profit",
    "original_gross_margin",
    "promotion_gross_margin",
    "target_quantity",
    "expected_sales_lift",
    "estimated_budget",
]

for col in numeric_columns:
    merged[col] = pd.to_numeric(
        merged[col],
        errors="coerce"
    )

    check(
        f"{col} 不存在缺失或非数字值",
        merged[col].notna().all(),
        f"异常数量：{int(merged[col].isna().sum())}"
    )

compare_numeric(
    merged["original_price"],
    merged["selling_price"].round(2),
    "商品原价与商品档案售价一致"
)

compare_numeric(
    merged["purchase_cost"],
    merged["purchase_cost_expected"].round(2),
    "促销采购成本与商品档案一致"
)

check(
    "商品原价均大于0",
    (merged["original_price"] > 0).all(),
    "存在原价小于或等于0的记录"
)

check(
    "采购成本均不小于0",
    (merged["purchase_cost"] >= 0).all(),
    "存在负数采购成本"
)

check(
    "促销价格均大于0",
    (merged["promotion_price"] > 0).all(),
    "存在小于或等于0的促销价格"
)


# ============================================================
# 12. 品类折扣区间与默认规则
# ============================================================

print("\n【检查9：品类折扣规则】")
print("-" * 65)

def get_discount_rule(category):
    return CATEGORY_DISCOUNT_RULES.get(
        str(category),
        DEFAULT_DISCOUNT_RULE
    )


discount_bounds = merged["category_name"].apply(
    get_discount_rule
)

merged["discount_min"] = discount_bounds.apply(lambda x: x[0])
merged["discount_max"] = discount_bounds.apply(lambda x: x[1])

discount_valid = (
    merged["discount_rate"].between(
        merged["discount_min"],
        merged["discount_max"]
    )
)

check(
    "促销折扣率符合对应品类折扣区间",
    discount_valid.all(),
    f"异常明细数量：{int((~discount_valid).sum())}"
)

fallback_categories = sorted(
    set(merged["category_name"].astype(str))
    - set(CATEGORY_DISCOUNT_RULES.keys())
)

print("\n使用默认折扣规则的品类：")

if fallback_categories:
    for category in fallback_categories:
        count = int(
            (merged["category_name"] == category).sum()
        )
        print(
            f"提示：{category}，明细数量：{count}，"
            f"使用默认区间{DEFAULT_DISCOUNT_RULE}"
        )
else:
    print("无，所有品类均匹配专属折扣规则。")


# ============================================================
# 13. 促销价格计算
# ============================================================

print("\n【检查10：促销价格计算】")
print("-" * 65)

expected_promotion_price = (
    merged["original_price"]
    * merged["discount_rate"]
).round(2)

compare_numeric(
    merged["promotion_price"],
    expected_promotion_price,
    "促销价格等于原价乘以折扣率"
)

check(
    "促销价格不高于商品原价",
    (
        merged["promotion_price"]
        <= merged["original_price"]
    ).all(),
    "存在促销价格高于原价的记录"
)


# ============================================================
# 14. 促销前后单件毛利
# ============================================================

print("\n【检查11：促销前后单件毛利计算】")
print("-" * 65)

expected_original_profit = (
    merged["original_price"]
    - merged["purchase_cost"]
).round(2)

expected_promotion_profit = (
    merged["promotion_price"]
    - merged["purchase_cost"]
).round(2)

compare_numeric(
    merged["original_unit_profit"],
    expected_original_profit,
    "促销前单件毛利计算正确"
)

compare_numeric(
    merged["promotion_unit_profit"],
    expected_promotion_profit,
    "促销后单件毛利计算正确"
)


# ============================================================
# 15. 促销前后毛利率
# ============================================================

print("\n【检查12：促销前后毛利率计算】")
print("-" * 65)

expected_original_margin = (
    expected_original_profit
    / merged["original_price"]
).round(4)

expected_promotion_margin = (
    expected_promotion_profit
    / merged["promotion_price"]
).round(4)

compare_numeric(
    merged["original_gross_margin"],
    expected_original_margin,
    "促销前毛利率计算正确",
    tolerance=0.0001
)

compare_numeric(
    merged["promotion_gross_margin"],
    expected_promotion_margin,
    "促销后毛利率计算正确",
    tolerance=0.0001
)


# ============================================================
# 16. 目标销量、提升幅度与预算
# ============================================================

print("\n【检查13：目标销量及预算参数】")
print("-" * 65)

quantity = merged["target_quantity"]

check(
    "目标销量处于20至500件之间",
    quantity.between(20, 500).all(),
    "存在超出目标销量范围的记录"
)

check(
    "目标销量均为整数",
    np.isclose(
        quantity,
        np.round(quantity),
        atol=1e-9
    ).all(),
    "存在非整数目标销量"
)

check(
    "预期销量提升幅度处于5%至50%之间",
    merged["expected_sales_lift"].between(
        0.05, 0.50
    ).all(),
    "存在超出设定范围的记录"
)

check(
    "预估活动预算处于500至10000元之间",
    merged["estimated_budget"].between(
        500, 10000
    ).all(),
    "存在超出预算区间的记录"
)


# ============================================================
# 17. 毛利预警逻辑
# ============================================================

print("\n【检查14：促销毛利风险预警】")
print("-" * 65)

def get_expected_warning(row):

    if row["promotion_unit_profit"] < 0:
        return "促销价格低于采购成本"

    elif row["promotion_gross_margin"] < 0.10:
        return "促销后毛利率低于10%"

    else:
        return "毛利空间正常"


expected_warning = merged.apply(
    get_expected_warning,
    axis=1
)

compare_text(
    merged["profit_warning"],
    expected_warning,
    "毛利预警与促销毛利计算结果一致"
)

check(
    "低于采购成本的商品均触发负毛利预警",
    (
        merged.loc[
            merged["promotion_unit_profit"] < 0,
            "profit_warning"
        ] == "促销价格低于采购成本"
    ).all(),
    "存在负毛利但未触发预警的商品"
)


# ============================================================
# 18. 结果分布
# ============================================================

print("\n【检查15：促销数据分布】")
print("-" * 65)

print("促销类型分布：")
print(promotions["promotion_type"].value_counts().to_string())

print("\n活动场景分布：")
print(promotions["promotion_scene"].value_counts().to_string())

print("\n促销商品品类分布：")
print(details["category_name"].value_counts().to_string())

print("\n促销毛利预警分布：")
print(details["profit_warning"].value_counts().to_string())

print("\n促销折扣率统计：")
print(merged["discount_rate"].describe().round(3).to_string())

print("\n促销前后毛利率统计：")
print(
    merged[
        [
            "original_gross_margin",
            "promotion_gross_margin",
        ]
    ].describe().round(4).to_string()
)


# ============================================================
# 19. 最终检查汇总
# ============================================================

print("\n" + "=" * 65)
print("促销活动业务逻辑检查汇总")
print("=" * 65)

print(f"商品档案数量：{len(products)}")
print(f"促销活动数量：{len(promotions)}")
print(f"促销商品明细数量：{len(details)}")

print(
    f"平均每场活动商品数："
    f"{detail_counts.mean():.2f}"
)

print(f"\n检查项目数量：{check_count}")
print(f"通过项目数量：{check_count - len(errors)}")
print(f"异常项目数量：{len(errors)}")

if errors:
    print("\n发现以下异常项目：")

    for item in errors:
        print(f"- {item}")

    print("\nFAIL：促销活动业务逻辑检查未全部通过！")

else:
    print("\nPASS：所有促销活动业务逻辑检查均通过！")

print("=" * 65)

