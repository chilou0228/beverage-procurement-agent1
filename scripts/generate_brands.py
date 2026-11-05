
from pathlib import Path
import pandas as pd

# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 读取商品档案
product_path = PROJECT_ROOT / "data" / "processed" / "products.csv"
df = pd.read_csv(product_path)

# 品牌基础信息
brand_descriptions = [
    "面向大众消费市场的综合酒类品牌",
    "主打品质与日常饮用场景的酒类品牌",
    "注重产品差异化与消费体验的酒类品牌",
    "覆盖礼赠与商务消费场景的酒类品牌",
    "面向年轻消费群体的特色酒类品牌"
]

brand_records = []

# 按品牌汇总商品信息
brand_groups = df.groupby("brand")

for index, (brand_name, group) in enumerate(brand_groups, start=1):

    brand_id = f"BR{index:03d}"

    # 品牌所属品类
    category_names = sorted(
        group["category_name"].unique().tolist()
    )

    # 商品数量
    sku_count = len(group)

    # 商品平均售价
    avg_price = round(group["selling_price"].mean(), 2)

    # 商品平均采购成本
    avg_cost = round(group["purchase_cost"].mean(), 2)

    # 平均毛利率
    avg_margin = round(group["gross_margin"].mean(), 4)

    # 模拟品牌定位标签
    positioning = [
        "大众消费",
        "品质升级",
        "中高端",
        "礼赠商务",
        "年轻潮流"
    ][(index - 1) % 5]

    # 模拟品牌简介
    description = brand_descriptions[(index - 1) % 5]

    brand_records.append({
        "brand_id": brand_id,
        "brand_name": brand_name,
        "brand_positioning": positioning,
        "brand_description": description,
        "category_coverage": "、".join(category_names),
        "sku_count": sku_count,
        "avg_selling_price": avg_price,
        "avg_purchase_cost": avg_cost,
        "avg_gross_margin": avg_margin,
        "status": "合作中"
    })

# 转换为 DataFrame
brand_df = pd.DataFrame(brand_records)

# 保存品牌档案
output_path = PROJECT_ROOT / "data" / "processed" / "brands.csv"

brand_df.to_csv(
    output_path,
    index=False,
    encoding="utf-8-sig"
)

print("=" * 50)
print("品牌档案生成完成")
print("=" * 50)

print(f"品牌总数：{len(brand_df)}")
print(f"覆盖品类数：{df['category_id'].nunique()}")
print(f"关联商品数：{brand_df['sku_count'].sum()}")

print("\n品牌档案预览：")
print(
    brand_df[
        ["brand_id", "brand_name", "brand_positioning", "sku_count"]
    ].head(10).to_string(index=False)
)

print(f"\n文件保存位置：{output_path}")
