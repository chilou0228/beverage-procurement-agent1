from pathlib import Path
import json
import re
import sqlite3
import urllib.request
import urllib.error

import numpy as np
import pandas as pd


# ============================================================
# 1. 项目路径与数据库
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]
DB_PATH = BASE_DIR / "data" / "database" / "beverage_agent.db"

OLLAMA_URL = "http://localhost:11434/api/chat"
OLLAMA_MODEL = "qwen2.5:7b"


def read_table(table_name):
    """从SQLite读取数据表。"""

    allowed_tables = {
        "products",
        "sales_daily",
        "inventory_snapshot",
        "inventory_batches",
        "purchase_orders",
        "purchase_order_details",
        "purchase_receipts",
        "suppliers",
        "supplier_ratings_v2",
        "supplier_strategies",
        "product_supplier_mapping",
        "backup_supplier_recommendations",
        "competitor_prices",
        "promotions",
        "promotion_details",
        "brands",
    }

    if table_name not in allowed_tables:
        raise ValueError(f"不允许读取数据表：{table_name}")

    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"数据库不存在：{DB_PATH}。请先运行 scripts/init_database.py"
        )

    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql_query(
            f'SELECT * FROM "{table_name}"',
            conn
        )


def safe_number(value, default=0):
    """安全转换数字。"""

    try:
        if pd.isna(value):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def records_to_text(df, limit=15):
    """将DataFrame转换为适合Agent阅读的文本。"""

    if df is None or df.empty:
        return "没有查询到符合条件的数据。"

    return df.head(limit).to_string(index=False)


# ============================================================
# 2. 经营总览
# ============================================================

def get_business_overview():
    sales = read_table("sales_daily")

    sales["date"] = pd.to_datetime(sales["date"])

    latest_date = sales["date"].max()
    start_date = latest_date - pd.Timedelta(days=29)

    recent = sales[
        sales["date"].between(start_date, latest_date)
    ]

    revenue = recent["revenue"].sum()
    gross_profit = recent["gross_profit"].sum()
    volume = recent["sales_volume"].sum()
    visitors = recent["visitors"].sum()
    orders = recent["orders"].sum()

    gross_margin = (
        gross_profit / revenue
        if revenue > 0 else 0
    )

    conversion_rate = (
        orders / visitors
        if visitors > 0 else 0
    )

    average_price = (
        revenue / volume
        if volume > 0 else 0
    )

    return {
        "period": (
            f"{start_date.strftime('%Y-%m-%d')} 至 "
            f"{latest_date.strftime('%Y-%m-%d')}"
        ),
        "revenue": round(revenue, 2),
        "gross_profit": round(gross_profit, 2),
        "gross_margin": round(gross_margin * 100, 2),
        "sales_volume": int(volume),
        "visitors": int(visitors),
        "orders": int(orders),
        "conversion_rate": round(conversion_rate * 100, 2),
        "average_price": round(average_price, 2),
    }


# ============================================================
# 3. 品类经营分析
# ============================================================

def get_category_analysis():
    sales = read_table("sales_daily")

    sales["date"] = pd.to_datetime(sales["date"])

    latest_date = sales["date"].max()
    start_date = latest_date - pd.Timedelta(days=29)

    recent = sales[
        sales["date"].between(start_date, latest_date)
    ]

    result = (
        recent.groupby("category_name")
        .agg(
            revenue=("revenue", "sum"),
            gross_profit=("gross_profit", "sum"),
            sales_volume=("sales_volume", "sum"),
            visitors=("visitors", "sum"),
            orders=("orders", "sum"),
        )
        .reset_index()
    )

    result["gross_margin"] = np.where(
        result["revenue"] > 0,
        result["gross_profit"] / result["revenue"] * 100,
        0
    )

    result["conversion_rate"] = np.where(
        result["visitors"] > 0,
        result["orders"] / result["visitors"] * 100,
        0
    )

    result = result.sort_values(
        "revenue",
        ascending=False
    )

    return result.round(2)


# ============================================================
# 4. 库存风险分析
# ============================================================

def get_inventory_risks():
    inventory = read_table("inventory_snapshot")
    batches = read_table("inventory_batches")

    inventory["inventory_coverage_days"] = pd.to_numeric(
        inventory["inventory_coverage_days"],
        errors="coerce"
    )

    def classify_inventory(days):
        if pd.isna(days):
            return "数据待核实"
        if days <= 7:
            return "紧急缺货风险"
        if days <= 15:
            return "库存偏低"
        if days >= 60:
            return "库存积压关注"
        return "库存正常"

    inventory["risk_level"] = (
        inventory["inventory_coverage_days"]
        .apply(classify_inventory)
    )

    inventory = inventory.sort_values(
        "inventory_coverage_days",
        ascending=True
    )

    batches["expiry_date"] = pd.to_datetime(
        batches["expiry_date"],
        errors="coerce"
    )

    batches["snapshot_date"] = pd.to_datetime(
        batches["snapshot_date"],
        errors="coerce"
    )

    batches["days_to_expiry"] = (
        batches["expiry_date"] - batches["snapshot_date"]
    ).dt.days

    expiring = batches[
        batches["days_to_expiry"].between(0, 30)
        & batches["expiry_date"].notna()
    ].copy()

    expiring = expiring.sort_values(
        "days_to_expiry"
    )

    summary = {
        "urgent": int(
            (inventory["risk_level"] == "紧急缺货风险").sum()
        ),
        "low": int(
            (inventory["risk_level"] == "库存偏低").sum()
        ),
        "overstock": int(
            (inventory["risk_level"] == "库存积压关注").sum()
        ),
        "expiring_batches": len(expiring),
    }

    return {
        "summary": summary,
        "inventory": inventory,
        "expiring": expiring,
    }


# ============================================================
# 5. 供应商分析
# ============================================================

def get_supplier_analysis():
    ratings = read_table("supplier_ratings_v2")

    strategies = read_table("supplier_strategies")

    result = ratings.merge(
        strategies[
            [
                "supplier_id",
                "cooperation_level",
                "purchase_priority",
                "risk_control_action",
                "development_action",
            ]
        ],
        on="supplier_id",
        how="left",
        validate="one_to_one"
    )

    result = result.sort_values(
        "total_score",
        ascending=False,
        na_position="last"
    )

    return result


# ============================================================
# 6. 竞品价格分析
# ============================================================

def get_competitor_analysis():
    competitors = read_table("competitor_prices")

    result = (
        competitors.groupby("category_name")
        .agg(
            competitor_count=("competitor_id", "count"),
            avg_competitor_price=("competitor_price", "mean"),
            avg_own_price=("own_selling_price", "mean"),
            avg_price_difference=("price_difference", "mean"),
            lower_price_count=(
                "price_difference",
                lambda x: int((x < 0).sum())
            ),
        )
        .reset_index()
    )

    result["price_difference_rate"] = np.where(
        result["avg_own_price"] > 0,
        result["avg_price_difference"]
        / result["avg_own_price"] * 100,
        0
    )

    return result.sort_values(
        "avg_price_difference"
    ).round(2)


# ============================================================
# 7. 采购补货建议
# ============================================================

def get_procurement_plan():
    inventory = read_table("inventory_snapshot")

    products = read_table("products")

    mapping = read_table("product_supplier_mapping")

    ratings = read_table("supplier_ratings_v2")

    primary_mapping = mapping[
        mapping["is_primary"].astype(str).str.lower().isin(
            ["true", "1", "yes"]
        )
    ].copy()

    primary_mapping = primary_mapping.merge(
        ratings[
            [
                "supplier_id",
                "total_score",
                "supplier_grade",
                "evaluation_status",
            ]
        ],
        on="supplier_id",
        how="left"
    )

    result = inventory.merge(
        products[
            [
                "sku_id",
                "selling_price",
                "purchase_cost",
                "lead_time_days",
            ]
        ],
        on="sku_id",
        how="left"
    )

    result = result.merge(
        primary_mapping[
            [
                "sku_id",
                "supplier_id",
                "supplier_name",
                "supplier_quote_cost",
                "avg_lead_time_days",
                "total_score",
                "supplier_grade",
            ]
        ],
        on="sku_id",
        how="left"
    )

    result["avg_daily_sales_30d"] = pd.to_numeric(
        result["avg_daily_sales_30d"],
        errors="coerce"
    ).fillna(0)

    result["available_stock"] = pd.to_numeric(
        result["available_stock"],
        errors="coerce"
    ).fillna(0)

    result["on_order_stock"] = pd.to_numeric(
        result["on_order_stock"],
        errors="coerce"
    ).fillna(0)

    result["safety_stock"] = pd.to_numeric(
        result["safety_stock"],
        errors="coerce"
    ).fillna(0)

    result["avg_lead_time_days"] = pd.to_numeric(
        result["avg_lead_time_days"],
        errors="coerce"
    ).fillna(7)

    # 目标库存 = 日均销量 × 交期 + 安全库存
    result["target_stock"] = (
        result["avg_daily_sales_30d"]
        * result["avg_lead_time_days"]
        + result["safety_stock"]
    )

    # 建议采购量 = 目标库存 - 可用库存 - 在途库存
    result["suggested_purchase_quantity"] = np.ceil(
        (
            result["target_stock"]
            - result["available_stock"]
            - result["on_order_stock"]
        ).clip(lower=0)
    )

    result["estimated_purchase_amount"] = (
        result["suggested_purchase_quantity"]
        * result["supplier_quote_cost"].fillna(
            result["purchase_cost"]
        )
    )

    result["procurement_priority"] = np.select(
        [
            result["suggested_purchase_quantity"] > 0,
            result["inventory_coverage_days"] <= 7,
            result["inventory_coverage_days"] <= 15,
        ],
        [
            "建议补货",
            "紧急关注",
            "重点关注",
        ],
        default="暂不补货"
    )

    result = result.sort_values(
        [
            "suggested_purchase_quantity",
            "inventory_coverage_days",
        ],
        ascending=[False, True]
    )

    return result


# ============================================================
# 8. 促销活动分析
# ============================================================

def get_promotion_analysis():
    details = read_table("promotion_details")

    promotions = read_table("promotions")

    result = details.merge(
        promotions[
            [
                "promotion_id",
                "promotion_name",
                "promotion_type",
                "promotion_scene",
                "start_date",
                "end_date",
            ]
        ],
        on="promotion_id",
        how="left",
        validate="many_to_one"
    )

    result = result.sort_values(
        "promotion_gross_margin",
        ascending=True
    )

    return result


# ============================================================
# 9. 单SKU诊断
# ============================================================

def diagnose_product(sku_id):
    products = read_table("products")

    product = products[
        products["sku_id"].astype(str)
        == str(sku_id)
    ]

    if product.empty:
        return {
            "error": f"没有找到商品编号 {sku_id}"
        }

    product = product.iloc[0]

    sales = read_table("sales_daily")

    sales["date"] = pd.to_datetime(sales["date"])

    latest_date = sales["date"].max()
    start_date = latest_date - pd.Timedelta(days=29)

    recent = sales[
        (sales["sku_id"] == sku_id)
        & sales["date"].between(start_date, latest_date)
    ]

    inventory = read_table("inventory_snapshot")

    stock = inventory[
        inventory["sku_id"] == sku_id
    ]

    competitors = read_table("competitor_prices")

    comp = competitors[
        competitors["sku_id"] == sku_id
    ]

    recommendations = read_table(
        "backup_supplier_recommendations"
    )

    supplier = recommendations[
        recommendations["sku_id"] == sku_id
    ]

    promotions = read_table("promotion_details")

    promotion = promotions[
        promotions["sku_id"] == sku_id
    ]

    return {
        "product": product.to_dict(),
        "sales": {
            "revenue_30d": round(
                recent["revenue"].sum(), 2
            ),
            "gross_profit_30d": round(
                recent["gross_profit"].sum(), 2
            ),
            "volume_30d": int(
                recent["sales_volume"].sum()
            ),
            "visitors_30d": int(
                recent["visitors"].sum()
            ),
        },
        "inventory": (
            stock.iloc[0].to_dict()
            if not stock.empty else {}
        ),
        "competitor": {
            "avg_price": round(
                comp["competitor_price"].mean(), 2
            ) if not comp.empty else None,
            "count": len(comp),
        },
        "supplier": (
            supplier.iloc[0].to_dict()
            if not supplier.empty else {}
        ),
        "promotion": (
            promotion[
                [
                    "promotion_price",
                    "promotion_gross_margin",
                    "profit_warning",
                ]
            ].to_dict("records")
            if not promotion.empty else []
        ),
    }


# ============================================================
# 10. 促销方案模拟
# ============================================================

def simulate_promotion(sku_id, discount_rate):
    products = read_table("products")

    product = products[
        products["sku_id"].astype(str)
        == str(sku_id)
    ]

    if product.empty:
        return {
            "error": f"没有找到商品编号 {sku_id}"
        }

    if not 0 < float(discount_rate) <= 1:
        return {
            "error": "折扣率必须大于0且小于等于1"
        }

    product = product.iloc[0]

    original_price = float(product["selling_price"])
    purchase_cost = float(product["purchase_cost"])

    promotion_price = round(
        original_price * float(discount_rate),
        2
    )

    unit_profit = round(
        promotion_price - purchase_cost,
        2
    )

    gross_margin = (
        unit_profit / promotion_price
        if promotion_price > 0 else 0
    )

    if unit_profit < 0:
        warning = "促销价格低于采购成本"
    elif gross_margin < 0.10:
        warning = "促销后毛利率低于10%"
    else:
        warning = "毛利空间正常"

    return {
        "sku_id": sku_id,
        "product_name": product["product_name"],
        "original_price": original_price,
        "purchase_cost": purchase_cost,
        "discount_rate": float(discount_rate),
        "promotion_price": promotion_price,
        "unit_profit": unit_profit,
        "gross_margin": round(gross_margin * 100, 2),
        "warning": warning,
    }


# ============================================================
# 11. Agent工具定义
# ============================================================

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_business_overview",
            "description": "查询最近30天整体经营指标，包括销售额、毛利、销量、访客和转化率。",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_category_analysis",
            "description": "分析各酒水品类最近30天的销售额、毛利、销量和转化率。",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_inventory_risks",
            "description": "查询库存覆盖天数、低库存、库存积压和临期批次风险。",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_supplier_analysis",
            "description": "查询供应商评分、等级、合作策略和风险控制建议。",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_competitor_analysis",
            "description": "查询各品类竞品均价、本品价格和竞品价格差异。",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_procurement_plan",
            "description": "根据日均销量、交期、安全库存、可用库存和在途库存计算采购补货建议。",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_promotion_analysis",
            "description": "查询促销价格、促销毛利率和毛利风险预警。",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "diagnose_product",
            "description": "综合诊断指定SKU的销售、库存、竞品、供应商和促销情况。",
            "parameters": {
                "type": "object",
                "properties": {
                    "sku_id": {
                        "type": "string",
                        "description": "商品SKU编号，例如SKU0001",
                    },
                },
                "required": ["sku_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "simulate_promotion",
            "description": "模拟指定SKU在某个折扣率下的促销价格、单件毛利、毛利率和风险。",
            "parameters": {
                "type": "object",
                "properties": {
                    "sku_id": {
                        "type": "string",
                        "description": "商品SKU编号",
                    },
                    "discount_rate": {
                        "type": "number",
                        "description": "折扣率，例如0.85代表85折",
                    },
                },
                "required": ["sku_id", "discount_rate"],
            },
        },
    },
]


TOOL_FUNCTIONS = {
    "get_business_overview": get_business_overview,
    "get_category_analysis": get_category_analysis,
    "get_inventory_risks": get_inventory_risks,
    "get_supplier_analysis": get_supplier_analysis,
    "get_competitor_analysis": get_competitor_analysis,
    "get_procurement_plan": get_procurement_plan,
    "get_promotion_analysis": get_promotion_analysis,
    "diagnose_product": diagnose_product,
    "simulate_promotion": simulate_promotion,
}


def run_tool(name, arguments=None):
    arguments = arguments or {}

    if name not in TOOL_FUNCTIONS:
        return {"error": f"未知工具：{name}"}

    try:
        result = TOOL_FUNCTIONS[name](**arguments)

        if isinstance(result, pd.DataFrame):
            return {
                "columns": list(result.columns),
                "rows": result.head(30).to_dict("records"),
                "total_rows": len(result),
            }

        if isinstance(result, dict):
            clean = {}
            for key, value in result.items():
                if isinstance(value, pd.DataFrame):
                    clean[key] = value.head(20).to_dict("records")
                elif isinstance(value, pd.Series):
                    clean[key] = value.to_dict()
                elif isinstance(value, pd.Timestamp):
                    clean[key] = str(value)
                else:
                    clean[key] = value
            return clean

        return result

    except Exception as exc:
        return {"error": str(exc)}


# ============================================================
# 12. 无模型时的本地业务路由
# ============================================================

def local_route(question):
    q = question.lower()

    sku_match = re.search(
        r"SKU\d+",
        question,
        re.IGNORECASE
    )

    sku_id = sku_match.group(0).upper() if sku_match else None

    if any(word in q for word in ["促销模拟", "打几折", "折扣模拟", "促销价格"]):
        if sku_id:
            rate_match = re.search(
                r"(0\.\d+|\d{1,2}\s*折)",
                q
            )

            if rate_match:
                raw = rate_match.group(1)

                if "折" in raw:
                    rate = float(raw.replace("折", "").strip()) / 10
                else:
                    rate = float(raw)

                return run_tool(
                    "simulate_promotion",
                    {
                        "sku_id": sku_id,
                        "discount_rate": rate,
                    }
                )

    if sku_id and any(
        word in q for word in ["诊断", "分析", "怎么样", "情况"]
    ):
        return run_tool(
            "diagnose_product",
            {"sku_id": sku_id}
        )

    if any(word in q for word in ["补货", "采购计划", "采购建议"]):
        return run_tool("get_procurement_plan")

    if any(word in q for word in ["库存", "缺货", "临期", "积压"]):
        return run_tool("get_inventory_risks")

    if any(word in q for word in ["供应商", "供货商"]):
        return run_tool("get_supplier_analysis")

    if any(word in q for word in ["竞品", "竞对", "价格对比"]):
        return run_tool("get_competitor_analysis")

    if any(word in q for word in ["促销", "毛利预警", "促销活动"]):
        return run_tool("get_promotion_analysis")

    if any(word in q for word in ["品类", "分类销售"]):
        return run_tool("get_category_analysis")

    return run_tool("get_business_overview")


# ============================================================
# 13. 本地大模型 Tool Calling
# ============================================================

def ask_ollama(question):
    messages = [
        {
            "role": "system",
            "content": (
                "你是酒水采销经营分析助手。"
                "你必须根据用户问题选择合适的业务工具。"
                "涉及经营数据时必须调用工具，不能编造数据。"
                "采购建议仅供决策参考，不自动执行采购订单。"
                "项目使用模拟数据，回答时必须说明数据为模拟数据。"
                "请使用中文回答，结构清晰，给出关键指标和建议。"
            ),
        },
        {
            "role": "user",
            "content": question,
        },
    ]

    for _ in range(4):
        payload = {
            "model": OLLAMA_MODEL,
            "messages": messages,
            "tools": TOOLS,
            "stream": False,
        }

        request = urllib.request.Request(
            OLLAMA_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urllib.request.urlopen(
            request,
            timeout=120
        ) as response:
            result = json.loads(
                response.read().decode("utf-8")
            )

        message = result.get("message", {})
        tool_calls = message.get("tool_calls", [])

        if not tool_calls:
            return message.get(
                "content",
                "模型没有返回有效回答。"
            )

        messages.append(message)

        for call in tool_calls:
            function = call.get("function", {})
            name = function.get("name")
            arguments = function.get("arguments", {})

            tool_result = run_tool(
                name,
                arguments
            )

            messages.append({
                "role": "tool",
                "name": name,
                "content": json.dumps(
                    tool_result,
                    ensure_ascii=False,
                    default=str
                ),
            })

    return "工具调用次数达到上限，请缩小问题范围后重试。"


# ============================================================
# 14. Agent统一入口
# ============================================================

def ask_agent(question, use_ollama=False):
    if not question or not question.strip():
        return {
            "mode": "提示",
            "answer": "请输入你的业务问题。",
        }

    if use_ollama:
        try:
            answer = ask_ollama(question)

            return {
                "mode": "本地大模型 Tool Calling",
                "answer": answer,
            }

        except Exception as exc:
            return {
                "mode": "本地工具路由（模型不可用）",
                "answer": (
                    "本地模型暂时无法连接，已切换为业务工具路由模式。\n\n"
                    f"模型连接信息：{exc}\n\n"
                    "以下是业务工具查询结果：\n"
                    + json.dumps(
                        local_route(question),
                        ensure_ascii=False,
                        indent=2,
                        default=str
                    )
                ),
            }

    result = local_route(question)

    return {
        "mode": "本地业务工具路由",
        "answer": json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
            default=str
        ),
    }