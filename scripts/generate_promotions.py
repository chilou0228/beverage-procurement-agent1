
import pandas as pd
import numpy as np
from pathlib import Path


# ============================================================
# 1. 基础配置
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[1]

PRODUCT_FILE = BASE_DIR / "data" / "processed" / "products.csv"
OUTPUT_FILE = BASE_DIR / "data" / "processed" / "promotions.csv"
DETAIL_OUTPUT_FILE = BASE_DIR / "data" / "processed" / "promotion_details.csv"

RANDOM_SEED = 20261105
rng = np.random.default_rng(RANDOM_SEED)

ACTIVITY_COUNT = 60


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
        "category_id",
        "category_name",
        "selling_price",
        "purchase_cost",
        "gross_margin"
    ]

    missing = [
        col for col in required_columns
        if col not in products.columns
    ]

    if missing:
        raise ValueError(f"商品档案缺少必要字段：{missing}")

    if products["sku_id"].duplicated().any():
        raise ValueError("商品档案存在重复SKU。")

    numeric_columns = [
        "selling_price",
        "purchase_cost",
        "gross_margin"
    ]

    for col in numeric_columns:
        products[col] = pd.to_numeric(
            products[col],
            errors="coerce"
        )

        if products[col].isna().any():
            raise ValueError(f"商品字段 {col} 存在缺失或非数字数据。")

    if (products["selling_price"] <= 0).any():
        raise ValueError("商品售价必须大于0。")

    if (products["purchase_cost"] < 0).any():
        raise ValueError("采购成本不能小于0。")

    return products


# ============================================================
# 3. 促销活动规则
# ============================================================

PROMOTION_TYPES = [
    "限时折扣",
    "满减活动",
    "多件优惠",
    "组合套餐",
    "买赠活动"
]

PROMOTION_SCENES = [
    "日常促销",
    "周末促销",
    "节日营销",
    "季节性营销",
    "品类主题活动"
]

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


# ============================================================
# 4. 生成促销活动主表
# ============================================================

def generate_promotions():

    records = []

    start_date = pd.Timestamp("2026-10-01")
    end_date = pd.Timestamp("2027-09-30")

    for i in range(1, ACTIVITY_COUNT + 1):

        promotion_type = rng.choice(PROMOTION_TYPES)
        promotion_scene = rng.choice(PROMOTION_SCENES)

        duration_days = int(
            rng.integers(3, 16)
        )

        promotion_start = start_date + pd.Timedelta(
            days=int(
                rng.integers(
                    0,
                    (end_date - start_date).days - 20
                )
            )
        )

        promotion_end = promotion_start + pd.Timedelta(
            days=duration_days - 1
        )

        records.append({
            "promotion_id": f"PROMO{i:04d}",
            "promotion_name": f"{promotion_scene}-{promotion_type}-{i:03d}",
            "promotion_type": promotion_type,
            "promotion_scene": promotion_scene,
            "start_date": promotion_start.strftime("%Y-%m-%d"),
            "end_date": promotion_end.strftime("%Y-%m-%d"),
            "duration_days": duration_days,
            "promotion_status": "模拟待执行",
            "data_type": "simulated"
        })

    return pd.DataFrame(records)


# ============================================================
# 5. 生成促销活动商品明细
# ============================================================

def generate_promotion_details(products, promotions):

    records = []

    detail_counter = 1

    for _, promotion in promotions.iterrows():

        # 每场活动选择5-20个商品
        product_count = int(
            rng.integers(5, 21)
        )

        selected_indices = rng.choice(
            products.index.to_numpy(),
            size=min(product_count, len(products)),
            replace=False
        )

        selected_products = products.loc[selected_indices]

        for _, product in selected_products.iterrows():

            category_name = str(product["category_name"])

            own_price = float(product["selling_price"])
            purchase_cost = float(product["purchase_cost"])

            discount_min, discount_max = CATEGORY_DISCOUNT_RULES.get(
                category_name,
                DEFAULT_DISCOUNT_RULE
            )

            discount_rate = round(
                float(rng.uniform(discount_min, discount_max)),
                3
            )

            promotion_price = round(
                own_price * discount_rate,
                2
            )

            # 促销前后单件毛利
            original_unit_profit = round(
                own_price - purchase_cost,
                2
            )

            promotion_unit_profit = round(
                promotion_price - purchase_cost,
                2
            )

            original_margin = round(
                original_unit_profit / own_price,
                4
            )

            promotion_margin = round(
                promotion_unit_profit / promotion_price,
                4
            ) if promotion_price > 0 else 0

            # 模拟促销目标销量，不代表实际销量
            target_quantity = int(
                rng.integers(20, 501)
            )

            # 模拟促销带来的目标销量提升幅度
            expected_lift = round(
                float(rng.uniform(0.05, 0.50)),
                3
            )

            # 简单模拟活动预算
            estimated_budget = round(
                float(
                    rng.uniform(500, 10000)
                ),
                2
            )

            # 促销单件毛利是否为负
            if promotion_unit_profit < 0:
                profit_warning = "促销价格低于采购成本"
            elif promotion_margin < 0.10:
                profit_warning = "促销后毛利率低于10%"
            else:
                profit_warning = "毛利空间正常"

            records.append({
                "promotion_detail_id": f"PDET{detail_counter:06d}",
                "promotion_id": promotion["promotion_id"],
                "sku_id": product["sku_id"],
                "product_name": product["product_name"],
                "category_name": category_name,
                "original_price": round(own_price, 2),
                "purchase_cost": round(purchase_cost, 2),
                "discount_rate": discount_rate,
                "promotion_price": promotion_price,
                "original_unit_profit": original_unit_profit,
                "promotion_unit_profit": promotion_unit_profit,
                "original_gross_margin": original_margin,
                "promotion_gross_margin": promotion_margin,
                "target_quantity": target_quantity,
                "expected_sales_lift": expected_lift,
                "estimated_budget": estimated_budget,
                "profit_warning": profit_warning,
                "data_type": "simulated"
            })

            detail_counter += 1

    return pd.DataFrame(records)


# ============================================================
# 6. 数据质量检查
# ============================================================

def check_promotions(
    products,
    promotions,
    promotion_details
):

    assert len(promotions) == ACTIVITY_COUNT, \
        "促销活动数量不符合设定。"

    assert promotions["promotion_id"].is_unique, \
        "促销活动ID存在重复。"

    assert promotions["start_date"].notna().all(), \
        "促销开始日期存在缺失。"

    assert promotions["end_date"].notna().all(), \
        "促销结束日期存在缺失。"

    assert (
        pd.to_datetime(promotions["end_date"])
        >= pd.to_datetime(promotions["start_date"])
    ).all(), "促销结束日期早于开始日期。"

    assert promotion_details["promotion_detail_id"].is_unique, \
        "促销明细ID存在重复。"

    assert promotion_details["promotion_id"].isin(
        promotions["promotion_id"]
    ).all(), "存在无对应主表的促销明细。"

    assert promotion_details["sku_id"].isin(
        products["sku_id"]
    ).all(), "存在无对应商品档案的SKU。"

    assert promotion_details["discount_rate"].between(
        0, 1
    ).all(), "折扣率超出合理范围。"

    assert (
        promotion_details["promotion_price"] > 0
    ).all(), "促销价格必须大于0。"

    assert (
        promotion_details["target_quantity"] > 0
    ).all(), "目标销量必须大于0。"

    assert promotion_details["data_type"].eq(
        "simulated"
    ).all(), "促销明细数据类型异常。"

    print("\n数据质量检查：全部通过")


# ============================================================
# 7. 主程序
# ============================================================

def main():

    print("=" * 60)
    print("开始生成促销活动模拟数据")
    print("=" * 60)

    products = load_products()

    print(f"读取商品数量：{len(products)}")

    promotions = generate_promotions()

    promotion_details = generate_promotion_details(
        products,
        promotions
    )

    check_promotions(
        products,
        promotions,
        promotion_details
    )

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    promotions.to_csv(
        OUTPUT_FILE,
        index=False,
        encoding="utf-8-sig"
    )

    promotion_details.to_csv(
        DETAIL_OUTPUT_FILE,
        index=False,
        encoding="utf-8-sig"
    )

    print("\n促销活动数据生成完成！")

    print(f"促销活动数量：{len(promotions)}")
    print(f"促销商品明细数量：{len(promotion_details)}")
    print(
        f"平均每场活动商品数："
        f"{promotion_details.groupby('promotion_id').size().mean():.2f}"
    )

    print("\n促销类型分布：")
    print(promotions["promotion_type"].value_counts())

    print("\n促销商品品类分布：")
    print(promotion_details["category_name"].value_counts())

    print("\n促销毛利预警分布：")
    print(promotion_details["profit_warning"].value_counts())

    print("\n促销明细预览：")
    print(
        promotion_details[
            [
                "product_name",
                "original_price",
                "discount_rate",
                "promotion_price",
                "promotion_gross_margin",
                "profit_warning"
            ]
        ].head(10).to_string(index=False)
    )

    print(f"\n活动主表：{OUTPUT_FILE}")
    print(f"活动明细：{DETAIL_OUTPUT_FILE}")

    print("\n注意：")
    print("1. 所有促销活动和目标数据均为模拟数据。")
    print("2. 目标销量和销量提升幅度不代表实际活动效果。")
    print("3. 毛利未扣除平台佣金、物流、营销费用等其他成本。")

    print("=" * 60)


if __name__ == "__main__":
    main()

