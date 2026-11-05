
from pathlib import Path
import random
import yaml
import pandas as pd

# 固定随机种子，确保每次生成结果一致
random.seed(42)

# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 读取配置
category_path = PROJECT_ROOT / "config" / "category_config.yaml"
rules_path = PROJECT_ROOT / "config" / "category_rules.yaml"

with open(category_path, "r", encoding="utf-8") as f:
    category_config = yaml.safe_load(f)

with open(rules_path, "r", encoding="utf-8") as f:
    rules_config = yaml.safe_load(f)

categories = category_config["categories"]
business_rules = rules_config["business_rules"]

# 品牌名称库：模拟品牌，仅用于项目数据演示
brand_pool = [
    "华夏酒坊", "云岭酿造", "北辰酒业", "金谷酒庄", "青禾酒业",
    "山河佳酿", "丰年酒业", "锦川酒庄", "天酿工坊", "星海酒业",
    "东方醇酿", "百川酒业", "长风酒庄", "云台酒业", "嘉禾酿造",
    "盛世佳酿", "清源酒业", "瑞丰酒庄", "九州酒坊", "醇香工坊",
    "远山酒业", "金麦酒坊", "蓝海酿造", "丰泽酒庄", "千山酒业",
    "悦酿工坊", "江南酒业", "禾木酒庄", "天成酒坊", "锦华酿造"
]

# 生成商品档案
products = []
sku_number = 1

for category in categories:
    category_id = category["category_id"]
    category_name = category["category_name"]
    sku_count = category["sku_count"]

    rule = business_rules[category_id]

    min_price, max_price = rule["price_range_yuan"]
    min_cost, max_cost = rule["purchase_cost_ratio"]

    for i in range(sku_count):

        # 商品编号
        sku_id = f"SKU{sku_number:04d}"

        # 品牌
        brand = brand_pool[(sku_number - 1) % len(brand_pool)]

        # 子品类
        subcategory = random.choice(category["subcategories"])

        # 商品售价
        price = round(
            random.uniform(min_price, max_price), 2
        )

        # 采购成本
        cost_ratio = random.uniform(min_cost, max_cost)
        purchase_cost = round(price * cost_ratio, 2)

        # 商品毛利率
        gross_margin = round(
            (price - purchase_cost) / price, 4
        )

        # 供货周期
        lead_time = random.randint(
            *rule["lead_time_days"]
        )

        # 规格容量：模拟商品规格
        volume_options = [
            "330ml", "500ml", "750ml", "1L",
            "1.5L", "2L", "礼盒装"
        ]
        volume = random.choice(volume_options)

        # 生成商品名称
        product_name = (
            f"{brand}{subcategory}{volume}装"
        )

        products.append({
            "sku_id": sku_id,
            "product_name": product_name,
            "category_id": category_id,
            "category_name": category_name,
            "subcategory": subcategory,
            "brand": brand,
            "specification": volume,
            "selling_price": price,
            "purchase_cost": purchase_cost,
            "gross_margin": gross_margin,
            "lead_time_days": lead_time,
            "status": "在售"
        })

        sku_number += 1

# 转换为 DataFrame
df = pd.DataFrame(products)

# 保存商品档案
output_path = (
    PROJECT_ROOT / "data" / "processed" / "products.csv"
)

df.to_csv(output_path, index=False, encoding="utf-8-sig")

# 输出生成结果
print("=" * 50)
print("商品档案生成完成")
print("=" * 50)

print(f"商品总数：{len(df)}")
print(f"品牌数量：{df['brand'].nunique()}")
print(f"一级品类数量：{df['category_name'].nunique()}")
print(f"平均售价：¥{df['selling_price'].mean():.2f}")
print(f"平均采购成本：¥{df['purchase_cost'].mean():.2f}")
print(f"平均毛利率：{df['gross_margin'].mean():.2%}")

print("\n各品类 SKU 数量：")
print(df.groupby("category_name")["sku_id"].count())

print(f"\n文件保存位置：{output_path}")
