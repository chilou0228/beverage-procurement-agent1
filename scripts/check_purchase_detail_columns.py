from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent

file_path = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "purchase_order_details.csv"
)

details = pd.read_csv(file_path)

print("=" * 50)
print("采购订单明细字段检查")
print("=" * 50)

print("\n当前文件的全部字段：")

for column in details.columns:
    print(f"- {column}")

print("\n前5行数据：")
print(details.head().to_string(index=False))

print("\n数据记录数量：", len(details))
