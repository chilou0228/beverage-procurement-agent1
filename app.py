
from pathlib import Path
import math

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


# ============================================================
# 1. 页面基础配置
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data" / "processed"

st.set_page_config(
    page_title="酒水智能采销决策系统",
    page_icon="🍷",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# 2. 页面视觉样式
# ============================================================

st.markdown(
    """
    <style>
    .stApp {
        background-color: #F5F6F8;
        color: #30343B;
    }

    [data-testid="stSidebar"] {
        background-color: #FFFFFF;
        border-right: 1px solid #E9EBEF;
    }

    [data-testid="stSidebar"] * {
        color: #30343B;
    }

    h1, h2, h3 {
        color: #30343B;
    }

    div[data-testid="stMetric"] {
        background-color: #FFFFFF;
        border: 1px solid #E9EBEF;
        border-radius: 12px;
        padding: 16px;
    }

    div[data-testid="stMetricLabel"] {
        color: #777F89;
    }

    div[data-testid="stMetricValue"] {
        color: #F04438;
    }

    .main-title {
        font-size: 28px;
        font-weight: 750;
        color: #30343B;
        margin-bottom: 4px;
    }

    .sub-title {
        font-size: 14px;
        color: #858C96;
        margin-bottom: 20px;
    }

    .section-title {
        font-size: 19px;
        font-weight: 700;
        color: #30343B;
        margin-top: 12px;
        margin-bottom: 10px;
    }

    .notice {
        background: #FFF7F5;
        border: 1px solid #FFE1DC;
        border-radius: 10px;
        padding: 12px 15px;
        color: #7C4942;
        font-size: 13px;
    }

    div[data-testid="stDataFrame"] {
        border: 1px solid #E9EBEF;
        border-radius: 10px;
    }

    .stButton > button {
        background-color: #F04438;
        color: white;
        border: none;
        border-radius: 8px;
    }

    .stButton > button:hover {
        background-color: #D9362B;
        color: white;
        border: none;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# 3. 数据读取
# ============================================================

@st.cache_data(show_spinner=False)
def load_csv(filename):
    path = DATA_DIR / filename

    if not path.exists():
        return pd.DataFrame()

    try:
        return pd.read_csv(
            path,
            encoding="utf-8-sig"
        )
    except Exception as e:
        st.error(f"读取文件失败：{filename}，错误：{e}")
        return pd.DataFrame()


def require_data(filename, display_name):
    df = load_csv(filename)

    if df.empty:
        st.error(
            f"未找到{display_name}数据。"
            f"请确认文件存在：data/processed/{filename}"
        )
        st.stop()

    return df


products = load_csv("products.csv")
brands = load_csv("brands.csv")
suppliers = load_csv("suppliers.csv")
mapping = load_csv("product_supplier_mapping.csv")
sales = load_csv("sales_daily.csv")
inventory = load_csv("inventory_snapshot.csv")
batches = load_csv("inventory_batches.csv")
purchase_orders = load_csv("purchase_orders.csv")
purchase_details = load_csv("purchase_order_details.csv")
receipts = load_csv("purchase_receipts.csv")
supplier_performance = load_csv("supplier_performance.csv")
supplier_ratings = load_csv("supplier_ratings_v2.csv")
supplier_strategies = load_csv("supplier_strategies.csv")
backup_recommendations = load_csv("backup_supplier_recommendations.csv")
competitors = load_csv("competitor_prices.csv")
promotions = load_csv("promotions.csv")
promotion_details = load_csv("promotion_details.csv")


# ============================================================
# 4. 数据处理辅助函数
# ============================================================

def to_number(series):
    return pd.to_numeric(series, errors="coerce").fillna(0)


def money(value):
    if pd.isna(value):
        return "—"

    return f"¥{value:,.2f}"


def number(value):
    if pd.isna(value):
        return "—"

    return f"{value:,.0f}"


def pct(value):
    if pd.isna(value):
        return "—"

    return f"{value:.2%}"


def add_title(title, subtitle=None):
    st.markdown(
        f'<div class="main-title">{title}</div>',
        unsafe_allow_html=True
    )

    if subtitle:
        st.markdown(
            f'<div class="sub-title">{subtitle}</div>',
            unsafe_allow_html=True
        )


def add_section(title):
    st.markdown(
        f'<div class="section-title">{title}</div>',
        unsafe_allow_html=True
    )


def show_table(df, height=420):
    if df.empty:
        st.info("暂无符合条件的数据。")
        return

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        height=height
    )


def download_csv(df, filename, label="下载CSV"):
    if df.empty:
        st.warning("暂无可下载的数据。")
        return

    st.download_button(
        label=label,
        data=df.to_csv(
            index=False,
            encoding="utf-8-sig"
        ).encode("utf-8-sig"),
        file_name=filename,
        mime="text/csv",
    )


def category_filter(df, column="category_name"):
    if column not in df.columns:
        return df

    categories = sorted(
        df[column].dropna().astype(str).unique().tolist()
    )

    selected = st.multiselect(
        "筛选品类",
        categories,
        default=categories,
        key=f"category_filter_{column}_{len(df)}"
    )

    return df[df[column].astype(str).isin(selected)]


def safe_divide(a, b):
    if b is None or b == 0:
        return 0

    return a / b


# ============================================================
# 5. 侧边栏
# ============================================================

with st.sidebar:
    st.markdown("## 🍷 酒水智能采销")
    st.caption("经营分析 · 采购决策 · 供应链管理")
    st.divider()

    page = st.radio(
        "功能导航",
        [
            "经营总览",
            "品类经营分析",
            "SKU商品诊断",
            "库存风险预警",
            "供应商管理",
            "竞品价格分析",
            "促销利润模拟",
            "智能业务助手",
            "数据说明",
        ],
        label_visibility="collapsed"
    )

    st.divider()

    st.caption("项目数据类型：模拟数据")
    st.caption("版本：规则驱动 Demo")


# ============================================================
# 6. 页面一：经营总览
# ============================================================

if page == "经营总览":

    add_title(
        "经营总览",
        "全品类经营数据监控与采销决策概览"
    )

    if sales.empty or products.empty:
        st.error("经营总览所需销售或商品数据缺失。")
        st.stop()

    sales = sales.copy()
    sales["date"] = pd.to_datetime(
        sales["date"],
        errors="coerce"
    )

    sales = sales.dropna(subset=["date"])

    min_date = sales["date"].min().date()
    max_date = sales["date"].max().date()

    col_date, col_category = st.columns([2, 2])

    with col_date:
        date_range = st.date_input(
            "统计日期范围",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date
        )

    with col_category:
        categories = sorted(
            sales["category_name"].dropna().unique()
        )

        selected_categories = st.multiselect(
            "经营品类",
            categories,
            default=categories
        )

    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = date_range
    else:
        start_date, end_date = min_date, max_date

    filtered = sales[
        (sales["date"].dt.date >= start_date)
        & (sales["date"].dt.date <= end_date)
        & (sales["category_name"].isin(selected_categories))
    ].copy()

    revenue = to_number(filtered["revenue"]).sum()
    gross_profit = to_number(filtered["gross_profit"]).sum()
    volume = to_number(filtered["sales_volume"]).sum()
    visitors = to_number(filtered["visitors"]).sum()
    orders = to_number(filtered["orders"]).sum()

    gross_margin = safe_divide(gross_profit, revenue)
    conversion = safe_divide(orders, visitors)
    aov = safe_divide(revenue, orders)

    k1, k2, k3, k4, k5 = st.columns(5)

    k1.metric("累计销售额", money(revenue))
    k2.metric("销售毛利", money(gross_profit))
    k3.metric("销售毛利率", pct(gross_margin))
    k4.metric("销量", number(volume))
    k5.metric("模拟转化率", pct(conversion))

    st.caption(
        f"统计周期：{start_date} 至 {end_date}。"
        "毛利未扣除平台佣金、物流、营销费用等。"
    )

    add_section("销售趋势")

    daily = (
        filtered.groupby("date", as_index=False)
        .agg(
            revenue=("revenue", "sum"),
            gross_profit=("gross_profit", "sum")
        )
    )

    if not daily.empty:
        fig = px.line(
            daily,
            x="date",
            y="revenue",
            markers=False,
            title="每日销售额趋势"
        )

        fig.update_traces(
            line=dict(color="#F04438", width=2.5)
        )

        fig.update_layout(
            height=350,
            plot_bgcolor="white",
            paper_bgcolor="white",
            xaxis_title="日期",
            yaxis_title="销售额（元）"
        )

        st.plotly_chart(fig, use_container_width=True)

    left, right = st.columns(2)

    with left:
        add_section("品类销售额排名")

        category_sales = (
            filtered.groupby("category_name", as_index=False)
            .agg(revenue=("revenue", "sum"))
            .sort_values("revenue", ascending=False)
        )

        fig = px.bar(
            category_sales,
            x="revenue",
            y="category_name",
            orientation="h",
            text_auto=".3s",
            title="各品类销售额"
        )

        fig.update_traces(marker_color="#F04438")
        fig.update_layout(
            height=400,
            yaxis={"categoryorder": "total ascending"}
        )

        st.plotly_chart(fig, use_container_width=True)

    with right:
        add_section("经营指标")

        category_metrics = (
            filtered.groupby("category_name", as_index=False)
            .agg(
                revenue=("revenue", "sum"),
                gross_profit=("gross_profit", "sum"),
                sales_volume=("sales_volume", "sum")
            )
        )

        category_metrics["gross_margin"] = (
            category_metrics["gross_profit"]
            / category_metrics["revenue"].replace(0, np.nan)
        )

        category_metrics["gross_margin"] = (
            category_metrics["gross_margin"].fillna(0)
        )

        show_table(
            category_metrics.sort_values(
                "revenue",
                ascending=False
            ).round(3)
        )

    add_section("采购与库存概况")

    if not inventory.empty:
        inv_stock = to_number(inventory["available_stock"]).sum()
        inv_transit = to_number(inventory["on_order_stock"]).sum()
        inv_cost = to_number(inventory["inventory_cost"]).sum()

        a, b, c = st.columns(3)

        a.metric("可用库存", number(inv_stock))
        b.metric("在途库存", number(inv_transit))
        c.metric("库存成本", money(inv_cost))

    if not purchase_orders.empty:
        st.metric(
            "采购订单数量",
            number(len(purchase_orders))
        )

    st.info(
        "提示：本页面使用模拟销售数据。订单数及转化率为模拟口径，"
        "不代表真实平台交易数据。"
    )


# ============================================================
# 7. 页面二：品类经营分析
# ============================================================

elif page == "品类经营分析":

    add_title(
        "品类经营分析",
        "从销售规模、毛利水平和商品结构观察品类表现"
    )

    df = require_data("sales_daily.csv", "销售")

    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    category_data = (
        df.groupby("category_name", as_index=False)
        .agg(
            revenue=("revenue", "sum"),
            gross_profit=("gross_profit", "sum"),
            sales_volume=("sales_volume", "sum"),
            visitors=("visitors", "sum"),
            orders=("orders", "sum")
        )
    )

    category_data["gross_margin"] = (
        category_data["gross_profit"]
        / category_data["revenue"].replace(0, np.nan)
    )

    category_data["gross_margin"] = (
        category_data["gross_margin"].fillna(0)
    )

    category_data["conversion_rate"] = (
        category_data["orders"]
        / category_data["visitors"].replace(0, np.nan)
    )

    category_data["conversion_rate"] = (
        category_data["conversion_rate"].fillna(0)
    )

    c1, c2 = st.columns(2)

    with c1:
        fig = px.bar(
            category_data.sort_values("revenue"),
            x="revenue",
            y="category_name",
            orientation="h",
            title="品类销售额"
        )
        fig.update_traces(marker_color="#F04438")
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        fig = px.scatter(
            category_data,
            x="revenue",
            y="gross_margin",
            size="sales_volume",
            color="category_name",
            hover_name="category_name",
            title="品类销售规模与毛利率"
        )
        st.plotly_chart(fig, use_container_width=True)

    add_section("品类经营指标明细")

    show_table(
        category_data.sort_values(
            "revenue",
            ascending=False
        ).round(4)
    )

    download_csv(
        category_data,
        "category_analysis.csv",
        "下载品类分析结果"
    )


# ============================================================
# 8. 页面三：SKU商品诊断
# ============================================================

elif page == "SKU商品诊断":

    add_title(
        "SKU商品诊断",
        "查看单品销售表现、库存状况、竞品价格及供应商信息"
    )

    product_df = require_data("products.csv", "商品")

    sku_options = product_df["sku_id"].astype(str).tolist()

    selected_sku = st.selectbox(
        "选择商品SKU",
        sku_options
    )

    product = product_df[
        product_df["sku_id"].astype(str) == selected_sku
    ].iloc[0]

    a, b, c, d = st.columns(4)

    a.metric("商品名称", str(product["product_name"]))
    b.metric("品类", str(product["category_name"]))
    c.metric("基础售价", money(product["selling_price"]))
    d.metric("采购成本", money(product["purchase_cost"]))

    sku_sales = sales[
        sales["sku_id"].astype(str) == selected_sku
    ].copy()

    if not sku_sales.empty:
        sku_sales["date"] = pd.to_datetime(
            sku_sales["date"],
            errors="coerce"
        )

        sku_trend = (
            sku_sales.groupby("date", as_index=False)
            .agg(
                revenue=("revenue", "sum"),
                sales_volume=("sales_volume", "sum")
            )
        )

        fig = px.line(
            sku_trend,
            x="date",
            y="revenue",
            title="SKU每日销售额趋势"
        )

        fig.update_traces(line=dict(color="#F04438", width=2))
        st.plotly_chart(fig, use_container_width=True)

    left, right = st.columns(2)

    with left:
        add_section("库存情况")

        if not inventory.empty:
            inv = inventory[
                inventory["sku_id"].astype(str) == selected_sku
            ]

            show_table(inv)

        if not batches.empty:
            batch = batches[
                batches["sku_id"].astype(str) == selected_sku
            ]

            add_section("库存批次与有效期")
            show_table(batch)

    with right:
        add_section("竞品价格")

        if not competitors.empty:
            comp = competitors[
                competitors["sku_id"].astype(str) == selected_sku
            ]

            show_table(
                comp[
                    [
                        "competitor_brand",
                        "competitor_channel",
                        "competitor_price",
                        "own_selling_price",
                        "price_difference_rate",
                        "price_position"
                    ]
                ]
            )

        add_section("供应商信息")

        if not mapping.empty:
            supplier_info = mapping[
                mapping["sku_id"].astype(str) == selected_sku
            ]

            show_table(supplier_info)


# ============================================================
# 9. 页面四：库存风险预警
# ============================================================

elif page == "库存风险预警":

    add_title(
        "库存风险预警",
        "结合近30天日均销量、安全库存及库存覆盖天数识别风险"
    )

    df = require_data("inventory_snapshot.csv", "库存快照")

    for col in [
        "available_stock",
        "safety_stock",
        "on_order_stock",
        "inventory_coverage_days",
        "inventory_cost",
    ]:
        df[col] = to_number(df[col])

    def inventory_risk(row):
        if row["available_stock"] <= 0:
            return "缺货风险"

        if row["available_stock"] < row["safety_stock"]:
            return "低于安全库存"

        if row["inventory_coverage_days"] < 7:
            return "高缺货风险"

        if row["inventory_coverage_days"] > 60:
            return "库存积压风险"

        return "库存正常"

    df["risk_level"] = df.apply(
        inventory_risk,
        axis=1
    )

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "库存SKU数",
        number(len(df))
    )

    c2.metric(
        "风险SKU数",
        number((df["risk_level"] != "库存正常").sum())
    )

    c3.metric(
        "库存成本",
        money(df["inventory_cost"].sum())
    )

    selected_risks = st.multiselect(
        "风险类型",
        sorted(df["risk_level"].unique()),
        default=sorted(df["risk_level"].unique())
    )

    filtered = df[
        df["risk_level"].isin(selected_risks)
    ].copy()

    filtered = category_filter(filtered)

    add_section("库存风险商品列表")

    show_table(
        filtered.sort_values(
            "inventory_coverage_days",
            ascending=True
        )
    )

    download_csv(
        filtered,
        "inventory_risk_report.csv",
        "下载库存风险报告"
    )

    st.caption(
        "风险阈值是项目设定的模拟规则，不代表实际企业库存政策。"
    )


# ============================================================
# 10. 页面五：供应商管理
# ============================================================

elif page == "供应商管理":

    add_title(
        "供应商管理",
        "供应商综合评分、合作分级与主备供应商推荐"
    )

    ratings = require_data(
        "supplier_ratings_v2.csv",
        "供应商评分"
    )

    recommendations = require_data(
        "backup_supplier_recommendations.csv",
        "备选供应商推荐"
    )

    grade_counts = ratings["supplier_grade"].value_counts()

    c1, c2, c3 = st.columns(3)

    c1.metric("供应商数量", number(len(ratings)))

    c2.metric(
        "有效评分供应商",
        number(ratings["total_score"].notna().sum())
    )

    c3.metric(
        "待观察供应商",
        number((ratings["supplier_grade"] == "待观察").sum())
    )

    left, right = st.columns(2)

    with left:
        fig = px.bar(
            grade_counts.reset_index(),
            x="supplier_grade",
            y="count",
            title="供应商等级分布",
            text_auto=True
        )

        fig.update_traces(marker_color="#F04438")
        st.plotly_chart(fig, use_container_width=True)

    with right:
        score_data = ratings[
            ratings["total_score"].notna()
        ].copy()

        fig = px.histogram(
            score_data,
            x="total_score",
            nbins=12,
            title="供应商综合评分分布"
        )

        fig.update_traces(marker_color="#FF6B65")
        st.plotly_chart(fig, use_container_width=True)

    add_section("供应商综合评分明细")

    grade_filter = st.multiselect(
        "供应商等级",
        sorted(ratings["supplier_grade"].dropna().unique()),
        default=sorted(ratings["supplier_grade"].dropna().unique())
    )

    rating_filtered = ratings[
        ratings["supplier_grade"].isin(grade_filter)
    ].copy()

    show_table(
        rating_filtered.sort_values(
            "total_score",
            ascending=False,
            na_position="last"
        )
    )

    download_csv(
        rating_filtered,
        "supplier_ratings.csv",
        "下载供应商评分"
    )

    add_section("主备供应商推荐")

    decision_filter = st.multiselect(
        "推荐决策",
        sorted(recommendations["decision"].dropna().unique()),
        default=sorted(recommendations["decision"].dropna().unique())
    )

    recommendation_filtered = recommendations[
        recommendations["decision"].isin(decision_filter)
    ].copy()

    show_table(recommendation_filtered)

    download_csv(
        recommendation_filtered,
        "backup_supplier_recommendations.csv",
        "下载备选供应商推荐结果"
    )

    st.warning(
        "供应商推荐仅为辅助决策，不会自动替换供应商。"
        "综合评分依据模拟订单和到货记录计算。"
    )


# ============================================================
# 11. 页面六：竞品价格分析
# ============================================================

elif page == "竞品价格分析":

    add_title(
        "竞品价格分析",
        "比较商品售价与模拟竞品报价，识别相对价格位置"
    )

    df = require_data(
        "competitor_prices.csv",
        "竞品价格"
    )

    df["competitor_price"] = to_number(df["competitor_price"])
    df["own_selling_price"] = to_number(df["own_selling_price"])

    c1, c2, c3 = st.columns(3)

    c1.metric("竞品记录数", number(len(df)))
    c2.metric("覆盖SKU数", number(df["sku_id"].nunique()))
    c3.metric(
        "平均价格差异",
        pct(to_number(df["price_difference_rate"]).mean())
    )

    add_section("价格位置分布")

    position_data = (
        df["price_position"]
        .value_counts()
        .rename_axis("价格位置")
        .reset_index(name="记录数")
    )

    fig = px.pie(
        position_data,
        names="价格位置",
        values="记录数",
        hole=0.45
    )

    st.plotly_chart(fig, use_container_width=True)

    add_section("竞品价格比较")

    filtered = category_filter(df)

    sku_options = sorted(
        filtered["sku_id"].astype(str).unique()
    )

    if sku_options:
        selected_sku = st.selectbox(
            "选择SKU查看竞品报价",
            sku_options
        )

        selected = filtered[
            filtered["sku_id"].astype(str) == selected_sku
        ].copy()

        if not selected.empty:
            chart_data = pd.concat(
                [
                    pd.DataFrame({
                        "报价来源": ["本品"],
                        "价格": [selected["own_selling_price"].iloc[0]]
                    }),
                    pd.DataFrame({
                        "报价来源": selected["competitor_brand"].astype(str),
                        "价格": selected["competitor_price"]
                    })
                ],
                ignore_index=True
            )

            fig = px.bar(
                chart_data,
                x="报价来源",
                y="价格",
                title="本品与模拟竞品价格比较"
            )

            fig.update_traces(marker_color="#F04438")
            st.plotly_chart(fig, use_container_width=True)

            show_table(selected)

    download_csv(
        filtered,
        "competitor_price_analysis.csv",
        "下载竞品价格分析"
    )

    st.info(
        "竞品名称、品牌、渠道和价格均为模拟数据，"
        "不代表真实市场报价或真实品牌竞争关系。"
    )


# ============================================================
# 12. 页面七：促销利润模拟
# ============================================================

elif page == "促销利润模拟":

    add_title(
        "促销利润模拟",
        "调整折扣和销量假设，观察促销方案对商品毛利的影响"
    )

    df = require_data(
        "promotion_details.csv",
        "促销明细"
    )

    sku_options = sorted(
        df["sku_id"].astype(str).unique()
    )

    selected_sku = st.selectbox(
        "选择促销商品",
        sku_options
    )

    row = df[
        df["sku_id"].astype(str) == selected_sku
    ].iloc[0]

    original_price = float(row["original_price"])
    purchase_cost = float(row["purchase_cost"])
    original_quantity = int(row["target_quantity"])
    original_discount = float(row["discount_rate"])

    st.markdown(
        f"**商品：{row['product_name']}**　"
        f"**品类：{row['category_name']}**"
    )

    a, b, c = st.columns(3)

    a.metric("原价", money(original_price))
    b.metric("采购成本", money(purchase_cost))
    c.metric("当前模拟折扣", pct(original_discount))

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        discount = st.slider(
            "促销折扣率",
            min_value=0.50,
            max_value=1.00,
            value=float(np.clip(original_discount, 0.50, 1.00)),
            step=0.01,
            format="%.2f"
        )

    with col2:
        target_quantity = st.number_input(
            "预计销量（件）",
            min_value=1,
            max_value=100000,
            value=max(original_quantity, 1),
            step=10
        )

    promotion_price = round(
        original_price * discount,
        2
    )

    unit_profit = round(
        promotion_price - purchase_cost,
        2
    )

    gross_margin = safe_divide(
        unit_profit,
        promotion_price
    )

    estimated_revenue = promotion_price * target_quantity
    estimated_gross_profit = unit_profit * target_quantity

    original_unit_profit = original_price - purchase_cost
    original_gross_profit = original_unit_profit * target_quantity

    st.divider()

    add_section("模拟结果")

    m1, m2, m3, m4 = st.columns(4)

    m1.metric("促销售价", money(promotion_price))
    m2.metric("单件毛利", money(unit_profit))
    m3.metric("促销毛利率", pct(gross_margin))
    m4.metric("预计销售额", money(estimated_revenue))

    m5, m6, m7 = st.columns(3)

    m5.metric(
        "预计销售毛利",
        money(estimated_gross_profit)
    )

    m6.metric(
        "原价销售毛利",
        money(original_gross_profit)
    )

    m7.metric(
        "毛利变化",
        money(estimated_gross_profit - original_gross_profit)
    )

    if unit_profit < 0:
        st.error(
            "高风险：促销售价低于采购成本，"
            "当前方案产生负单件毛利。"
        )

    elif gross_margin < 0.10:
        st.warning(
            "毛利预警：促销后毛利率低于10%，"
            "建议谨慎评估促销力度。"
        )

    else:
        st.success(
            "当前方案单件毛利为正，且促销后毛利率不低于10%。"
        )

    comparison = pd.DataFrame({
        "指标": ["售价", "单件毛利", "毛利率", "预计销售毛利"],
        "原价方案": [
            original_price,
            original_unit_profit,
            safe_divide(original_unit_profit, original_price),
            original_gross_profit
        ],
        "促销方案": [
            promotion_price,
            unit_profit,
            gross_margin,
            estimated_gross_profit
        ]
    })

    add_section("原价方案与促销方案对比")

    show_table(comparison.round(4))

    st.caption(
        "以上为基于输入销量的静态情景测算，"
        "没有模拟需求弹性、平台佣金、物流、营销费用和税费，"
        "不能直接视为实际净利润预测。"
    )


# ============================================================
# 13. 页面八：智能业务助手
# ============================================================

elif page == "智能业务助手":

    add_title(
        "智能业务助手",
        "基于预设业务规则和项目数据，生成采销分析摘要"
    )

    st.markdown(
        """
        <div class="notice">
        当前版本采用规则驱动方式，不调用外部大模型或付费API。
        输入关键词后，系统根据预设规则调用对应数据分析逻辑。
        </div>
        """,
        unsafe_allow_html=True
    )

    question = st.text_area(
        "请输入业务问题",
        placeholder="例如：哪些供应商风险较高？哪些商品库存覆盖天数偏高？",
        height=100
    )

    if st.button("生成分析结果", use_container_width=True):

        if not question.strip():
            st.warning("请先输入业务问题。")

        else:
            q = question.strip()

            if any(word in q for word in ["供应商", "供货", "履约"]):

                if supplier_ratings.empty:
                    st.error("供应商评分数据不存在。")

                else:
                    risky = supplier_ratings[
                        supplier_ratings["supplier_grade"] == "D级"
                    ].copy()

                    st.subheader("供应商风险分析")

                    st.write(
                        f"当前供应商评分记录共{len(supplier_ratings)}家，"
                        f"其中D级供应商{len(risky)}家。"
                    )

                    show_table(
                        risky.sort_values(
                            "total_score",
                            ascending=True
                        )
                    )

                    st.info(
                        "建议优先核查低评分供应商的订单履约、"
                        "到货及时性及未交付订单。"
                    )

            elif any(word in q for word in ["库存", "缺货", "积压"]):

                if inventory.empty:
                    st.error("库存数据不存在。")

                else:
                    temp = inventory.copy()

                    temp["inventory_coverage_days"] = to_number(
                        temp["inventory_coverage_days"]
                    )

                    risk = temp[
                        temp["inventory_coverage_days"] < 7
                    ]

                    excess = temp[
                        temp["inventory_coverage_days"] > 60
                    ]

                    st.subheader("库存风险分析")

                    st.write(
                        f"库存覆盖低于7天的SKU：{len(risk)}个；"
                        f"覆盖超过60天的SKU：{len(excess)}个。"
                    )

                    show_table(
                        pd.concat(
                            [risk, excess]
                        ).drop_duplicates("sku_id")
                    )

                    st.info(
                        "建议结合在途库存、安全库存、供应商交期"
                        "进一步判断补货优先级。"
                    )

            elif any(word in q for word in ["竞品", "价格", "定价"]):

                if competitors.empty:
                    st.error("竞品价格数据不存在。")

                else:
                    temp = competitors.copy()

                    summary = (
                        temp.groupby("price_position")
                        .size()
                        .reset_index(name="记录数")
                    )

                    st.subheader("竞品价格分析")

                    show_table(summary)

                    st.info(
                        "可优先关注明显低于本品的竞品价格，"
                        "结合本品毛利空间判断是否需要调整价格。"
                    )

            elif any(word in q for word in ["促销", "折扣", "毛利"]):

                if promotion_details.empty:
                    st.error("促销数据不存在。")

                else:
                    warning = (
                        promotion_details[
                            "profit_warning"
                        ].value_counts()
                        .reset_index()
                    )

                    st.subheader("促销毛利风险分析")

                    show_table(warning)

                    st.info(
                        "建议优先检查负毛利商品和促销后毛利率低于10%的商品。"
                    )

            elif any(word in q for word in ["销售", "GMV", "经营"]):

                if sales.empty:
                    st.error("销售数据不存在。")

                else:
                    revenue = to_number(sales["revenue"]).sum()
                    profit = to_number(sales["gross_profit"]).sum()

                    st.subheader("整体经营分析")

                    st.metric("累计销售额", money(revenue))
                    st.metric("累计销售毛利", money(profit))

                    st.info(
                        "建议结合品类销售额、毛利率和库存覆盖情况"
                        "进一步识别经营机会。"
                    )

            else:
                st.warning(
                    "暂未识别该问题。可尝试使用："
                    "销售、经营、库存、缺货、积压、供应商、"
                    "履约、竞品、价格、促销、折扣、毛利等关键词。"
                )


# ============================================================
# 14. 页面九：数据说明
# ============================================================

elif page == "数据说明":

    add_title(
        "数据说明",
        "项目数据范围、模拟口径及业务逻辑边界"
    )

    st.warning(
        "本项目所有业务数据均为模拟数据，"
        "不代表任何真实酒企、电商平台、品牌或供应商。"
    )

    data_overview = []

    files = [
        ("products.csv", products, "商品档案"),
        ("brands.csv", brands, "品牌档案"),
        ("suppliers.csv", suppliers, "供应商档案"),
        ("sales_daily.csv", sales, "每日销售数据"),
        ("inventory_snapshot.csv", inventory, "库存快照"),
        ("inventory_batches.csv", batches, "库存批次"),
        ("purchase_orders.csv", purchase_orders, "采购订单"),
        ("purchase_order_details.csv", purchase_details, "采购明细"),
        ("purchase_receipts.csv", receipts, "采购到货"),
        ("supplier_ratings_v2.csv", supplier_ratings, "供应商评分"),
        ("supplier_strategies.csv", supplier_strategies, "供应商策略"),
        ("backup_supplier_recommendations.csv", backup_recommendations, "备选供应商推荐"),
        ("competitor_prices.csv", competitors, "竞品价格"),
        ("promotions.csv", promotions, "促销活动"),
        ("promotion_details.csv", promotion_details, "促销商品明细"),
    ]

    for filename, data, description in files:
        data_overview.append({
            "文件": filename,
            "业务内容": description,
            "记录数": len(data),
            "状态": "已加载" if not data.empty else "缺失"
        })

    show_table(pd.DataFrame(data_overview))

    add_section("重要口径说明")

    st.markdown(
        """
        1. 销售额为模拟商品销售额，不等于平台净收入。
        2. 销售毛利未扣除佣金、物流、营销费用等。
        3. 库存数据为单日库存快照，不是完整历史库存流水。
        4. 供应商评分依据模拟采购订单与到货记录计算。
        5. 供应商推荐仅用于辅助比较，不自动执行采购替换。
        6. 竞品名称、品牌、渠道及报价均为模拟对象。
        7. 促销销量提升、预算和折扣均为模拟参数。
        8. 智能业务助手使用预设规则，不是LLM自主规划Agent。
        9. 所有采购决策仍需人工复核和审批。
        """
    )

    add_section("项目技术栈")

    st.markdown(
        """
        - Python
        - Pandas / NumPy
        - SQLite
        - Plotly
        - Streamlit
        - 规则驱动的业务分析与决策逻辑
        """
    )


# ============================================================
# 15. 页脚
# ============================================================

st.divider()

st.caption(
    "酒水全品类智能采销与供应链决策辅助系统｜"
    "规则驱动 Demo｜模拟数据，仅用于学习与项目演示"
)

