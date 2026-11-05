
from pathlib import Path
import pandas as pd
import yaml

# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 文件路径
product_path = PROJECT_ROOT / "data" / "processed" / "products.csv"
category_path = PROJECT_ROOT / "config" / "category_config.yaml"
rules_path = PROJECT_ROOT / "config" / "category_rules.yaml"

# 读取数据
df = pd.read_csv(product_path)

with open(category_path, "r", encoding="utf-8") as f:
    category_config = yaml.safe_load(f)

with open(rules_path, "r", encoding="utf-8") as f:
    rules_config = yaml.safe_load(f)

categories = category_config["categories"]
business_rules = rules_config["business_rules"]

print("=" * 50)
print("商品档案数据质量检查")
print("=" * 50)

# 1. 检查商品数量
assert len(df) == 300, "商品总数不等于300"

# 2. 检查 SKU 编号是否重复
assert df["sku_id"].is_unique, "发现重复 SKU 编号"

# 3. 检查必需字段是否缺失
required_columns = [
    "sku_id", "product_name", "category_id",
    "category_name", "subcategory", "brand",
    "specification", "selling_price",
    "purchase_cost", "gross_margin",
    "lead_time_days", "status"
]

assert set(required_columns).issubset(df.columns), (
    "商品档案缺少必要字段"
)

assert not df[required_columns].isnull().any().any(), (
    "商品档案存在缺失值"
)

# 4. 检查价格和采购成本
assert (df["selling_price"] > 0).all(), "发现非正售价"
assert (df["purchase_cost"] > 0).all(), "发现非正采购成本"
assert (df["purchase_cost"] < df["selling_price"]).all(), (
    "发现采购成本不低于售价的商品"
)

# 5. 检查毛利率计算
calculated_margin = (
    df["selling_price"] - df["purchase_cost"]
) / df["selling_price"]

margin_diff = (
    calculated_margin - df["gross_margin"]
).abs()

assert (margin_diff < 0.00011).all(), "毛利率计算不一致"

# 6. 检查品类 ID 和品类名称
for category in categories:
    category_id = category["category_id"]
    category_name = category["category_name"]

    category_df = df[df["category_id"] == category_id]

    assert len(category_df) == category["sku_count"], (
        f"{category_name} 的 SKU 数量不正确"
    )

    assert (category_df["category_name"] == category_name).all(), (
        f"{category_name} 的品类名称不一致"
    )

    # 检查售价、成本比例和交期是否符合配置
    rule = business_rules[category_id]

    min_price, max_price = rule["price_range_yuan"]
    min_cost, max_cost = rule["purchase_cost_ratio"]
    min_days, max_days = rule["lead_time_days"]

    assert df.loc[
        df["category_id"] == category_id, "selling_price"
    ].between(min_price, max_price).all(), (
        f"{category_name} 存在超出价格区间的商品"
    )

    category_cost_ratio = (
        category_df["purchase_cost"] /
        category_df["selling_price"]
    )

    assert category_cost_ratio.between(
        min_cost, max_cost
    ).all(), f"{category_name} 的采购成本比例异常"

    assert category_df["lead_time_days"].between(
        min_days, max_days
    ).all(), f"{category_name} 的供货周期异常"

# 7. 检查品牌和品类数量
assert df["brand"].nunique() == 30, "品牌数量不等于30"
assert df["category_id"].nunique() == 10, "品类数量不等于10"

print("[通过] 商品总数检查")
print("[通过] SKU 唯一性检查")
print("[通过] 必需字段完整性检查")
print("[通过] 售价与采购成本检查")
print("[通过] 毛利率计算检查")
print("[通过] 品类 SKU 数量检查")
print("[通过] 价格、成本比例和交期检查")
print("[通过] 品牌与品类数量检查")

print("\n商品档案质量检查全部通过！")
print(f"商品数量：{len(df)}")
print(f"品牌数量：{df['brand'].nunique()}")
print(f"品类数量：{df['category_id'].nunique()}")
print(f"缺失值数量：{df.isnull().sum().sum()}")
print(f"重复 SKU 数量：{df['sku_id'].duplicated().sum()}")

