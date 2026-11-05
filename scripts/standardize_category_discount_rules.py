
import pandas as pd
import re
from pathlib import Path

# ============================================================
# 第55步：统一促销品类折扣规则
# 任务1：统计品类经营数据
# 任务2：生成品类折扣规则配置模板
# ============================================================

# 1. 路径配置
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

# 如果自动识别失败，可以在这里填写商品档案的实际路径
# 例如：PRODUCT_FILE = DATA_DIR / "商品档案.csv"
PRODUCT_FILE = None


# 2. 读取CSV，兼容常见中文编码
def read_csv_file(file_path):
    encodings = ["utf-8-sig", "utf-8", "gbk"]

    for encoding in encodings:
        try:
            return pd.read_csv(file_path, encoding=encoding)
        except UnicodeDecodeError:
            continue

    raise ValueError(f"无法识别文件编码：{file_path}")


# 3. 自动查找商品档案
def find_product_file():
    if PRODUCT_FILE is not None:
        if not PRODUCT_FILE.exists():
            raise FileNotFoundError(f"商品档案不存在：{PRODUCT_FILE}")
        return PRODUCT_FILE

    keywords = [
        "商品档案", "商品主档", "商品信息",
        "产品档案", "product_master", "products"
    ]

    excluded = [
        "销售", "促销", "库存", "竞品",
        "明细", "活动", "记录"
    ]

    candidates = []

    for file in DATA_DIR.rglob("*.csv"):
        name = file.stem.lower()

        if any(word.lower() in name for word in excluded):
            continue

        if any(word.lower() in name for word in keywords):
            candidates.append(file)

    if len(candidates) == 1:
        return candidates[0]

    if len(candidates) == 0:
        raise FileNotFoundError(
            "未自动找到商品档案，请在代码顶部 PRODUCT_FILE 中填写实际文件路径。"
        )

    raise ValueError(
        "检测到多个可能的商品档案，请手动指定 PRODUCT_FILE：\n"
        + "\n".join(str(p) for p in candidates)
    )


# 4. 自动识别字段
def find_column(df, candidates, required=True):
    # 优先完全匹配
    normalized = {
        str(col).strip().lower(): col
        for col in df.columns
    }

    for name in candidates:
        key = name.strip().lower()
        if key in normalized:
            return normalized[key]

    # 再进行包含匹配
    for name in candidates:
        key = name.strip().lower()

        for col in df.columns:
            if key in str(col).strip().lower():
                return col

    if required:
        raise ValueError(
            f"未找到字段：{candidates}\n"
            f"当前文件字段为：{list(df.columns)}"
        )

    return None


# 5. 数值清洗
def clean_numeric(series):
    values = (
        series.astype(str)
        .str.replace(",", "", regex=False)
        .str.replace("￥", "", regex=False)
        .str.replace("¥", "", regex=False)
        .str.replace("元", "", regex=False)
        .str.replace("%", "", regex=False)
        .str.strip()
    )

    return pd.to_numeric(values, errors="coerce")


# 6. 毛利率标准化
def normalize_margin(series, original_series=None):
    result = clean_numeric(series)

    # 如果原始数据带有百分号，按百分数处理
    if original_series is not None:
        percent_mask = original_series.astype(str).str.contains(
            "%", regex=False, na=False
        )
        result.loc[percent_mask] = result.loc[percent_mask] / 100

    # 如果是25、30这类百分数格式，统一转换为0.25、0.30
    valid = result.dropna()

    if not valid.empty and valid.abs().max() > 1.5:
        result = result / 100

    return result


def main():

    print("=" * 65)
    print("第55步：统一促销品类折扣规则")
    print("=" * 65)

    # --------------------------------------------------------
    # 一、读取商品档案
    # --------------------------------------------------------
    file_path = find_product_file()
    df = read_csv_file(file_path)

    print(f"\n商品档案：{file_path.name}")
    print(f"商品原始记录数：{len(df)}")
    print(f"商品档案字段：{list(df.columns)}")

    # --------------------------------------------------------
    # 二、识别关键字段
    # --------------------------------------------------------
    category_col = find_column(
        df,
        ["商品品类", "所属品类", "品类", "商品类别", "category"]
    )

    sku_col = find_column(
        df,
        ["SKU编码", "sku_id", "商品编码", "商品ID", "SKU"],
        required=False
    )

    price_col = find_column(
        df,
        [
            "建议零售价", "商品售价", "销售价格",
            "销售价", "零售价", "售价",
            "selling_price", "retail_price", "sale_price"
        ],
        required=False
    )

    cost_col = find_column(
        df,
        [
            "单位成本", "商品成本", "采购成本",
            "采购价", "成本价", "进货价",
            "cost_price", "unit_cost", "purchase_price"
        ],
        required=False
    )

    margin_col = find_column(
        df,
        ["毛利率", "毛利率(%)", "gross_margin_rate"],
        required=False
    )

    print("\n字段匹配结果：")
    print(f"品类字段：{category_col}")
    print(f"SKU字段：{sku_col}")
    print(f"售价字段：{price_col}")
    print(f"成本字段：{cost_col}")
    print(f"毛利率字段：{margin_col}")

    if price_col is None:
        raise ValueError(
            "未识别到售价字段，请在代码中补充商品档案的实际售价字段名称。"
        )

    # --------------------------------------------------------
    # 三、清洗数据
    # --------------------------------------------------------
    data = df.copy()

    data[category_col] = (
        data[category_col]
        .fillna("未填写品类")
        .astype(str)
        .str.strip()
    )

    data["_售价"] = clean_numeric(data[price_col])

    if sku_col is not None:
        data["_SKU"] = data[sku_col].astype(str).str.strip()
        data.loc[data[sku_col].isna(), "_SKU"] = pd.NA
    else:
        data["_SKU"] = data.index.astype(str)

    # --------------------------------------------------------
    # 四、计算毛利率
    # --------------------------------------------------------
    if margin_col is not None:

        data["_毛利率"] = normalize_margin(
            data[margin_col],
            data[margin_col]
        )

        margin_source = "商品档案已有毛利率"

    elif cost_col is not None:

        data["_成本"] = clean_numeric(data[cost_col])

        data["_毛利率"] = (
            (data["_售价"] - data["_成本"]) / data["_售价"]
        ).where(data["_售价"] > 0)

        margin_source = "根据售价和成本计算"

    else:

        data["_毛利率"] = pd.NA
        margin_source = "缺少成本及毛利率字段，无法计算"

    print(f"\n毛利率计算口径：{margin_source}")

    # --------------------------------------------------------
    # 五、统计各品类经营情况
    # --------------------------------------------------------
    records = []

    for category, group in data.groupby(category_col, dropna=False):

        valid_price = group["_售价"].dropna()
        valid_margin = group["_毛利率"].dropna()

        sku_count = group["_SKU"].nunique()

        records.append({
            "商品品类": category,
            "SKU数量": sku_count,
            "平均售价": round(valid_price.mean(), 2)
                if not valid_price.empty else None,
            "平均毛利率": round(valid_margin.mean() * 100, 2)
                if not valid_margin.empty else None,
            "缺失售价SKU数": int(group["_售价"].isna().sum()),
            "缺失毛利率SKU数": int(group["_毛利率"].isna().sum())
        })

    summary = pd.DataFrame(records)

    summary = summary.sort_values(
        by="SKU数量",
        ascending=False
    )

    # 输出品类统计结果
    output_summary = DATA_DIR / "category_analysis_step55.csv"

    summary.to_csv(
        output_summary,
        index=False,
        encoding="utf-8-sig"
    )

    # --------------------------------------------------------
    # 六、生成品类折扣规则配置模板
    # --------------------------------------------------------
    rules = pd.DataFrame({
        "category": summary["商品品类"],
        "min_discount_factor": "",
        "max_discount_factor": "",
        "default_discount_factor": "",
        "min_gross_margin_rate": "",
        "rule_note": ""
    })

    output_rules = DATA_DIR / "category_discount_rules_template.csv"

    rules.to_csv(
        output_rules,
        index=False,
        encoding="utf-8-sig"
    )

    # --------------------------------------------------------
    # 七、打印执行报告
    # --------------------------------------------------------
    print("\n" + "=" * 65)
    print("品类经营数据统计结果")
    print("=" * 65)

    print(summary.to_string(index=False))

    print("\n" + "=" * 65)
    print("第55步任务1完成")
    print("=" * 65)

    print(f"商品档案记录数：{len(data)}")
    print(f"商品品类数量：{len(summary)}")
    print(f"SKU总数：{data['_SKU'].nunique()}")
    print(f"毛利率数据来源：{margin_source}")

    print("\n生成文件：")
    print(f"1. {output_summary}")
    print(f"2. {output_rules}")

    print("\n注意：折扣规则配置模板暂不自动填写。")
    print("下一步需要根据品类毛利空间和经营定位确定合理折扣范围。")


if __name__ == "__main__":
    main()

