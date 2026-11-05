
from pathlib import Path
import random
import pandas as pd

random.seed(2026)

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 读取基础数据
products = pd.read_csv(
    PROJECT_ROOT / "data" / "processed" / "products.csv"
)

suppliers = pd.read_csv(
    PROJECT_ROOT / "data" / "processed" / "suppliers.csv"
)

mapping = pd.read_csv(
    PROJECT_ROOT / "data" / "processed" / "product_supplier_mapping.csv"
)

inventory = pd.read_csv(
    PROJECT_ROOT / "data" / "processed" / "inventory_snapshot.csv"
)

# 合并商品与库存
product_inventory = products.merge(
    inventory[
        ["sku_id", "available_stock", "avg_daily_sales_30d"]
    ],
    on="sku_id",
    how="left"
)

# 只使用主供应商
primary_mapping = mapping[
    mapping["is_primary"] == True
].copy()

# 从商品档案中获取唯一的商品基础信息
product_info = products[
    ["sku_id", "brand", "product_name", "category_name"]
].copy()

# 合并商品信息与库存信息
product_info = product_info.merge(
    inventory[
        ["sku_id", "available_stock", "avg_daily_sales_30d"]
    ],
    on="sku_id",
    how="left"
)

# 再与主供应商报价表关联
primary_mapping = primary_mapping.merge(
    product_info[
        ["sku_id", "brand", "available_stock", "avg_daily_sales_30d"]
    ],
    on="sku_id",
    how="left"
)
# 采购订单模拟日期范围
start_date = pd.Timestamp("2026-07-26")
end_date = pd.Timestamp("2026-10-23")

order_date_range = pd.date_range(
    start=start_date,
    end=end_date,
    freq="D"
)

# 分别保存订单主表和订单明细
orders = []
order_details = []

# 按供应商生成订单
for supplier_id in suppliers["supplier_id"]:

    supplier_products = primary_mapping[
        primary_mapping["supplier_id"] == supplier_id
    ]

    if supplier_products.empty:
        continue

    # 每家供应商模拟 2 至 5 张订单
    order_count = random.randint(2, 5)

    supplier_info = suppliers[
        suppliers["supplier_id"] == supplier_id
    ].iloc[0]

    for order_index in range(1, order_count + 1):

        # 订单日期
        order_date = pd.Timestamp(
            random.choice(order_date_range)
        )

        # 随机选择 2 至 6 个商品
        sample_count = min(
            random.randint(2, 6),
            len(supplier_products)
        )

        selected_products = supplier_products.sample(
            n=sample_count,
            random_state=random.randint(1, 100000)
        )

        order_id = (
            f"PO-{supplier_id}-{order_index:03d}"
        )

        total_quantity = 0
        order_amount = 0

        # 生成当前订单的商品明细
        for _, product in selected_products.iterrows():

            daily_sales = float(
                product["avg_daily_sales_30d"]
            )

            # 根据近期日均销量模拟采购数量
            quantity = max(
                1,
                int(round(
                    daily_sales * random.uniform(7, 30)
                ))
            )

            # 使用主供应商模拟报价
            unit_cost = float(
                product["supplier_quote_cost"]
            )

            subtotal = round(
                quantity * unit_cost, 2
            )

            total_quantity += quantity
            order_amount += subtotal

            order_details.append({
                "order_id": order_id,
                "supplier_id": supplier_id,
                "supplier_name": supplier_info["supplier_name"],
                "sku_id": product["sku_id"],
                "product_name": product["product_name"],
                "category_name": product["category_name"],
                "brand": product["brand"],
                "purchase_quantity": quantity,
                "unit_purchase_cost": round(unit_cost, 2),
                "subtotal": subtotal
            })

        # 预计到货日期
        lead_time = int(
            supplier_info["avg_lead_time_days"]
        )

        expected_arrival_date = (
            order_date + pd.Timedelta(days=lead_time)
        )

        # 模拟订单状态
        if expected_arrival_date > end_date:
            order_status = "运输中"
        else:
            order_status = random.choices(
                ["已完成", "部分到货", "运输中"],
                weights=[0.65, 0.20, 0.15],
                k=1
            )[0]

        # 订单主表
        orders.append({
            "order_id": order_id,
            "supplier_id": supplier_id,
            "supplier_name": supplier_info["supplier_name"],
            "order_date": order_date.strftime("%Y-%m-%d"),
            "expected_arrival_date": (
                expected_arrival_date.strftime("%Y-%m-%d")
            ),
            "lead_time_days": lead_time,
            "total_quantity": total_quantity,
            "order_amount": round(order_amount, 2),
            "order_status": order_status
        })

# 转换为 DataFrame
orders_df = pd.DataFrame(orders)
details_df = pd.DataFrame(order_details)

# 保存订单主表
orders_path = (
    PROJECT_ROOT /
    "data" /
    "processed" /
    "purchase_orders.csv"
)

orders_df.to_csv(
    orders_path,
    index=False,
    encoding="utf-8-sig"
)

# 保存订单明细表
details_path = (
    PROJECT_ROOT /
    "data" /
    "processed" /
    "purchase_order_details.csv"
)

details_df.to_csv(
    details_path,
    index=False,
    encoding="utf-8-sig"
)

# 输出结果
print("=" * 55)
print("采购订单及明细数据生成完成")
print("=" * 55)

print(f"采购订单数量：{len(orders_df)}")
print(f"采购订单明细数量：{len(details_df)}")
print(f"涉及供应商：{orders_df['supplier_id'].nunique()}")
print(f"采购商品种类：{details_df['sku_id'].nunique()}")
print(f"采购商品总量：{orders_df['total_quantity'].sum():,}")
print(f"采购订单总金额：¥{orders_df['order_amount'].sum():,.2f}")

print("\n订单状态分布：")
print(orders_df["order_status"].value_counts())

print("\n订单明细预览：")
print(
    details_df.head(10).to_string(index=False)
)

print(f"\n订单主表：{orders_path}")
print(f"订单明细表：{details_path}")

