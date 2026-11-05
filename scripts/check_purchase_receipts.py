
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 读取数据
receipts = pd.read_csv(
    PROJECT_ROOT / "data" / "processed" / "purchase_receipts.csv"
)

orders = pd.read_csv(
    PROJECT_ROOT / "data" / "processed" / "purchase_orders.csv"
)

details = pd.read_csv(
    PROJECT_ROOT / "data" / "processed" / "purchase_order_details.csv"
)

# 转换日期格式
receipts["receipt_date"] = pd.to_datetime(
    receipts["receipt_date"]
)

receipts["expected_arrival_date"] = pd.to_datetime(
    receipts["expected_arrival_date"]
)

orders["order_date"] = pd.to_datetime(orders["order_date"])

# 数据截止日期
simulation_end_date = pd.Timestamp("2026-10-23")

print("=" * 55)
print("采购到货数据质量检查")
print("=" * 55)

# 1. 检查到货记录数量
assert len(receipts) > 0, "到货记录为空"

# 2. 检查到货记录编号唯一性
assert receipts["receipt_id"].is_unique, (
    "存在重复到货记录编号"
)

# 3. 检查必需字段完整性
required_columns = [
    "receipt_id",
    "order_id",
    "supplier_id",
    "supplier_name",
    "sku_id",
    "product_name",
    "category_name",
    "ordered_quantity",
    "received_quantity",
    "receipt_date",
    "expected_arrival_date"
]

assert set(required_columns).issubset(receipts.columns)

assert not receipts[required_columns].isnull().any().any(), (
    "到货记录存在缺失值"
)

# 4. 检查到货数量有效性
assert (receipts["ordered_quantity"] > 0).all()
assert (receipts["received_quantity"] > 0).all()

# 5. 检查订单关联
assert receipts["order_id"].isin(orders["order_id"]).all(), (
    "存在无法关联的采购订单"
)

# 6. 检查供应商和商品关联
order_info = orders[
    ["order_id", "supplier_id", "supplier_name", "order_date"]
].copy()

receipt_check = receipts.merge(
    order_info,
    on="order_id",
    how="left",
    suffixes=("", "_order"),
    validate="many_to_one"
)

assert (
    receipt_check["supplier_id"] ==
    receipt_check["supplier_id_order"]
).all(), "到货记录供应商与订单不一致"

assert (
    receipt_check["supplier_name"] ==
    receipt_check["supplier_name_order"]
).all(), "到货记录供应商名称与订单不一致"

# 7. 检查商品是否属于对应订单
detail_keys = details[
    ["order_id", "sku_id"]
].drop_duplicates()

receipt_keys = receipts[
    ["order_id", "sku_id"]
].drop_duplicates()

key_check = receipt_keys.merge(
    detail_keys,
    on=["order_id", "sku_id"],
    how="left",
    indicator=True
)

assert (key_check["_merge"] == "both").all(), (
    "存在不属于对应采购订单的商品到货记录"
)

# 8. 检查到货日期
assert (
    receipts["receipt_date"] >=
    receipt_check["order_date"]
).all(), "到货日期早于采购订单日期"

assert (
    receipts["receipt_date"] <= simulation_end_date
).all(), "到货日期超过模拟数据截止日期"

# 9. 检查单个订单商品的累计到货数量
receipt_summary = (
    receipts.groupby(["order_id", "sku_id"])
    .agg(
        total_received=("received_quantity", "sum"),
        ordered_quantity=("ordered_quantity", "first"),
        receipt_count=("receipt_id", "count")
    )
    .reset_index()
)

# 同一订单同一商品的采购数量必须一致
quantity_consistency = (
    receipts.groupby(["order_id", "sku_id"])["ordered_quantity"]
    .nunique()
)

assert (quantity_consistency == 1).all(), (
    "同一订单商品的采购数量不一致"
)

assert (
    receipt_summary["total_received"] <=
    receipt_summary["ordered_quantity"]
).all(), "累计到货数量超过采购数量"

# 10. 检查到货日期与预计到货日期字段
assert (
    receipts["expected_arrival_date"].notna()
).all(), "预计到货日期存在缺失"

# 11. 检查采购明细中的商品信息
product_check = receipts.merge(
    details[
        ["order_id", "sku_id", "product_name", "category_name"]
    ].drop_duplicates(),
    on=["order_id", "sku_id"],
    how="left",
    suffixes=("", "_detail"),
    validate="many_to_one"
)

assert (
    product_check["product_name"] ==
    product_check["product_name_detail"]
).all(), "商品名称与采购订单明细不一致"

assert (
    product_check["category_name"] ==
    product_check["category_name_detail"]
).all(), "商品品类与采购订单明细不一致"

# 输出检查结果
print("[通过] 到货记录数量检查")
print("[通过] 到货记录编号唯一性检查")
print("[通过] 到货记录字段完整性检查")
print("[通过] 到货数量有效性检查")
print("[通过] 采购订单关联检查")
print("[通过] 供应商信息一致性检查")
print("[通过] 采购商品关联检查")
print("[通过] 到货日期合理性检查")
print("[通过] 累计到货数量检查")
print("[通过] 预计到货日期检查")
print("[通过] 商品名称及品类一致性检查")

print("\n采购到货数据质量检查全部通过！")

print(f"到货记录数量：{len(receipts):,}")
print(f"涉及采购订单：{receipts['order_id'].nunique()}")
print(f"涉及供应商：{receipts['supplier_id'].nunique()}")
print(f"涉及采购 SKU：{receipts['sku_id'].nunique()}")
print(f"累计到货数量：{receipts['received_quantity'].sum():,}")
print(f"分批到货商品组合：{len(receipt_summary):,}")
print(
    f"发生分批到货的商品组合："
    f"{(receipt_summary['receipt_count'] > 1).sum():,}"
)

