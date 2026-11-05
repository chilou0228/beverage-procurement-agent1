
from pathlib import Path
import random
import pandas as pd

random.seed(2027)

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 读取采购订单及明细
orders = pd.read_csv(
    PROJECT_ROOT / "data" / "processed" / "purchase_orders.csv"
)

details = pd.read_csv(
    PROJECT_ROOT / "data" / "processed" / "purchase_order_details.csv"
)

orders["order_date"] = pd.to_datetime(orders["order_date"])
orders["expected_arrival_date"] = pd.to_datetime(
    orders["expected_arrival_date"]
)

# 模拟数据截止日期
simulation_end_date = pd.Timestamp("2026-10-23")

receipts = []

for _, order in orders.iterrows():

    order_id = order["order_id"]

    # 当前订单的商品明细
    order_details = details[
        details["order_id"] == order_id
    ]

    # 根据订单状态模拟到货比例
    status = order["order_status"]

    for _, item in order_details.iterrows():

        ordered_quantity = int(item["purchase_quantity"])

        if status == "已完成":
            received_ratio = 1.0

        elif status == "部分到货":
            received_ratio = random.uniform(0.3, 0.8)

        else:
            # 运输中订单可能尚未到货，也可能部分到货
            received_ratio = random.choice([
                0,
                0,
                0.2,
                0.5
            ])

        received_quantity = int(
            round(ordered_quantity * received_ratio)
        )

        if received_quantity <= 0:
            continue

        # 模拟分批到货
        if received_quantity >= 2 and random.random() < 0.3:

            first_quantity = random.randint(
                1,
                received_quantity - 1
            )

            quantities = [
                first_quantity,
                received_quantity - first_quantity
            ]

        else:
            quantities = [received_quantity]

        for batch_index, quantity in enumerate(
            quantities,
            start=1
        ):

            # 模拟实际到货日期
            delay_days = random.randint(-2, 7)

            receipt_date = (
                order["expected_arrival_date"] +
                pd.Timedelta(days=delay_days)
            )

            # 实际到货日期不能早于采购订单日期
            if receipt_date < order["order_date"]:
                receipt_date = order["order_date"]

            # 如果到货日期超过模拟数据截止日期，
            # 则本次到货尚未发生，不生成到货记录
            if receipt_date > simulation_end_date:
                continue

            receipt_id = (
                f"RC-{order_id}-"
                f"{item['sku_id']}-"
                f"{batch_index:02d}"
            )

            receipts.append({
                "receipt_id": receipt_id,
                "order_id": order_id,
                "supplier_id": order["supplier_id"],
                "supplier_name": order["supplier_name"],
                "sku_id": item["sku_id"],
                "product_name": item["product_name"],
                "category_name": item["category_name"],
                "ordered_quantity": ordered_quantity,
                "received_quantity": quantity,
                "receipt_date": receipt_date.strftime("%Y-%m-%d"),
                "expected_arrival_date": (
                    order["expected_arrival_date"].strftime("%Y-%m-%d")
                )
            })

# 转换为 DataFrame
receipts_df = pd.DataFrame(receipts)

# 保存到货记录
output_path = (
    PROJECT_ROOT /
    "data" /
    "processed" /
    "purchase_receipts.csv"
)

receipts_df.to_csv(
    output_path,
    index=False,
    encoding="utf-8-sig"
)

print("=" * 55)
print("采购到货记录生成完成")
print("=" * 55)

print(f"到货记录数量：{len(receipts_df)}")
print(f"涉及采购订单：{receipts_df['order_id'].nunique()}")
print(f"涉及供应商：{receipts_df['supplier_id'].nunique()}")
print(f"实际到货商品数量：{receipts_df['received_quantity'].sum():,}")

print("\n各供应商到货记录 TOP10：")
print(
    receipts_df.groupby("supplier_name")["received_quantity"]
    .sum()
    .sort_values(ascending=False)
    .head(10)
)

print("\n到货记录预览：")
print(
    receipts_df.head(10).to_string(index=False)
)

print(f"\n文件保存位置：{output_path}")
