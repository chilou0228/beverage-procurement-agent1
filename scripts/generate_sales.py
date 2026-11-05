
from pathlib import Path
import random
import numpy as np
import pandas as pd

# 固定随机种子，保证结果可复现
random.seed(42)
np.random.seed(42)

# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 读取商品档案
product_path = PROJECT_ROOT / "data" / "processed" / "products.csv"
products = pd.read_csv(product_path)

# 模拟日期：连续365天
end_date = pd.Timestamp("2026-10-23")
start_date = end_date - pd.Timedelta(days=364)

dates = pd.date_range(
    start=start_date,
    end=end_date,
    freq="D"
)

# 各品类日均销量基准
category_demand = {
    "白酒": 2.8,
    "葡萄酒": 1.8,
    "洋酒": 1.5,
    "啤酒": 8.0,
    "黄酒": 2.0,
    "养生酒/保健酒": 1.2,
    "清酒/烧酒": 2.0,
    "果酒/米酒": 2.5,
    "鸡尾酒/预调酒": 4.0,
    "其他酒类": 1.0
}

# 品类季节性参数
def get_season_factor(category, date):
    month = date.month

    # 啤酒夏季需求更高
    if category == "啤酒":
        return 1.7 if month in [6, 7, 8] else 0.8 if month in [12, 1, 2] else 1.0

    # 白酒、黄酒在传统节日前后需求提高
    if category in ["白酒", "黄酒", "养生酒/保健酒"]:
        return 1.5 if month in [1, 2, 9, 10] else 1.0

    # 葡萄酒、洋酒在年末和节日期间需求提高
    if category in ["葡萄酒", "洋酒"]:
        return 1.3 if month in [2, 12] else 1.0

    # 果酒和预调酒在夏季需求较高
    if category in ["果酒/米酒", "鸡尾酒/预调酒"]:
        return 1.3 if month in [5, 6, 7, 8] else 1.0

    return 1.0


records = []

for _, product in products.iterrows():

    sku_id = product["sku_id"]
    category = product["category_name"]
    brand = product["brand"]

    base_price = float(product["selling_price"])
    purchase_cost = float(product["purchase_cost"])

    # 为每个 SKU 设置基础需求强度
    sku_demand_factor = random.uniform(0.5, 1.8)

    # 为每个 SKU 设置基础流量水平
    base_visitors = random.randint(30, 300)

    for date in dates:

        # 星期因素：周末需求略高
        weekday_factor = 1.2 if date.weekday() >= 5 else 1.0

        # 季节因素
        season_factor = get_season_factor(category, date)

        # 随机波动
        random_factor = np.random.lognormal(
            mean=0,
            sigma=0.25
        )

        # 计算当天期望销量
        expected_sales = (
            category_demand[category]
            * sku_demand_factor
            * weekday_factor
            * season_factor
            * random_factor
        )

        sales_volume = max(
            0,
            int(round(expected_sales))
        )

        # 访客数与销量存在一定关系
        visitors = max(
            sales_volume,
            int(
                base_visitors
                * weekday_factor
                * np.random.uniform(0.7, 1.3)
            )
        )

        # 模拟转化率
        conversion_rate = random.uniform(0.015, 0.06)

        # 订单数不超过销量
        orders = min(
            sales_volume,
            int(round(visitors * conversion_rate))
        )

        # 模拟销售价格波动
        actual_price = round(
            base_price * random.uniform(0.97, 1.03),
            2
        )

        # 计算销售额
        revenue = round(
            sales_volume * actual_price,
            2
        )

        # 计算销售毛利
        gross_profit = round(
            sales_volume * (actual_price - purchase_cost),
            2
        )

        records.append({
            "date": date.strftime("%Y-%m-%d"),
            "sku_id": sku_id,
            "category_name": category,
            "brand": brand,
            "sales_volume": sales_volume,
            "visitors": visitors,
            "orders": orders,
            "selling_price": actual_price,
            "purchase_cost": purchase_cost,
            "revenue": revenue,
            "gross_profit": gross_profit
        })


# 转换为 DataFrame
sales_df = pd.DataFrame(records)

# 保存数据
output_path = (
    PROJECT_ROOT / "data" / "processed" / "sales_daily.csv"
)

sales_df.to_csv(
    output_path,
    index=False,
    encoding="utf-8-sig"
)

# 输出统计结果
print("=" * 55)
print("365天每日销售数据生成完成")
print("=" * 55)

print(f"销售记录数：{len(sales_df):,}")
print(f"覆盖 SKU 数：{sales_df['sku_id'].nunique()}")
print(f"覆盖日期数：{sales_df['date'].nunique()}")
print(f"开始日期：{sales_df['date'].min()}")
print(f"结束日期：{sales_df['date'].max()}")

print("\n整体经营指标：")
print(f"累计销售额：¥{sales_df['revenue'].sum():,.2f}")
print(f"累计销售毛利：¥{sales_df['gross_profit'].sum():,.2f}")
print(f"累计销量：{sales_df['sales_volume'].sum():,}")
print(f"累计访客：{sales_df['visitors'].sum():,}")

print("\n各品类销售额：")
print(
    sales_df.groupby("category_name")["revenue"]
    .sum()
    .sort_values(ascending=False)
    .round(2)
)

print(f"\n文件保存位置：{output_path}")

