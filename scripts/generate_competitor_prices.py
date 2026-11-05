
import pandas as pd
import numpy as np
from pathlib import Path


# ============================================================
# 1. 基础配置
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[1]
PRODUCT_FILE = BASE_DIR / "data" / "processed" / "products.csv"
OUTPUT_FILE = BASE_DIR / "data" / "processed" / "competitor_prices.csv"

RANDOM_SEED = 20261104
COMPETITOR_COUNT_MIN = 2
COMPETITOR_COUNT_MAX = 4

rng = np.random.default_rng(RANDOM_SEED)


# ============================================================
# 2. 读取商品档案
# ============================================================

def load_products():
    if not PRODUCT_FILE.exists():
        raise FileNotFoundError(f"找不到商品档案：{PRODUCT_FILE}")

    products = pd.read_csv(PRODUCT_FILE)

    required_columns = [
        "sku_id",
        "product_name",
        "brand",
        "category_name",
        "selling_price"
    ]

    missing = [col for col in required_columns if col not in products.columns]

    if missing:
        raise ValueError(f"商品档案缺少必要字段：{missing}")

    if products["sku_id"].duplicated().any():
        raise ValueError("商品档案存在重复SKU，请先检查商品数据。")

    products["selling_price"] = pd.to_numeric(
        products["selling_price"], errors="coerce"
    )

    if products["selling_price"].isna().any():
        raise ValueError("商品售价存在缺失或非数字数据。")

    if (products["selling_price"] <= 0).any():
        raise ValueError("商品售价必须大于0。")

    return products


# ============================================================
# 3. 模拟竞品信息
# ============================================================

COMPETITOR_CHANNELS = [
    "综合电商平台",
    "品牌官方旗舰店",
    "垂直酒水电商",
    "区域酒水零售商"
]

PRICE_TYPES = [
    "日常售价",
    "促销售价"
]

PROMOTION_PROBABILITY = 0.25


# ============================================================
# 4. 生成竞品价格
# ============================================================

def generate_competitor_prices(products):

    records = []

    competitor_counter = 1

    for _, product in products.iterrows():

        sku_id = product["sku_id"]
        product_name = product["product_name"]
        brand = product["brand"]
        category_name = product["category_name"]
        own_price = float(product["selling_price"])

        competitor_count = int(
            rng.integers(
                COMPETITOR_COUNT_MIN,
                COMPETITOR_COUNT_MAX + 1
            )
        )

        for competitor_index in range(competitor_count):

            # 竞品价格围绕本商品售价上下波动
            price_ratio = float(
                np.clip(
                    rng.normal(loc=1.0, scale=0.12),
                    0.65,
                    1.40
                )
            )

            competitor_price = round(
                own_price * price_ratio,
                2
            )

            # 竞品名称仅作为模拟对标对象，不代表真实市场商品
            competitor_name = (
                f"{category_name}模拟竞品"
                f"{competitor_counter:04d}"
            )

            competitor_brand = (
                f"模拟竞品品牌{(competitor_counter - 1) % 30 + 1:02d}"
            )

            channel = rng.choice(COMPETITOR_CHANNELS)

            # 模拟竞品促销状态
            is_promotion = bool(
                rng.random() < PROMOTION_PROBABILITY
            )

            if is_promotion:
                price_type = "促销售价"
                discount_rate = round(
                    float(rng.uniform(0.85, 0.98)),
                    3
                )
                final_price = round(
                    competitor_price * discount_rate,
                    2
                )
            else:
                price_type = "日常售价"
                discount_rate = 1.0
                final_price = competitor_price

            # 计算相对本商品售价的价格差异
            price_difference = round(
                final_price - own_price,
                2
            )

            price_difference_rate = round(
                price_difference / own_price,
                4
            )

            if price_difference_rate <= -0.10:
                price_position = "明显低于本品"
            elif price_difference_rate < 0:
                price_position = "略低于本品"
            elif price_difference_rate <= 0.10:
                price_position = "接近本品"
            else:
                price_position = "高于本品"

            records.append({
                "competitor_id": f"COMP{competitor_counter:05d}",
                "sku_id": sku_id,
                "product_name": product_name,
                "category_name": category_name,
                "reference_brand": brand,
                "competitor_name": competitor_name,
                "competitor_brand": competitor_brand,
                "competitor_channel": channel,
                "competitor_list_price": competitor_price,
                "discount_rate": discount_rate,
                "competitor_price": final_price,
                "price_type": price_type,
                "own_selling_price": own_price,
                "price_difference": price_difference,
                "price_difference_rate": price_difference_rate,
                "price_position": price_position,
                "data_type": "simulated"
            })

            competitor_counter += 1

    return pd.DataFrame(records)


# ============================================================
# 5. 数据质量检查
# ============================================================

def check_competitor_prices(df, products):

    assert len(df) > 0, "竞品价格数据为空。"

    assert df["competitor_id"].is_unique, "竞品ID存在重复。"

    assert df["sku_id"].isin(products["sku_id"]).all(), \
        "存在不属于商品档案的SKU。"

    assert df["competitor_price"].notna().all(), \
        "竞品价格存在缺失。"

    assert (df["competitor_price"] > 0).all(), \
        "竞品价格必须大于0。"

    assert df["price_difference_rate"].notna().all(), \
        "价格差异比例存在缺失。"

    assert df["data_type"].eq("simulated").all(), \
        "数据类型标识异常。"

    competitor_counts = df.groupby("sku_id").size()

    assert competitor_counts.index.nunique() == len(products), \
        "并非所有商品都有竞品价格记录。"

    assert competitor_counts.between(
        COMPETITOR_COUNT_MIN,
        COMPETITOR_COUNT_MAX
    ).all(), "部分商品竞品数量不符合设定。"

    print("\n数据质量检查：全部通过")


# ============================================================
# 6. 主程序
# ============================================================

def main():

    print("=" * 60)
    print("开始生成竞品价格模拟数据")
    print("=" * 60)

    products = load_products()

    print(f"读取商品数量：{len(products)}")

    competitor_prices = generate_competitor_prices(products)

    check_competitor_prices(
        competitor_prices,
        products
    )

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    competitor_prices.to_csv(
        OUTPUT_FILE,
        index=False,
        encoding="utf-8-sig"
    )

    print("\n竞品价格数据生成完成！")
    print(f"商品数量：{len(products)}")
    print(f"竞品记录数：{len(competitor_prices)}")
    print(
        f"平均每个商品竞品数："
        f"{competitor_prices.groupby('sku_id').size().mean():.2f}"
    )

    print("\n竞品价格类型分布：")
    print(competitor_prices["price_type"].value_counts())

    print("\n竞品价格位置分布：")
    print(competitor_prices["price_position"].value_counts())

    print("\n竞品价格数据预览：")
    print(
        competitor_prices[
            [
                "product_name",
                "competitor_brand",
                "competitor_channel",
                "competitor_price",
                "own_selling_price",
                "price_position"
            ]
        ].head(10).to_string(index=False)
    )

    print(f"\n文件保存位置：{OUTPUT_FILE}")

    print("\n注意：")
    print("1. 所有竞品名称、品牌和价格均为模拟数据。")
    print("2. 价格差异仅用于演示竞品价格分析逻辑。")
    print("3. 不代表真实市场报价或真实品牌竞争关系。")

    print("=" * 60)


if __name__ == "__main__":
    main()

