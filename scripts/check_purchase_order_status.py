
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent

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
print("采购订单状态数据质量检查")
print("=" * 55)

# 1. 检查订单数量
assert len(orders) > 0
assert orders["order_id"].is_unique

# 2. 检查新增字段
required_columns = [
    "ordered_quantity",
    "received_quantity",
    "pending_quantity",
    "order_status"
]

assert set(required_columns).issubset(orders.columns)

# 3. 根据采购明细重新计算采购总量
expected_ordered = (
    details.groupby("order_id")["purchase_quantity"]
    .sum()
)

actual_ordered = orders.set_index("order_id")[
    "ordered_quantity"
]

assert actual_ordered.equals(
    expected_ordered.reindex(actual_ordered.index).astype(int)
), "订单采购总量与采购明细不一致"

# 4. 根据到货记录重新计算累计到货量
expected_received = (
    receipts.groupby("order_id")["received_quantity"]
    .sum()
)

expected_received = (
    expected_received
    .reindex(orders["order_id"], fill_value=0)
    .astype(int)
    .to_numpy()
)

assert (
    orders["received_quantity"].to_numpy() ==
    expected_received
).all(), "订单累计到货量与到货记录不一致"

# 5. 检查待到货数量
expected_pending = (
    orders["ordered_quantity"] -
    orders["received_quantity"]
)

assert (
    orders["pending_quantity"] == expected_pending
).all(), "待到货数量计算错误"

# 6. 检查数量合理性
assert (orders["ordered_quantity"] > 0).all()
assert (orders["received_quantity"] >= 0).all()
assert (orders["pending_quantity"] >= 0).all()

# 7. 检查订单状态
expected_status = []

for _, row in orders.iterrows():

    if row["received_quantity"] == 0:
        expected_status.append("运输中")

    elif row["received_quantity"] < row["ordered_quantity"]:
        expected_status.append("部分到货")

    else:
        expected_status.append("已完成")

assert (
    orders["order_status"].to_numpy() ==
    pd.Series(expected_status).to_numpy()
).all(), "订单状态与实际到货情况不一致"

# 8. 检查订单总量汇总
assert (
    orders["ordered_quantity"].sum() ==
    details["purchase_quantity"].sum()
)

assert (
    orders["received_quantity"].sum() ==
    receipts["received_quantity"].sum()
)

assert (
    orders["pending_quantity"].sum() ==
    orders["ordered_quantity"].sum() -
    orders["received_quantity"].sum()
)

print("[通过] 采购订单数量检查")
print("[通过] 订单状态字段检查")
print("[通过] 采购总量与明细一致性检查")
print("[通过] 累计到货量与到货记录一致性检查")
print("[通过] 待到货数量计算检查")
print("[通过] 采购及到货数量合理性检查")
print("[通过] 订单状态逻辑检查")
print("[通过] 采购总量汇总检查")

print("\n采购订单状态数据质量检查全部通过！")

print(f"订单总数：{len(orders)}")
print(f"采购总量：{orders['ordered_quantity'].sum():,}")
print(f"累计到货：{orders['received_quantity'].sum():,}")
print(f"待到货量：{orders['pending_quantity'].sum():,}")

print("\n订单状态分布：")
print(orders["order_status"].value_counts())
