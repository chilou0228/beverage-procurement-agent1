
from pathlib import Path
import yaml

# 获取项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 读取品类配置
category_config_path = PROJECT_ROOT / "config" / "category_config.yaml"

# 读取业务规则配置
rules_config_path = PROJECT_ROOT / "config" / "category_rules.yaml"

with open(category_config_path, "r", encoding="utf-8") as f:
    category_config = yaml.safe_load(f)

with open(rules_config_path, "r", encoding="utf-8") as f:
    rules_config = yaml.safe_load(f)

categories = category_config["categories"]
business_rules = rules_config["business_rules"]

print("=" * 50)
print("酒水采销 Agent 业务规则检查")
print("=" * 50)

# 1. 检查品类数量和 SKU 总数
total_skus = sum(item["sku_count"] for item in categories)

assert len(categories) == 10, "品类数量不正确"
assert total_skus == 300, "SKU 总数不正确"

# 2. 检查两份配置中的品类 ID 是否一致
category_ids = {item["category_id"] for item in categories}
rule_ids = set(business_rules.keys())

assert category_ids == rule_ids, (
    f"品类 ID 不匹配：缺少规则 {category_ids - rule_ids}，"
    f"多余规则 {rule_ids - category_ids}"
)

# 3. 检查每个品类的业务参数
for category in categories:
    category_id = category["category_id"]
    category_name = category["category_name"]
    rule = business_rules[category_id]

    # 检查品类名称
    assert rule["category_name"] == category_name, (
        f"{category_name} 的名称配置不一致"
    )

    # 检查价格区间
    min_price, max_price = rule["price_range_yuan"]
    assert 0 < min_price < max_price, (
        f"{category_name} 的价格区间不合理"
    )

    # 检查采购成本比例
    min_cost, max_cost = rule["purchase_cost_ratio"]
    assert 0 < min_cost <= max_cost < 1, (
        f"{category_name} 的采购成本比例不合理"
    )

    # 检查供货交期
    min_days, max_days = rule["lead_time_days"]
    assert 0 < min_days <= max_days, (
        f"{category_name} 的供货交期不合理"
    )

    # 检查商品属性
    assert len(rule["attributes"]) > 0, (
        f"{category_name} 缺少商品属性"
    )

    # 检查季节性销售节点
    assert len(rule["seasonal_peak"]) > 0, (
        f"{category_name} 缺少季节性销售节点"
    )

    print(
        f"[通过] {category_name}："
        f"价格区间 ¥{min_price}-¥{max_price}，"
        f"采购成本比例 {min_cost:.0%}-{max_cost:.0%}，"
        f"交期 {min_days}-{max_days} 天"
    )

print("\n" + "=" * 50)
print("全部业务规则检查通过！")
print(f"品类数量：{len(categories)}")
print(f"SKU 总数：{total_skus}")
print("两份配置文件的品类 ID 完全匹配")
print("=" * 50)

