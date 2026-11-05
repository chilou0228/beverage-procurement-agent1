
import re
from pathlib import Path

import numpy as np
import pandas as pd


# ============================================================
# 1. 路径配置
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[1]

PRODUCT_FILE = BASE_DIR / "data" / "processed" / "products.csv"
COMPETITOR_FILE = BASE_DIR / "data" / "processed" / "competitor_prices.csv"

COMPETITOR_COUNT_MIN = 2
COMPETITOR_COUNT_MAX = 4

ALLOWED_CHANNELS = {
    "综合电商平台",
    "品牌官方旗舰店",
    "垂直酒水电商",
    "区域酒水零售商",
}

ALLOWED_PRICE_TYPES = {
    "日常售价",
    "促销售价",
}

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
print("酒水采销 Agent｜竞品价格业务逻辑检查")
print("=" * 65)

products = pd.read_csv(
    PRODUCT_FILE,
    encoding="utf-8-sig"
)

competitors = pd.read_csv(
    COMPETITOR_FILE,
    encoding="utf-8-sig"
)

print(f"\n商品档案数量：{len(products)}")
print(f"竞品价格记录：{len(competitors)}")


# ============================================================
# 4. 基础字段完整性
# ============================================================

print("\n【检查1：竞品数据字段完整性】")
print("-" * 65)

required_columns = [
    "competitor_id",
    "sku_id",
    "product_name",
    "category_name",
    "reference_brand",
    "competitor_name",
    "competitor_brand",
    "competitor_channel",
    "competitor_list_price",
    "discount_rate",
    "competitor_price",
    "price_type",
    "own_selling_price",
    "price_difference",
    "price_difference_rate",
    "price_position",
    "data_type",
]

missing_columns = [
    col for col in required_columns
    if col not in competitors.columns
]

check(
    "竞品数据包含全部必要字段",
    len(missing_columns) == 0,
    f"缺失字段：{missing_columns}"
)

if missing_columns:
    raise SystemExit("竞品数据字段不完整，停止检查。")

check(
    "竞品数据不存在空值",
    not competitors[required_columns].isna().any().any(),
    f"空值数量：{int(competitors[required_columns].isna().sum().sum())}"
)


# ============================================================
# 5. 商品覆盖与竞品数量
# ============================================================

print("\n【检查2：商品覆盖与竞品数量】")
print("-" * 65)

competitor_counts = competitors.groupby("sku_id").size()

check(
    "每个商品均有竞品价格记录",
    set(competitor_counts.index) == set(products["sku_id"]),
    "部分商品缺少竞品记录或存在未知SKU"
)

check(
    "每个商品竞品数量在2至4条之间",
    competitor_counts.between(
        COMPETITOR_COUNT_MIN,
        COMPETITOR_COUNT_MAX
    ).all(),
    f"异常商品数量：{int((~competitor_counts.between(COMPETITOR_COUNT_MIN, COMPETITOR_COUNT_MAX)).sum())}"
)

check(
    "竞品记录总数等于各SKU竞品数量之和",
    int(competitor_counts.sum()) == len(competitors),
    "记录数量汇总不一致"
)


# ============================================================
# 6. 竞品ID与唯一性
# ============================================================

print("\n【检查3：竞品ID与记录唯一性】")
print("-" * 65)

check(
    "competitor_id 不存在重复",
    competitors["competitor_id"].is_unique,
    f"重复数量：{competitors['competitor_id'].duplicated().sum()}"
)

id_pattern_valid = competitors["competitor_id"].astype(str).str.fullmatch(
    r"COMP\d{5}"
)

check(
    "竞品ID符合COMP加五位数字格式",
    id_pattern_valid.all(),
    f"异常数量：{int((~id_pattern_valid).sum())}"
)

id_numbers = (
    competitors["competitor_id"]
    .astype(str)
    .str.replace("COMP", "", regex=False)
)

id_numbers = pd.to_numeric(id_numbers, errors="coerce")

check(
    "竞品ID编号连续且不存在缺失",
    (
        id_numbers.notna().all()
        and set(id_numbers.astype(int))
        == set(range(1, len(competitors) + 1))
    ),
    "竞品ID编号不连续或存在缺失"
)


# ============================================================
# 7. 关联商品档案
# ============================================================

print("\n【检查4：竞品数据与商品档案关联】")
print("-" * 65)

product_info = products[
    [
        "sku_id",
        "product_name",
        "brand",
        "category_name",
        "selling_price",
    ]
].copy()

product_info["selling_price"] = pd.to_numeric(
    product_info["selling_price"],
    errors="coerce"
)

merged = competitors.merge(
    product_info,
    on="sku_id",
    how="left",
    suffixes=("", "_expected"),
    validate="many_to_one"
)

check(
    "全部竞品记录均能关联商品档案",
    merged["selling_price"].notna().all(),
    f"孤立记录数量：{int(merged['selling_price'].isna().sum())}"
)

compare_text(
    merged["product_name"],
    merged["product_name_expected"],
    "商品名称与商品档案一致"
)

compare_text(
    merged["category_name"],
    merged["category_name_expected"],
    "商品品类与商品档案一致"
)

compare_text(
    merged["reference_brand"],
    merged["brand"],
    "参考品牌与商品档案一致"
)

compare_numeric(
    merged["own_selling_price"],
    merged["selling_price"],
    "本品售价与商品档案基础售价一致"
)


# ============================================================
# 8. 竞品价格基础合理性
# ============================================================

print("\n【检查5：竞品价格基础合理性】")
print("-" * 65)

numeric_columns = [
    "competitor_list_price",
    "discount_rate",
    "competitor_price",
    "own_selling_price",
    "price_difference",
    "price_difference_rate",
]

for col in numeric_columns:
    competitors[col] = pd.to_numeric(
        competitors[col],
        errors="coerce"
    )

    check(
        f"{col} 不存在空值或非数字数据",
        competitors[col].notna().all(),
        f"异常数量：{int(competitors[col].isna().sum())}"
    )

check(
    "竞品标价均大于0",
    (competitors["competitor_list_price"] > 0).all(),
    "存在小于或等于0的竞品标价"
)

check(
    "竞品最终售价均大于0",
    (competitors["competitor_price"] > 0).all(),
    "存在小于或等于0的竞品最终售价"
)

check(
    "本品参考售价均大于0",
    (competitors["own_selling_price"] > 0).all(),
    "存在小于或等于0的本品参考售价"
)


# ============================================================
# 9. 竞品标价生成区间
# ============================================================

print("\n【检查6：竞品标价波动范围】")
print("-" * 65)

# 原生成脚本设置：
# price_ratio = clip(normal(1.0, 0.12), 0.65, 1.40)
# competitor_list_price = round(own_price * price_ratio, 2)

lower_bound = (
    competitors["own_selling_price"] * 0.65
).round(2)

upper_bound = (
    competitors["own_selling_price"] * 1.40
).round(2)

within_price_range = (
    (competitors["competitor_list_price"] >= lower_bound)
    &
    (competitors["competitor_list_price"] <= upper_bound)
)

check(
    "竞品标价处于本品售价65%至140%范围",
    within_price_range.all(),
    f"异常记录数量：{int((~within_price_range).sum())}"
)


# ============================================================
# 10. 竞品促销状态与折扣计算
# ============================================================

print("\n【检查7：促销状态与折扣计算】")
print("-" * 65)

promotion_mask = competitors["price_type"].eq("促销售价")
normal_mask = competitors["price_type"].eq("日常售价")

check(
    "价格类型仅包含日常售价和促销售价",
    competitors["price_type"].isin(ALLOWED_PRICE_TYPES).all(),
    f"异常取值：{set(competitors['price_type']) - ALLOWED_PRICE_TYPES}"
)

check(
    "促销售价折扣率处于0.85至0.98之间",
    competitors.loc[
        promotion_mask, "discount_rate"
    ].between(0.85, 0.98).all(),
    "存在超出促销折扣范围的记录"
)

check(
    "日常售价折扣率均为1.0",
    np.isclose(
        competitors.loc[normal_mask, "discount_rate"],
        1.0,
        atol=1e-9
    ).all(),
    "存在日常售价折扣率不等于1.0的记录"
)

expected_final_price = (
    competitors["competitor_list_price"]
    * competitors["discount_rate"]
).round(2)

compare_numeric(
    competitors["competitor_price"],
    expected_final_price,
    "竞品最终售价等于竞品标价乘以折扣率"
)

check(
    "促销售价低于或等于竞品标价",
    (
        competitors.loc[
            promotion_mask, "competitor_price"
        ]
        <= competitors.loc[
            promotion_mask, "competitor_list_price"
        ]
    ).all(),
    "存在促销最终售价高于竞品标价的记录"
)


# ============================================================
# 11. 价格差异计算
# ============================================================

print("\n【检查8：价格差异计算】")
print("-" * 65)

expected_difference = (
    competitors["competitor_price"]
    - competitors["own_selling_price"]
).round(2)

expected_difference_rate = (
    expected_difference
    / competitors["own_selling_price"]
).round(4)

compare_numeric(
    competitors["price_difference"],
    expected_difference,
    "价格差异等于竞品最终售价减去本品售价"
)

compare_numeric(
    competitors["price_difference_rate"],
    expected_difference_rate,
    "价格差异比例计算正确",
    tolerance=0.00001
)


# ============================================================
# 12. 价格位置分类
# ============================================================

print("\n【检查9：竞品价格位置分类】")
print("-" * 65)


def classify_price_position(rate):

    if rate <= -0.10:
        return "明显低于本品"
    elif rate < 0:
        return "略低于本品"
    elif rate <= 0.10:
        return "接近本品"
    else:
        return "高于本品"


expected_position = (
    competitors["price_difference_rate"]
    .apply(classify_price_position)
)

compare_text(
    competitors["price_position"],
    expected_position,
    "竞品价格位置与价格差异比例对应正确"
)


# ============================================================
# 13. 竞品渠道和模拟标识
# ============================================================

print("\n【检查10：竞品来源与模拟标识】")
print("-" * 65)

check(
    "竞品渠道均属于预设渠道",
    competitors["competitor_channel"].isin(
        ALLOWED_CHANNELS
    ).all(),
    f"未知渠道：{set(competitors['competitor_channel']) - ALLOWED_CHANNELS}"
)

competitor_name_valid = pd.Series(
    [
        str(name).startswith(f"{category}模拟竞品")
        for name, category in zip(
            competitors["competitor_name"],
            competitors["category_name"]
        )
    ],
    index=competitors.index
)

check(
    "竞品名称均使用模拟竞品标识",
    competitor_name_valid.all(),
    f"异常数量：{int((~competitor_name_valid).sum())}"
)

check(
    "竞品品牌均使用模拟品牌标识",
    competitors["competitor_brand"]
    .astype(str)
    .str.fullmatch(r"模拟竞品品牌\d{2}").all(),
    "存在不符合模拟品牌命名规则的记录"
)

check(
    "数据类型均标记为simulated",
    competitors["data_type"].eq("simulated").all(),
    f"异常数量：{int((competitors['data_type'] != 'simulated').sum())}"
)


# ============================================================
# 14. 数据分布与输出汇总
# ============================================================

print("\n【检查11：数据分布与结果汇总】")
print("-" * 65)

check(
    "促销数据折扣率不超过1",
    (competitors["discount_rate"] <= 1).all(),
    "存在大于1的折扣率"
)

check(
    "每个SKU竞品数量统计正确",
    int(competitor_counts.sum()) == len(competitors),
    "SKU竞品数量汇总异常"
)

print("\n竞品价格类型分布：")
print(competitors["price_type"].value_counts().to_string())

print("\n竞品价格位置分布：")
print(competitors["price_position"].value_counts().to_string())

print("\n竞品渠道分布：")
print(competitors["competitor_channel"].value_counts().to_string())

print("\n竞品价格统计：")
print(
    competitors[
        [
            "competitor_list_price",
            "competitor_price",
            "own_selling_price",
        ]
    ].describe().round(2).to_string()
)


# ============================================================
# 15. 最终检查结果
# ============================================================

print("\n" + "=" * 65)
print("竞品价格业务逻辑检查汇总")
print("=" * 65)

print(f"商品数量：{len(products)}")
print(f"竞品记录数：{len(competitors)}")
print(
    f"平均每个商品竞品数："
    f"{competitors.groupby('sku_id').size().mean():.2f}"
)

print(f"\n检查项目数量：{check_count}")
print(f"通过项目数量：{check_count - len(errors)}")
print(f"异常项目数量：{len(errors)}")

if errors:
    print("\n发现以下异常项目：")
    for item in errors:
        print(f"- {item}")

    print("\nFAIL：竞品价格业务逻辑检查未全部通过！")
else:
    print("\nPASS：所有竞品价格业务逻辑检查均通过！")

print("=" * 65)
