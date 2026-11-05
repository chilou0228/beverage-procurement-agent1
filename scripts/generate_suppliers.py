
from pathlib import Path
import random
import pandas as pd

random.seed(42)

# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 读取商品档案
product_path = PROJECT_ROOT / "data" / "processed" / "products.csv"
products = pd.read_csv(product_path)

# 供应商名称库：均为模拟名称
supplier_names = [
    "华北酒类供应链有限公司",
    "华东酒业贸易有限公司",
    "华南食品酒水有限公司",
    "西南酒类供应有限公司",
    "东北酒水商贸有限公司",
    "中原酒业供应链有限公司",
    "华中酒类贸易有限公司",
    "西北酒水供应有限公司",
    "沿海酒类贸易有限公司",
    "全国酒业供应链有限公司",
    "金谷酒类供应有限公司",
    "丰泽酒水贸易有限公司",
    "盛达酒业供应链有限公司",
    "瑞丰食品贸易有限公司",
    "百川酒类商贸有限公司",
    "长风酒水供应有限公司",
    "锦华酒业贸易有限公司",
    "天成酒类供应链有限公司",
    "云岭酒水贸易有限公司",
    "嘉禾酒业供应有限公司",
    "星海酒类商贸有限公司",
    "青禾酒水供应链有限公司",
    "远山酒业贸易有限公司",
    "清源酒类供应有限公司",
    "江南酒水商贸有限公司",
    "北辰酒业供应链有限公司",
    "悦酿酒类贸易有限公司",
    "蓝海酒水供应有限公司",
    "九州酒业商贸有限公司",
    "千山酒类供应链有限公司",
    "山河酒水贸易有限公司",
    "锦川酒业供应有限公司",
    "东方酒类商贸有限公司",
    "金麦酒水供应链有限公司",
    "丰年酒业贸易有限公司",
    "禾木酒类供应有限公司",
    "醇香酒水商贸有限公司",
    "云台酒业供应链有限公司",
    "瑞祥酒类贸易有限公司",
    "盛源酒水供应有限公司"
]

regions = [
    "华北", "华东", "华南", "华中",
    "西南", "西北", "东北", "华东"
]

supplier_records = []

# 获取商品品类
category_names = sorted(products["category_name"].unique())

for index, supplier_name in enumerate(supplier_names, start=1):

    supplier_id = f"SUP{index:03d}"

    # 模拟供应商经营区域
    region = regions[(index - 1) % len(regions)]

    # 模拟供应商主营品类
    main_category = category_names[(index - 1) % len(category_names)]

    # 模拟供应商等级
    supplier_level = random.choices(
        ["战略供应商", "核心供应商", "普通供应商"],
        weights=[0.15, 0.35, 0.50],
        k=1
    )[0]

    # 模拟供货能力
    supply_capacity = random.randint(500, 10000)

    # 模拟平均交付周期
    lead_time = random.randint(2, 30)

    # 模拟历史准时交付率
    on_time_rate = round(random.uniform(0.85, 0.99), 4)

    # 模拟历史订单履约率
    fulfillment_rate = round(random.uniform(0.88, 0.995), 4)

    # 模拟账期
    payment_terms = random.choice([0, 15, 30, 45, 60])

    # 模拟合作状态
    status = random.choices(
        ["合作中", "观察中", "暂停合作"],
        weights=[0.80, 0.15, 0.05],
        k=1
    )[0]

    supplier_records.append({
        "supplier_id": supplier_id,
        "supplier_name": supplier_name,
        "region": region,
        "main_category": main_category,
        "supplier_level": supplier_level,
        "supply_capacity_units": supply_capacity,
        "avg_lead_time_days": lead_time,
        "on_time_delivery_rate": on_time_rate,
        "order_fulfillment_rate": fulfillment_rate,
        "payment_terms_days": payment_terms,
        "status": status
    })

# 生成 DataFrame
supplier_df = pd.DataFrame(supplier_records)

# 保存供应商档案
output_path = PROJECT_ROOT / "data" / "processed" / "suppliers.csv"

supplier_df.to_csv(
    output_path,
    index=False,
    encoding="utf-8-sig"
)

print("=" * 50)
print("供应商档案生成完成")
print("=" * 50)

print(f"供应商总数：{len(supplier_df)}")
print(f"供应商等级数量：{supplier_df['supplier_level'].nunique()}")
print(f"覆盖经营区域：{supplier_df['region'].nunique()}")

print("\n供应商等级分布：")
print(supplier_df["supplier_level"].value_counts())

print("\n供应商档案预览：")
print(
    supplier_df[
        ["supplier_id", "supplier_name", "main_category",
         "supplier_level", "avg_lead_time_days", "status"]
    ].head(10).to_string(index=False)
)

print(f"\n文件保存位置：{output_path}")
