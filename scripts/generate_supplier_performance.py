
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 读取数据
suppliers = pd.read_csv(
    PROJECT_ROOT / "data" / "processed" / "suppliers.csv"
)

orders = pd.read_csv(
    PROJECT_ROOT / "data" / "processed" / "purchase_orders.csv"
)

receipts = pd.read_csv(
    PROJECT_ROOT / "data" / "processed" / "purchase_receipts.csv"
)

orders["expected_arrival_date"] = pd.to_datetime(
    orders["expected_arrival_date"]
)

receipts["receipt_date"] = pd.to_datetime(
    receipts["receipt_date"]
)

receipts["expected_arrival_date"] = pd.to_datetime(
    receipts["expected_arrival_date"]
)

print("=" * 55)
print("供应商绩效数据生成")
print("=" * 55)

# 1. 汇总供应商采购订单数据
order_summary = (
    orders.groupby("supplier_id")
    .agg(
        order_count=("order_id", "nunique"),
        purchase_amount=("order_amount", "sum"),
        ordered_quantity=("ordered_quantity", "sum"),
        received_quantity=("received_quantity", "sum"),
        completed_orders=(
            "order_status",
            lambda x: (x == "已完成").sum()
        ),
        partial_orders=(
            "order_status",
            lambda x: (x == "部分到货").sum()
        ),
        pending_orders=(
            "order_status",
            lambda x: (x == "运输中").sum()
        )
    )
    .reset_index()
)

# 2. 计算订单履约率
order_summary["fulfillment_rate"] = (
    order_summary["received_quantity"] /
    order_summary["ordered_quantity"]
).fillna(0)

# 3. 计算订单完成率
order_summary["order_completion_rate"] = (
    order_summary["completed_orders"] /
    order_summary["order_count"]
).fillna(0)

# 4. 计算到货及时性
# 以到货数量加权，统计预计到货日期当天或之前到货的数量
receipts["delay_days"] = (
    receipts["receipt_date"] -
    receipts["expected_arrival_date"]
).dt.days

receipts["on_time_quantity"] = receipts.apply(
    lambda row: (
        row["received_quantity"]
        if row["delay_days"] <= 0
        else 0
    ),
    axis=1
)

# 只统计晚于预计日期的延迟天数
receipts["late_days"] = receipts["delay_days"].clip(lower=0)

receipt_summary = (
    receipts.groupby("supplier_id")
    .apply(
        lambda group: pd.Series({
            "on_time_quantity": group["on_time_quantity"].sum(),
            "late_quantity": group.loc[
                group["late_days"] > 0,
                "received_quantity"
            ].sum(),
            "weighted_late_days": (
                (
                    group["late_days"] *
                    group["received_quantity"]
                ).sum() /
                group["received_quantity"].sum()
                if group["received_quantity"].sum() > 0
                else 0
            )
        }),
        include_groups=False
    )
    .reset_index()
)

# 5. 合并供应商档案、采购订单和到货表现
performance = suppliers.merge(
    order_summary,
    on="supplier_id",
    how="left"
)

performance = performance.merge(
    receipt_summary,
    on="supplier_id",
    how="left"
)

# 6. 对没有采购订单或到货记录的供应商填充0
numeric_columns = [
    "order_count",
    "purchase_amount",
    "ordered_quantity",
    "received_quantity",
    "completed_orders",
    "partial_orders",
    "pending_orders",
    "fulfillment_rate",
    "order_completion_rate",
    "on_time_quantity",
    "late_quantity",
    "weighted_late_days"
]

performance[numeric_columns] = (
    performance[numeric_columns].fillna(0)
)

# 7. 计算到货及时率
performance["on_time_delivery_rate"] = (
    performance["on_time_quantity"] /
    performance["received_quantity"]
).where(
    performance["received_quantity"] > 0,
    0
)

# 8. 整理字段名称和顺序
performance = performance.rename(
    columns={
        "supplier_level": "original_supplier_level",
        "weighted_late_days": "avg_weighted_late_days"
    }
)

output_columns = [
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

performance = performance[output_columns]

# 9. 保存供应商绩效数据
output_path = (
    PROJECT_ROOT /
    "data" /
    "processed" /
    "supplier_performance.csv"
)

performance.to_csv(
    output_path,
    index=False,
    encoding="utf-8-sig"
)

# 10. 输出结果
print(f"供应商总数：{len(performance)}")
print(
    f"有采购订单的供应商："
    f"{(performance['order_count'] > 0).sum()}"
)

print("\n供应商绩效 TOP10（按采购金额）：")

top10 = performance.sort_values(
    "purchase_amount",
    ascending=False
).head(10)

print(
    top10[
        [
            "supplier_name",
            "order_count",
            "purchase_amount",
            "fulfillment_rate",
            "on_time_delivery_rate",
            "avg_weighted_late_days"
        ]
    ].to_string(index=False)
)

print("\n整体采购履约情况：")

total_ordered = performance["ordered_quantity"].sum()
total_received = performance["received_quantity"].sum()

print(f"采购总量：{total_ordered:,.0f}")
print(f"累计到货：{total_received:,.0f}")
print(
    f"整体履约率："
    f"{total_received / total_ordered:.2%}"
    if total_ordered > 0
    else "整体履约率：0%"
)

print(f"\n文件保存位置：{output_path}")

