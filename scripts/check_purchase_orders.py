
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent

orders = pd.read_csv(
    PROJECT_ROOT / "data" / "processed" / "purchase_orders.csv"
)

details = pd.read_csv(
    PROJECT_ROOT / "data" / "processed" / "purchase_order_details.csv"
)

suppliers = pd.read_csv(
    PROJECT_ROOT / "data" / "processed" / "suppliers.csv"
)

print("=" * 55)
print("采购订单数据质量检查")
print("=" * 55)

# 1. 检查订单数量
assert len(orders) > 0, "采购订单为空"

# 2. 检查订单编号唯一性
assert orders["order_id"].is_unique, "存在重复订单编号"

# 3. 检查订单明细数量
assert len(details) > len(orders), "订单明细数量异常"

# 4. 检查明细必需字段
required_detail_columns = [
    "order_id",
    "supplier_id",
    "supplier_name",
    "sku_id",
    "product_name",
    "category_name",
    "brand",
    "purchase_quantity",
    "unit_purchase_cost",
    "subtotal"
]

assert set(required_detail_columns).issubset(details.columns)

assert not details[required_detail_columns].isnull().any().any(), (
    "订单明细存在缺失值"
)

# 5. 检查订单数量和金额
assert (orders["total_quantity"] > 0).all()
assert (orders["order_amount"] > 0).all()

assert (details["purchase_quantity"] > 0).all()
assert (details["unit_purchase_cost"] > 0).all()
assert (details["subtotal"] > 0).all()

# 6. 检查订单明细编号关联
assert details["order_id"].isin(orders["order_id"]).all(), (
    "存在无法关联的订单明细"
)

# 7. 检查供应商关联
assert orders["supplier_id"].isin(suppliers["supplier_id"]).all()
assert details["supplier_id"].isin(suppliers["supplier_id"]).all()

# 8. 检查明细金额计算
expected_subtotal = (
    details["purchase_quantity"] *
    details["unit_purchase_cost"]
)

subtotal_diff = (
    expected_subtotal - details["subtotal"]
).abs()

assert (subtotal_diff < 0.011).all(), (
    "订单明细金额计算错误"
)

# 9. 检查每张订单的商品数量汇总
detail_summary = (
    details.groupby("order_id")
    .agg(
        detail_quantity=("purchase_quantity", "sum"),
        detail_amount=("subtotal", "sum")
    )
)

order_check = orders.set_index("order_id").join(
    detail_summary,
    how="left"
)

assert order_check["detail_quantity"].notna().all()
assert (
    order_check["total_quantity"] ==
    order_check["detail_quantity"]
).all(), "订单商品数量与明细汇总不一致"

# 10. 检查每张订单的金额汇总
amount_diff = (
    order_check["order_amount"] -
    order_check["detail_amount"]
).abs()

assert (amount_diff < 0.02).all(), (
    "订单金额与明细汇总不一致"
)

# 11. 检查订单状态
valid_status = ["已完成", "部分到货", "运输中"]

assert orders["order_status"].isin(valid_status).all(), (
    "存在无效订单状态"
)

print("[通过] 采购订单数量检查")
print("[通过] 订单编号唯一性检查")
print("[通过] 订单明细数量检查")
print("[通过] 订单明细字段完整性检查")
print("[通过] 采购数量及金额有效性检查")
print("[通过] 订单明细关联检查")
print("[通过] 供应商关联检查")
print("[通过] 订单明细金额计算检查")
print("[通过] 订单商品数量汇总检查")
print("[通过] 订单金额汇总检查")
print("[通过] 订单状态检查")

print("\n采购订单数据质量检查全部通过！")
print(f"订单数量：{len(orders)}")
print(f"订单明细数量：{len(details)}")
print(f"涉及供应商：{orders['supplier_id'].nunique()}")
print(f"采购 SKU 数量：{details['sku_id'].nunique()}")
print(f"采购总量：{orders['total_quantity'].sum():,}")
print(f"采购总金额：¥{orders['order_amount'].sum():,.2f}")
