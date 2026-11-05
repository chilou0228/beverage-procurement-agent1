
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 读取数据
performance = pd.read_csv(
    PROJECT_ROOT / "data" / "processed" / "supplier_performance.csv"
)

suppliers = pd.read_csv(
    PROJECT_ROOT / "data" / "processed" / "suppliers.csv"
)

orders = pd.read_csv(
    PROJECT_ROOT / "data" / "processed" / "purchase_orders.csv"
)

receipts = pd.read_csv(
    PROJECT_ROOT / "data" / "processed" / "purchase_receipts.csv"
)

print("=" * 55)
print("供应商绩效数据质量检查")
print("=" * 55)

# 1. 检查供应商数量及唯一性
assert len(performance) == len(suppliers), (
    "供应商绩效记录数量与供应商档案不一致"
)

assert performance["supplier_id"].is_unique, (
    "存在重复供应商绩效记录"
)

# 2. 检查供应商关联
assert performance["supplier_id"].isin(
    suppliers["supplier_id"]
).all(), "存在无法关联的供应商"

# 3. 检查必需字段
required_columns = [
    "supplier_id",
    "supplier_name",
    "region",
    "main_category",
    "original_supplier_level",
    "order_count",
    "purchase_amount",
    "ordered_quantity",
    "received_quantity",
    "fulfillment_rate",
    "completed_orders",
    "partial_orders",
    "pending_orders",
    "order_completion_rate",
    "on_time_quantity",
    "late_quantity",
    "on_time_delivery_rate",
    "avg_weighted_late_days"
]

# 注意：当前生成脚本的输出字段中包含以上字段
assert set(required_columns).issubset(
    performance.columns
), "供应商绩效表缺少必需字段"

# 4. 检查数值字段完整性
numeric_columns = [
    "order_count",
    "purchase_amount",
    "ordered_quantity",
    "received_quantity",
    "fulfillment_rate",
    "completed_orders",
    "partial_orders",
    "pending_orders",
    "order_completion_rate",
    "on_time_quantity",
    "late_quantity",
    "on_time_delivery_rate",
    "avg_weighted_late_days"
]

assert not performance[numeric_columns].isnull().any().any(), (
    "绩效指标存在缺失值"
)

# 5. 检查采购金额和采购数量有效性
assert (performance["purchase_amount"] >= 0).all()
assert (performance["ordered_quantity"] >= 0).all()
assert (performance["received_quantity"] >= 0).all()

# 6. 检查履约率计算
expected_fulfillment = (
    performance["received_quantity"] /
    performance["ordered_quantity"]
).fillna(0)

assert (
    (performance["fulfillment_rate"] - expected_fulfillment).abs()
    < 0.000001
).all(), "供应商履约率计算错误"

# 7. 检查订单完成率计算
expected_completion = (
    performance["completed_orders"] /
    performance["order_count"]
).fillna(0)

assert (
    (performance["order_completion_rate"] - expected_completion).abs()
    < 0.000001
).all(), "供应商订单完成率计算错误"

# 8. 检查到货及时率计算
expected_on_time_rate = (
    performance["on_time_quantity"] /
    performance["received_quantity"]
).where(
    performance["received_quantity"] > 0,
    0
)

assert (
    (
        performance["on_time_delivery_rate"] -
        expected_on_time_rate
    ).abs() < 0.000001
).all(), "供应商到货及时率计算错误"

# 9. 检查各项比率范围
rate_columns = [
    "fulfillment_rate",
    "order_completion_rate",
    "on_time_delivery_rate"
]

for column in rate_columns:
    assert performance[column].between(0, 1).all(), (
        f"{column} 超出合理范围"
    )

# 10. 检查到货数量与订单数量关系
assert (
    performance["received_quantity"] <=
    performance["ordered_quantity"]
).all(), "供应商累计到货量超过采购量"

assert (
    performance["on_time_quantity"] +
    performance["late_quantity"] <=
    performance["received_quantity"]
).all(), "及时到货量与延迟到货量异常"

# 11. 检查订单状态数量汇总
assert (
    performance["completed_orders"] +
    performance["partial_orders"] +
    performance["pending_orders"] ==
    performance["order_count"]
).all(), "供应商订单状态数量汇总错误"

# 12. 检查绩效汇总与原始数据一致
assert performance["order_count"].sum() == len(orders)

assert abs(
    performance["purchase_amount"].sum() -
    orders["order_amount"].sum()
) < 0.02, "采购金额汇总与订单主表不一致"

assert (
    performance["ordered_quantity"].sum() ==
    orders["ordered_quantity"].sum()
)

assert (
    performance["received_quantity"].sum() ==
    receipts["received_quantity"].sum()
)

print("[通过] 供应商数量及唯一性检查")
print("[通过] 供应商档案关联检查")
print("[通过] 必需字段检查")
print("[通过] 数值字段完整性检查")
print("[通过] 采购金额及数量有效性检查")
print("[通过] 供应商履约率计算检查")
print("[通过] 订单完成率计算检查")
print("[通过] 到货及时率计算检查")
print("[通过] 绩效比率范围检查")
print("[通过] 到货数量合理性检查")
print("[通过] 订单状态汇总检查")
print("[通过] 原始采购数据汇总一致性检查")

print("\n供应商绩效数据质量检查全部通过！")

print(f"供应商数量：{len(performance)}")
print(f"采购订单数量：{performance['order_count'].sum()}")
print(f"采购总金额：¥{performance['purchase_amount'].sum():,.2f}")
print(f"采购总量：{performance['ordered_quantity'].sum():,}")
print(f"累计到货：{performance['received_quantity'].sum():,}")
