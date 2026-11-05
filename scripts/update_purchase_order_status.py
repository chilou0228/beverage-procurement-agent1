
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 读取采购订单主表、采购订单明细、实际到货记录
orders = pd.read_csv(
    PROJECT_ROOT / "data" / "processed" / "purchase_orders.csv"
)

details = pd.read_csv(
    PROJECT_ROOT / "data" / "processed" / "purchase_order_details.csv"
)

receipts = pd.read_csv(
    PROJECT_ROOT / "data" / "processed" / "purchase_receipts.csv"
)

print("=" * 55)
print("采购订单状态自动更新")
print("=" * 55)

# 1. 汇总每张订单的采购总量
ordered_summary = (
    details.groupby("order_id")
    .agg(
        ordered_quantity=("purchase_quantity", "sum")
    )
    .reset_index()
)

# 2. 汇总每张订单的实际累计到货量
received_summary = (
    receipts.groupby("order_id")
    .agg(
        received_quantity=("received_quantity", "sum")
    )
    .reset_index()
)

# 3. 将采购数量和实际到货数量合并到订单主表
orders = orders.drop(
    columns=[
        "ordered_quantity",
        "received_quantity",
        "pending_quantity"
    ],
    errors="ignore"
)

orders = orders.merge(
    ordered_summary,
    on="order_id",
    how="left"
)

orders = orders.merge(
    received_summary,
    on="order_id",
    how="left"
)

# 没有到货记录的订单，到货数量记为0
orders["received_quantity"] = (
    orders["received_quantity"]
    .fillna(0)
    .astype(int)
)

orders["ordered_quantity"] = (
    orders["ordered_quantity"]
    .fillna(0)
    .astype(int)
)

# 4. 计算尚未到货数量
orders["pending_quantity"] = (
    orders["ordered_quantity"] -
    orders["received_quantity"]
)

# 5. 根据累计到货情况更新订单状态
def determine_order_status(row):

    if row["received_quantity"] == 0:
        return "运输中"

    elif row["received_quantity"] < row["ordered_quantity"]:
        return "部分到货"

    else:
        return "已完成"


orders["order_status"] = orders.apply(
    determine_order_status,
    axis=1
)

# 6. 保存更新后的采购订单主表
output_path = (
    PROJECT_ROOT /
    "data" /
    "processed" /
    "purchase_orders.csv"
)

orders.to_csv(
    output_path,
    index=False,
    encoding="utf-8-sig"
)

# 7. 输出状态统计
print("\n订单状态更新完成！")

print("\n订单状态分布：")
print(
    orders["order_status"]
    .value_counts()
)

print("\n采购数量汇总：")
print(f"采购总量：{orders['ordered_quantity'].sum():,}")
print(f"累计到货：{orders['received_quantity'].sum():,}")
print(f"待到货量：{orders['pending_quantity'].sum():,}")

print("\n订单状态示例：")
print(
    orders[
        [
            "order_id",
            "supplier_name",
            "ordered_quantity",
            "received_quantity",
            "pending_quantity",
            "order_status"
        ]
    ].head(10).to_string(index=False)
)

print(f"\n更新后的订单文件：{output_path}")

