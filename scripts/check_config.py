
from pathlib import Path
import yaml

# 获取项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 找到品类配置文件
config_path = PROJECT_ROOT / "config" / "category_config.yaml"

# 读取 YAML 文件
with open(config_path, "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

# 获取项目基本信息
project = config["project"]
categories = config["categories"]

# 计算 SKU 总数
total_skus = sum(
    category["sku_count"]
    for category in categories
)

print("=" * 45)
print("酒水采销 Agent 项目配置检查")
print("=" * 45)

print(f"项目名称：{project['name']}")
print(f"一级品类数量：{len(categories)}")
print(f"配置 SKU 总数：{total_skus}")
print(f"品牌数量：{project['total_brands']}")
print(f"供应商数量：{project['total_suppliers']}")

print("\n各品类 SKU 分配：")

for category in categories:
    print(
        f"{category['category_name']}："
        f"{category['sku_count']} 个 SKU"
    )

# 自动检查配置
assert len(categories) == 10, "一级品类数量不正确"
assert total_skus == project["total_skus"], "SKU 总数不正确"

category_ids = [
    category["category_id"]
    for category in categories
]

assert len(category_ids) == len(set(category_ids)), "品类ID重复"

print("\n配置检查通过！")

