
from pathlib import Path
import random
import pandas as pd

random.seed(42)

# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 读取商品和供应商档案
products = pd.read_csv(
    PROJECT_ROOT / "data" / "processed" / "products.csv"
)

suppliers = pd.read_csv(
    PROJECT_ROOT / "data" / "processed" / "suppliers.csv"
)

relationships = []

# 按主营品类整理供应商
supplier_groups = {
    category: group
    for category, group in suppliers.groupby("main_category")
}

# 为每个商品匹配供应商
for _, product in products.iterrows():

    category_name = product["category_name"]

    # 找到主营品类匹配的供应商
    candidates = supplier_groups.get(category_name)

    if candidates is None or len(candidates) < 2:
        raise ValueError(
            f"{category_name} 可匹配的供应商不足2家"
        )

    # 随机选择2家供应商
    selected = candidates.sample(
        n=2,
        random_state=random.randint(1, 100000)
    )

    for index, (_, supplier) in enumerate(selected.iterrows()):

        # 供应商报价：围绕商品基础采购成本上下浮动
        quote_cost = round(
            product["purchase_cost"] *
            random.uniform(0.97, 1.03),
            2
        )

        relationships.append({
            "sku_id": product["sku_id"],
            "product_name": product["product_name"],
            "category_id": product["category_id"],
            "category_name": category_name,
            "supplier_id": supplier["supplier_id"],
            "supplier_name": supplier["supplier_name"],
            "supplier_level": supplier["supplier_level"],
            "is_primary": 1 if index == 0 else 0,
            "base_purchase_cost": product["purchase_cost"],
            "supplier_quote_cost": quote_cost,
            "avg_lead_time_days": supplier["avg_lead_time_days"],
            "supplier_status": supplier["status"]
        })

# 生成关联表
relationship_df = pd.DataFrame(relationships)

# 保存
output_path = (
    PROJECT_ROOT /
    "data" /
    "processed" /
    "product_supplier_mapping.csv"
)

relationship_df.to_csv(
    output_path,
    index=False,
    encoding="utf-8-sig"
)

print("=" * 50)
print("商品—供应商关联表生成完成")
print("=" * 50)

print(f"关联记录总数：{len(relationship_df)}")
print(f"关联商品数量：{relationship_df['sku_id'].nunique()}")
print(f"关联供应商数量：{relationship_df['supplier_id'].nunique()}")

print("\n主供应商与备选供应商数量：")
print(
    relationship_df["is_primary"]
    .value_counts()
    .rename(index={1: "主供应商", 0: "备选供应商"})
)

print("\n商品供应商关联预览：")
print(
    relationship_df[
        ["sku_id", "product_name", "supplier_id",
         "supplier_name", "is_primary", "supplier_quote_cost"]
    ].head(10).to_string(index=False)
)

print(f"\n文件保存位置：{output_path}")

