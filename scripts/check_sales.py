
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent

sales_path = PROJECT_ROOT / "data" / "processed" / "sales_daily.csv"
products_path = PROJECT_ROOT / "data" / "processed" / "products.csv"

sales = pd.read_csv(sales_path)
products = pd.read_csv(products_path)

print("=" * 55)
print("每日销售数据质量检查")
print("=" * 55)

# 1. 检查数据规模
assert len(sales) == 109500, "销售记录数量不正确"
assert sales["sku_id"].nunique() == 300, "SKU 数量不正确"
assert sales["date"].nunique() == 365, "日期数量不正确"

# 2. 检查日期范围
sales["date"] = pd.to_datetime(sales["date"])

assert sales["date"].min() == pd.Timestamp("2025-10-24")
assert sales["date"].max() == pd.Timestamp("2026-10-23")

# 3. 检查必需字段
required_columns = [
    "date", "sku_id", "category_name", "brand",
    "sales_volume", "visitors", "orders",
    "selling_price", "purchase_cost",
    "revenue", "gross_profit"
]

assert set(required_columns).issubset(sales.columns), (
    "销售数据缺少必要字段"
)

assert not sales[required_columns].isnull().any().any(), (
    "销售数据存在缺失值"
)

# 4. 检查 SKU 和日期组合是否唯一
assert not sales.duplicated(
    subset=["date", "sku_id"]
).any(), "存在重复的 SKU 日期记录"

# 5. 检查每个 SKU 是否都有365天数据
days_per_sku = sales.groupby("sku_id")["date"].nunique()

assert (days_per_sku == 365).all(), (
    "存在销售日期不完整的 SKU"
)

# 6. 检查销售数量逻辑
assert (sales["sales_volume"] >= 0).all()
assert (sales["visitors"] >= sales["sales_volume"]).all()
assert (sales["orders"] >= 0).all()
assert (sales["orders"] <= sales["sales_volume"]).all()

# 7. 检查价格和成本
assert (sales["selling_price"] > 0).all()
assert (sales["purchase_cost"] > 0).all()

# 8. 检查销售额计算
expected_revenue = (
    sales["sales_volume"] * sales["selling_price"]
)

revenue_diff = (
    expected_revenue - sales["revenue"]
).abs()

assert (revenue_diff < 0.011).all(), (
    "销售额计算存在错误"
)

# 9. 检查毛利计算
expected_profit = (
    sales["sales_volume"] *
    (sales["selling_price"] - sales["purchase_cost"])
)

profit_diff = (
    expected_profit - sales["gross_profit"]
).abs()

assert (profit_diff < 0.011).all(), (
    "销售毛利计算存在错误"
)

# 10. 检查销售数据中的 SKU 是否都存在于商品档案
assert sales["sku_id"].isin(products["sku_id"]).all(), (
    "发现商品档案中不存在的 SKU"
)

# 11. 检查品类和品牌信息是否与商品档案一致
product_info = products[
    ["sku_id", "category_name", "brand"]
]

check_df = sales.merge(
    product_info,
    on="sku_id",
    how="left",
    suffixes=("_sales", "_product")
)

assert (
    check_df["category_name_sales"] ==
    check_df["category_name_product"]
).all(), "销售数据品类与商品档案不一致"

assert (
    check_df["brand_sales"] ==
    check_df["brand_product"]
).all(), "销售数据品牌与商品档案不一致"

print("[通过] 销售记录数量检查")
print("[通过] SKU 和日期覆盖检查")
print("[通过] 必需字段完整性检查")
print("[通过] SKU 日期唯一性检查")
print("[通过] 每个 SKU 的365天完整性检查")
print("[通过] 销量、访客、订单逻辑检查")
print("[通过] 售价与采购成本检查")
print("[通过] 销售额计算检查")
print("[通过] 销售毛利计算检查")
print("[通过] 商品档案关联检查")

print("\n销售数据质量检查全部通过！")
print(f"销售记录：{len(sales):,}")
print(f"SKU 数量：{sales['sku_id'].nunique()}")
print(f"日期数量：{sales['date'].nunique()}")
print(f"缺失值：{sales[required_columns].isnull().sum().sum()}")
print(f"重复记录：{sales.duplicated(['date', 'sku_id']).sum()}")
