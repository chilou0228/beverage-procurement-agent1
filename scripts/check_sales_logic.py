
from pathlib import Path
import sqlite3
import pandas as pd


# ==================================================
# 1. 数据库路径及检查参数
# ==================================================

ROOT_DIR = Path(__file__).resolve().parents[1]
DB_PATH = ROOT_DIR / "data" / "database" / "beverage_agent.db"

TOLERANCE = 0.02

results = []


# ==================================================
# 2. 通用检查函数
# ==================================================

def record_result(name, error_count, description=""):

    passed = error_count == 0

    results.append({
        "检查项目": name,
        "异常数量": error_count,
        "检查结果": "PASS" if passed else "FAIL"
    })

    status = "PASS" if passed else "FAIL"

    print(
        f"{status}：{name}，"
        f"异常数量：{error_count}"
    )

    if description:
        print(f"说明：{description}")


# ==================================================
# 3. 主检查程序
# ==================================================

def main():

    print("=" * 65)
    print("酒水采销 Agent｜销售数据业务逻辑检查")
    print("=" * 65)

    if not DB_PATH.exists():
        print(f"错误：数据库不存在：{DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)

    try:

        # 读取销售数据
        sales = pd.read_sql_query(
            "SELECT * FROM sales_daily",
            conn
        )

        # 读取商品档案
        products = pd.read_sql_query(
            "SELECT * FROM products",
            conn
        )

        print(f"\n销售记录数量：{len(sales):,}")
        print(f"商品数量：{len(products):,}")

        # ==================================================
        # 检查1：基础数值是否合理
        # ==================================================

        print("\n【检查1：销售基础数值检查】")
        print("-" * 65)

        numeric_columns = [
            "sales_volume",
            "visitors",
            "orders",
            "selling_price",
            "purchase_cost",
            "revenue",
            "gross_profit"
        ]

        for column in numeric_columns:

            null_count = sales[column].isna().sum()

            record_result(
                f"{column} 空值检查",
                int(null_count)
            )

        negative_columns = [
            "sales_volume",
            "visitors",
            "orders",
            "selling_price",
            "purchase_cost",
            "revenue"
        ]

        for column in negative_columns:

            error_count = int((sales[column] < 0).sum())

            record_result(
                f"{column} 非负检查",
                error_count
            )

        # ==================================================
        # 检查2：销售额计算是否正确
        # ==================================================

        print("\n【检查2：销售额计算检查】")
        print("-" * 65)

        expected_revenue = (
            sales["sales_volume"] * sales["selling_price"]
        )

        revenue_errors = int(
            (
                sales["revenue"] - expected_revenue
            ).abs().gt(TOLERANCE).sum()
        )

        record_result(
            "销售额 = 销量 × 实际销售售价",
            revenue_errors
        )

        # ==================================================
        # 检查3：销售毛利计算是否正确
        # ==================================================

        print("\n【检查3：销售毛利计算检查】")
        print("-" * 65)

        expected_profit = (
            sales["sales_volume"]
            * (
                sales["selling_price"]
                - sales["purchase_cost"]
            )
        )

        profit_errors = int(
            (
                sales["gross_profit"] - expected_profit
            ).abs().gt(TOLERANCE).sum()
        )

        record_result(
            "销售毛利 = 销量 ×（售价－采购成本）",
            profit_errors
        )

        # ==================================================
        # 检查4：销售价格与商品档案是否合理
        # ==================================================

        print("\n【检查4：商品价格与成本一致性检查】")
        print("-" * 65)

        price_comparison = sales.merge(
            products[
                ["sku_id", "selling_price", "purchase_cost"]
            ],
            on="sku_id",
            how="left",
            suffixes=("_sales", "_product"),
            indicator=True
        )

        missing_products = int(
            (price_comparison["_merge"] == "left_only").sum()
        )

        record_result(
            "销售记录对应商品档案",
            missing_products
        )

        matched = price_comparison[
            price_comparison["_merge"] == "both"
        ].copy()

        # 实际销售售价应处于基础售价的97%～103%之间
        lower_price = (
            matched["selling_price_product"] * 0.97
        )

        upper_price = (
            matched["selling_price_product"] * 1.03
        )

        price_errors = int(
            (
                (
                    matched["selling_price_sales"]
                    < lower_price - TOLERANCE
                )
                |
                (
                    matched["selling_price_sales"]
                    > upper_price + TOLERANCE
                )
            ).sum()
        )

        record_result(
            "销售实际售价处于商品基础售价的97%～103%区间",
            price_errors
        )

        # 检查销售采购成本是否与商品档案一致
        cost_errors = int(
            (
                (
                    matched["purchase_cost_sales"]
                    - matched["purchase_cost_product"]
                ).abs()
            ).gt(TOLERANCE).sum()
        )

        record_result(
            "销售采购成本与商品档案成本一致",
            cost_errors
        )

        # ==================================================
        # 检查5：销售日期完整性
        # ==================================================

        print("\n【检查5：销售日期完整性检查】")
        print("-" * 65)

        sales["date"] = pd.to_datetime(
            sales["date"],
            errors="coerce"
        )

        invalid_dates = int(
            sales["date"].isna().sum()
        )

        record_result(
            "销售日期格式检查",
            invalid_dates
        )

        valid_dates = sales["date"].dropna()

        if len(valid_dates) > 0:

            date_range = pd.date_range(
                start=valid_dates.min(),
                end=valid_dates.max(),
                freq="D"
            )

            actual_dates = pd.DatetimeIndex(
                valid_dates.unique()
            )

            missing_days = len(
                date_range.difference(actual_dates)
            )

            print(
                f"销售日期范围："
                f"{valid_dates.min().date()} 至 "
                f"{valid_dates.max().date()}"
            )

            record_result(
                "销售日期连续性检查",
                missing_days
            )

            record_result(
                "销售日期覆盖365天检查",
                0 if len(date_range) == 365 else 1,
                f"实际覆盖 {len(date_range)} 天"
            )

        # ==================================================
        # 检查6：商品与日期组合是否重复
        # ==================================================

        print("\n【检查6：销售记录重复检查】")
        print("-" * 65)

        duplicate_count = int(
            sales.duplicated(
                subset=["date", "sku_id"]
            ).sum()
        )

        record_result(
            "同一商品同一天重复记录检查",
            duplicate_count
        )

        # ==================================================
        # 检查7：销售数据与商品档案覆盖情况
        # ==================================================

        print("\n【检查7：商品销售覆盖检查】")
        print("-" * 65)

        sales_skus = set(
            sales["sku_id"].dropna()
        )

        product_skus = set(
            products["sku_id"].dropna()
        )

        unsold_skus = product_skus - sales_skus
        unknown_skus = sales_skus - product_skus

        record_result(
            "商品档案中的SKU销售覆盖检查",
            len(unsold_skus),
            f"没有销售记录的SKU数量：{len(unsold_skus)}"
        )

        record_result(
            "销售数据中不存在于商品档案的SKU检查",
            len(unknown_skus)
        )

        # ==================================================
        # 8. 输出检查汇总
        # ==================================================

        print("\n" + "=" * 65)
        print("销售数据业务逻辑检查汇总")
        print("=" * 65)

        result_df = pd.DataFrame(results)

        total = len(result_df)

        passed = int(
            (result_df["检查结果"] == "PASS").sum()
        )

        failed = total - passed

        print(f"检查项目数量：{total}")
        print(f"通过项目数量：{passed}")
        print(f"异常项目数量：{failed}")

        if failed == 0:
            print("\nPASS：所有销售数据业务逻辑检查均通过！")
        else:
            print("\nWARNING：发现异常，请根据上方结果排查。")

    finally:
        conn.close()


if __name__ == "__main__":
    main()

