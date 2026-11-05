
from pathlib import Path
import pandas as pd

# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 读取数据
products = pd.read_csv(
    PROJECT_ROOT / "data" / "processed" / "products.csv"
)

suppliers = pd.read_csv(
    PROJECT_ROOT / "data" / "processed" / "suppliers.csv"
)

mapping = pd.read_csv(
    PROJECT_ROOT / "data" / "processed" /
    "product_supplier_mapping.csv"
)

print("=" * 50)
print("商品—供应商关联关系质量检查")
print("=" * 50)

# 1. 检查关联记录数量
assert len(mapping) == 600, "关联记录数量不正确"

# 2. 检查商品和供应商是否存在
assert mapping["sku_id"].isin(products["sku_id"]).all(), (
    "关联表存在无效 SKU"
)

assert mapping["supplier_id"].isin(suppliers["supplier_id"]).all(), (
    "关联表存在无效供应商"
)

# 3. 检查每个商品是否恰好关联2家供应商
supplier_counts = mapping.groupby("sku_id")["supplier_id"].nunique()

assert (supplier_counts == 2).all(), (
    "存在关联供应商数量不等于2的商品"
)

# 4. 检查每个商品是否恰好有1家主供应商
primary_counts = mapping.groupby("sku_id")["is_primary"].sum()

assert (primary_counts == 1).all(), (
    "存在主供应商数量不等于1的商品"
)

# 5. 检查是否存在重复的商品—供应商组合
assert not mapping.duplicated(
    subset=["sku_id", "supplier_id"]
).any(), "存在重复的商品—供应商关联"

# 6. 检查供应商主营品类是否匹配商品品类
check_df = mapping.merge(
    suppliers[["supplier_id", "main_category"]],
    on="supplier_id",
    how="left"
)

assert (
    check_df["category_name"] == check_df["main_category"]
).all(), "发现供应商主营品类与商品品类不匹配"

# 7. 检查供应商报价
assert (mapping["supplier_quote_cost"] > 0).all(), (
    "存在非正供应商报价"
)

# 8. 检查主供应商和备选供应商数量
assert (mapping["is_primary"] == 1).sum() == 300
assert (mapping["is_primary"] == 0).sum() == 300

print("[通过] 关联记录数量检查")
print("[通过] SKU 和供应商编号有效性检查")
print("[通过] 每个商品关联2家供应商")
print("[通过] 每个商品恰好有1家主供应商")
print("[通过] 商品—供应商组合唯一性检查")
print("[通过] 供应商主营品类匹配检查")
print("[通过] 供应商报价有效性检查")
print("[通过] 主供应商与备选供应商数量检查")

print("\n关联关系质量检查全部通过！")
print(f"商品数量：{products['sku_id'].nunique()}")
print(f"供应商数量：{suppliers['supplier_id'].nunique()}")
print(f"关联记录：{len(mapping)}")

