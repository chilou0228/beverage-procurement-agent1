from __future__ import annotations

from pathlib import Path
from datetime import date
import html
import math
import warnings

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

warnings.filterwarnings("ignore", category=FutureWarning)

# ============================================================
# 页面基础配置
# ============================================================
st.set_page_config(
    page_title="酒水采销经营驾驶舱",
    page_icon="🍷",
    layout="wide",
    initial_sidebar_state="expanded",
)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data" / "processed"

# ============================================================
# 全局视觉样式：白色工作台 + 珊瑚红强调色
# ============================================================
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Noto+Sans+SC:wght@400;500;600;700;800&display=swap');

    :root {
      --brand: #D94841;
      --brand-dark: #A92F2A;
      --brand-soft: #FFF1EF;
      --ink: #242A32;
      --muted: #7B8491;
      --line: #E9ECF1;
      --canvas: #F6F7F9;
      --white: #FFFFFF;
      --green: #16866A;
      --amber: #C8872B;
      --blue: #5278B8;
    }

    html, body, [class*="css"] {
      font-family: 'DM Sans', 'Noto Sans SC', sans-serif;
    }
    .stApp { background: var(--canvas); color: var(--ink); }
    [data-testid="stHeader"] { background: rgba(246,247,249,0.88); }
    [data-testid="stMainBlockContainer"] { padding-top: 1.55rem; padding-bottom: 3rem; max-width: 1500px; }

    /* Sidebar */
    [data-testid="stSidebar"] {
      background: #FFFFFF;
      border-right: 1px solid var(--line);
    }
    [data-testid="stSidebar"] > div:first-child { padding-top: 1.2rem; }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color: #66707D; }
    [data-testid="stSidebar"] [data-testid="stRadio"] label {
      border-radius: 10px;
      padding: 0.48rem 0.65rem;
      margin: 0.12rem 0;
      transition: all .18s ease;
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] label:hover { background: #FFF5F4; }
    [data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {
      background: #FFF0EE;
      color: #B93832;
      font-weight: 700;
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) p { color: #B93832 !important; }

    /* Inputs */
    div[data-baseweb="select"] > div, div[data-baseweb="input"] > div,
    div[data-baseweb="textarea"] > div {
      border-radius: 10px !important;
      border-color: #E2E6EC !important;
      background: #FFFFFF !important;
    }
    [data-testid="stDateInput"] input { border-radius: 10px !important; }
    .stSlider [data-baseweb="slider"] { padding-top: .35rem; }
    div.stButton > button {
      border-radius: 10px;
      border: 1px solid #D94841;
      background: #D94841;
      color: white;
      font-weight: 650;
      padding: .48rem 1rem;
      transition: all .18s ease;
    }
    div.stButton > button:hover {
      border-color: #A92F2A;
      background: #A92F2A;
      color: white;
      box-shadow: 0 5px 14px rgba(217,72,65,.18);
    }
    div.stDownloadButton > button {
      border-radius: 10px;
      border: 1px solid #E5B3AF;
      background: #FFFFFF;
      color: #B93832;
      font-weight: 600;
    }
    div.stDownloadButton > button:hover { border-color: #D94841; color: #A92F2A; }

    /* Tabs and dataframes */
    [data-testid="stTabs"] [data-baseweb="tab-list"] { gap: 1rem; border-bottom: 1px solid var(--line); }
    [data-testid="stTabs"] [data-baseweb="tab"] { color: #6F7885; font-weight: 600; }
    [data-testid="stTabs"] [aria-selected="true"] { color: #C63E37 !important; }
    [data-testid="stDataFrame"] {
      border: 1px solid var(--line);
      border-radius: 12px;
      overflow: hidden;
      background: white;
    }
    [data-testid="stAlert"] { border-radius: 12px; }
    hr { border-color: var(--line); }

    /* Custom components */
    .brand-lockup { display:flex; align-items:center; gap:10px; padding: 0.25rem 0 1.25rem 0; }
    .brand-mark {
      width: 38px; height: 38px; border-radius: 12px;
      background: linear-gradient(145deg,#E75A50,#B9322D);
      color: white; display:flex; align-items:center; justify-content:center;
      font-size: 19px; box-shadow: 0 5px 14px rgba(217,72,65,.22);
    }
    .brand-name { font-size: 15px; font-weight: 800; color: #252B33; letter-spacing: -.2px; }
    .brand-sub { color: #929AA5; font-size: 10px; letter-spacing: 1.15px; margin-top: 1px; }
    .side-label { color:#A0A7B1; font-size:10px; font-weight:800; letter-spacing:1.4px; margin: 1.1rem 0 .45rem .2rem; }

    .page-eyebrow { color:#C04A43; font-size:11px; font-weight:800; letter-spacing:1.7px; text-transform:uppercase; margin-bottom:5px; }
    .page-title { color:#222831; font-size:27px; font-weight:800; letter-spacing:-.9px; line-height:1.25; margin:0; }
    .page-desc { color:#7B8491; font-size:13px; margin-top:7px; line-height:1.65; }
    .hero {
      background: linear-gradient(112deg,#FFFFFF 0%,#FFF8F7 68%,#FDEAE7 100%);
      border:1px solid #F1E4E2; border-radius:18px; padding:21px 24px;
      margin: 0 0 19px 0; position:relative; overflow:hidden;
    }
    .hero:after {
      content:''; position:absolute; right:-36px; top:-72px; width:220px; height:220px;
      border-radius:50%; border:28px solid rgba(217,72,65,.055);
    }
    .hero-kicker { color:#C04A43; font-size:11px; letter-spacing:1.5px; font-weight:800; }
    .hero-title { font-size:25px; font-weight:800; color:#252A32; margin:7px 0 5px 0; letter-spacing:-.7px; }
    .hero-copy { color:#7C8490; font-size:12px; line-height:1.7; max-width:760px; }
    .hero-chip { display:inline-block; border-radius:20px; background:#FCE7E4; color:#AE3933; padding:5px 10px; font-size:10px; font-weight:700; margin-top:12px; }

    .section-head { display:flex; align-items:flex-end; justify-content:space-between; gap:12px; margin: 20px 0 11px 0; }
    .section-title { font-size:15px; font-weight:800; color:#2B313A; margin:0; }
    .section-sub { font-size:11px; color:#98A0AA; margin-top:4px; }
    .section-tag { background:#F0F2F5; color:#75808D; border-radius:20px; padding:4px 9px; font-size:10px; font-weight:700; }

    .metric-card {
      min-height:116px; background:#FFFFFF; border:1px solid #E9ECF1;
      border-radius:15px; padding:15px 16px 13px 16px; position:relative;
      box-shadow:0 2px 8px rgba(31,43,58,.025);
    }
    .metric-card:before { content:''; position:absolute; top:15px; left:0; width:3px; height:31px; border-radius:0 4px 4px 0; background:var(--accent,#D94841); }
    .metric-label { color:#818A96; font-size:11px; font-weight:650; margin-bottom:9px; }
    .metric-value { color:#252B33; font-size:24px; font-weight:800; line-height:1.15; letter-spacing:-.6px; font-variant-numeric:tabular-nums; }
    .metric-note { color:#A0A7B1; font-size:10px; margin-top:8px; }
    .metric-icon { position:absolute; right:13px; top:12px; width:29px; height:29px; border-radius:9px; display:flex; align-items:center; justify-content:center; background:var(--tint,#FFF0EE); color:var(--accent,#D94841); font-size:14px; }

    .panel { background:#FFFFFF; border:1px solid #E9ECF1; border-radius:15px; padding:15px 17px; box-shadow:0 2px 8px rgba(31,43,58,.02); }
    .insight { background:#FFFFFF; border:1px solid #E9ECF1; border-radius:13px; padding:13px 15px; min-height:83px; }
    .insight-label { color:#929AA5; font-size:10px; font-weight:700; margin-bottom:6px; }
    .insight-value { color:#303741; font-size:14px; font-weight:800; line-height:1.45; }
    .insight-copy { color:#929AA5; font-size:10px; margin-top:4px; }
    .status-pill { display:inline-block; padding:4px 9px; border-radius:16px; font-size:10px; font-weight:800; }
    .status-good { background:#E8F5F0; color:#16866A; }
    .status-warn { background:#FFF4E4; color:#B7791F; }
    .status-bad { background:#FDEBE9; color:#C7443D; }
    .status-neutral { background:#EFF1F4; color:#75808D; }
    .notice { background:#FFF8F1; border:1px solid #F3E3CC; color:#8B6A3D; border-radius:11px; padding:10px 13px; font-size:11px; line-height:1.65; }
    .footer-note { color:#A5ACB5; font-size:10px; border-top:1px solid #E9ECF1; padding-top:13px; margin-top:28px; line-height:1.7; }
    .empty-state { background:#FFFFFF; border:1px dashed #DDE2E8; border-radius:14px; padding:24px; text-align:center; color:#89929D; font-size:12px; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# 数据读取与通用工具
# ============================================================
@st.cache_data(ttl=300, show_spinner=False)
def read_csv_file(file_name: str) -> pd.DataFrame:
    path = DATA_DIR / file_name
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path, low_memory=False)
    except Exception as exc:
        st.warning(f"读取 {file_name} 失败：{exc}")
        return pd.DataFrame()


def as_numeric(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    out = df.copy()
    for col in cols:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")
    return out


def money(value: float | int | None, compact: bool = False) -> str:
    if value is None or pd.isna(value):
        return "—"
    value = float(value)
    if compact:
        if abs(value) >= 100_000_000:
            return f"¥{value / 100_000_000:,.2f}亿"
        if abs(value) >= 10_000:
            return f"¥{value / 10_000:,.1f}万"
    return f"¥{value:,.2f}"


def number(value: float | int | None, digits: int = 0) -> str:
    if value is None or pd.isna(value):
        return "—"
    return f"{float(value):,.{digits}f}"


def percent(value: float | int | None, digits: int = 1) -> str:
    if value is None or pd.isna(value):
        return "—"
    return f"{float(value) * 100:.{digits}f}%"


def safe_div(a: float, b: float) -> float:
    return float(a / b) if b and not pd.isna(b) else np.nan


def section(title: str, subtitle: str = "", tag: str = "") -> None:
    tag_html = f'<span class="section-tag">{html.escape(tag)}</span>' if tag else ""
    st.markdown(
        f'<div class="section-head"><div><div class="section-title">{html.escape(title)}</div>'
        f'<div class="section-sub">{html.escape(subtitle)}</div></div>{tag_html}</div>',
        unsafe_allow_html=True,
    )


def page_header(eyebrow: str, title: str, desc: str) -> None:
    st.markdown(
        f'<div style="margin-bottom:17px"><div class="page-eyebrow">{html.escape(eyebrow)}</div>'
        f'<h1 class="page-title">{html.escape(title)}</h1>'
        f'<div class="page-desc">{html.escape(desc)}</div></div>',
        unsafe_allow_html=True,
    )


def metric_card(label: str, value: str, note: str = "", icon: str = "•", accent: str = "#D94841", tint: str = "#FFF0EE") -> None:
    st.markdown(
        f'<div class="metric-card" style="--accent:{accent};--tint:{tint}">'
        f'<div class="metric-icon">{html.escape(icon)}</div>'
        f'<div class="metric-label">{html.escape(label)}</div>'
        f'<div class="metric-value">{html.escape(value)}</div>'
        f'<div class="metric-note">{html.escape(note)}</div></div>',
        unsafe_allow_html=True,
    )


def insight_card(label: str, value: str, copy: str = "") -> None:
    st.markdown(
        f'<div class="insight"><div class="insight-label">{html.escape(label)}</div>'
        f'<div class="insight-value">{html.escape(value)}</div>'
        f'<div class="insight-copy">{html.escape(copy)}</div></div>',
        unsafe_allow_html=True,
    )


def empty_state(message: str) -> None:
    st.markdown(f'<div class="empty-state">{html.escape(message)}</div>', unsafe_allow_html=True)


def polish_fig(fig: go.Figure, height: int = 330) -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(l=8, r=8, t=20, b=8),
        paper_bgcolor="rgba(255,255,255,0)",
        plot_bgcolor="rgba(255,255,255,0)",
        font=dict(family="DM Sans, Noto Sans SC, sans-serif", color="#6F7885", size=11),
        title_font=dict(size=14, color="#303741"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=10)),
        hoverlabel=dict(bgcolor="#252B33", font_color="white", bordercolor="#252B33"),
    )
    fig.update_xaxes(showgrid=False, linecolor="#E9ECF1", tickfont=dict(size=10), title=None)
    fig.update_yaxes(showgrid=True, gridcolor="#F0F2F5", zeroline=False, tickfont=dict(size=10), title=None)
    return fig


def show_table(df: pd.DataFrame, height: int = 370) -> None:
    if df.empty:
        empty_state("当前筛选条件下暂无数据")
    else:
        st.dataframe(df, use_container_width=True, hide_index=True, height=height)


def download_csv(df: pd.DataFrame, filename: str, label: str = "导出 CSV") -> None:
    if not df.empty:
        st.download_button(
            label=label,
            data=df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig"),
            file_name=filename,
            mime="text/csv",
        )


def status_style(value: str) -> str:
    text = str(value).lower()
    if any(x in text for x in ["正常", "维持主供", "稳定", "完成", "a级", "b级"]):
        return "status-good"
    if any(x in text for x in ["关注", "考虑", "谨慎", "预警", "待观察"]):
        return "status-warn"
    if any(x in text for x in ["风险", "缺货", "淘汰", "低于成本", "d级"]):
        return "status-bad"
    return "status-neutral"


# Load all supported project tables.
products = read_csv_file("products.csv")
sales = read_csv_file("sales_daily.csv")
inventory = read_csv_file("inventory_snapshot.csv")
batches = read_csv_file("inventory_batches.csv")
suppliers = read_csv_file("suppliers.csv")
supplier_ratings = read_csv_file("supplier_ratings_v2.csv")
supplier_strategies = read_csv_file("supplier_strategies.csv")
backup_recs = read_csv_file("backup_supplier_recommendations.csv")
competitors = read_csv_file("competitor_prices.csv")
promotions = read_csv_file("promotions.csv")
promotion_details = read_csv_file("promotion_details.csv")
product_supplier = read_csv_file("product_supplier_mapping.csv")
purchase_orders = read_csv_file("purchase_orders.csv")
receipts = read_csv_file("purchase_receipts.csv")

if not sales.empty and "date" in sales.columns:
    sales["date"] = pd.to_datetime(sales["date"], errors="coerce")
if not products.empty and "sku_id" in products.columns:
    products["sku_id"] = products["sku_id"].astype(str)
if not sales.empty and "sku_id" in sales.columns:
    sales["sku_id"] = sales["sku_id"].astype(str)
for df_name in ["inventory", "batches", "competitors", "product_supplier", "backup_recs", "promotion_details"]:
    df_obj = globals()[df_name]
    if not df_obj.empty and "sku_id" in df_obj.columns:
        df_obj["sku_id"] = df_obj["sku_id"].astype(str)

# ============================================================
# 侧边栏导航与全局筛选
# ============================================================
PAGES = [
    "经营总览",
    "品类经营",
    "SKU 诊断",
    "库存健康",
    "供应商管理",
    "备选供应商",
    "竞品价格",
    "促销测算",
    "经营助手",
    "数据说明",
]

with st.sidebar:
    st.markdown(
        '<div class="brand-lockup"><div class="brand-mark">🍷</div><div>'
        '<div class="brand-name">酒水采销驾驶舱</div><div class="brand-sub">BEVERAGE INTELLIGENCE</div>'
        '</div></div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="side-label">WORKSPACE</div>', unsafe_allow_html=True)
    current_page = st.radio("导航菜单", PAGES, label_visibility="collapsed")
    st.markdown('<div class="side-label">GLOBAL FILTERS</div>', unsafe_allow_html=True)

    category_options = []
    if not products.empty and "category_name" in products.columns:
        category_options = sorted(products["category_name"].dropna().astype(str).unique().tolist())
    elif not sales.empty and "category_name" in sales.columns:
        category_options = sorted(sales["category_name"].dropna().astype(str).unique().tolist())
    selected_categories = st.multiselect("商品品类", category_options, default=category_options, placeholder="选择品类")

    min_day = max_day = None
    if not sales.empty and "date" in sales.columns and sales["date"].notna().any():
        min_day = sales["date"].min().date()
        max_day = sales["date"].max().date()
    if min_day and max_day:
        date_range = st.date_input("分析周期", value=(min_day, max_day), min_value=min_day, max_value=max_day)
    else:
        date_range = ()

    st.divider()
    st.markdown("**演示环境**")
    st.caption("规则驱动 · 模拟业务数据 · 本地 CSV")
    loaded_files = sum(not x.empty for x in [products, sales, inventory, supplier_ratings, competitors, promotion_details])
    st.markdown(f"<span class='status-pill status-good'>{loaded_files}/6 核心数据表已加载</span>", unsafe_allow_html=True)
    st.caption("数据截止日期以各数据表记录为准。")

# Global filtered data
sales_filtered = sales.copy()
if not sales_filtered.empty:
    if selected_categories and "category_name" in sales_filtered.columns:
        sales_filtered = sales_filtered[sales_filtered["category_name"].astype(str).isin(selected_categories)]
    if len(date_range) == 2 and "date" in sales_filtered.columns:
        sales_filtered = sales_filtered[
            (sales_filtered["date"].dt.date >= date_range[0]) &
            (sales_filtered["date"].dt.date <= date_range[1])
        ]

products_filtered = products.copy()
if not products_filtered.empty and selected_categories and "category_name" in products_filtered.columns:
    products_filtered = products_filtered[products_filtered["category_name"].astype(str).isin(selected_categories)]

# ============================================================
# 页面 1：经营总览
# ============================================================
if current_page == "经营总览":
    st.markdown(
        '<div class="hero"><div class="hero-kicker">BEVERAGE BUSINESS OVERVIEW</div>'
        '<div class="hero-title">让每一项采销决策，都有数据依据。</div>'
        '<div class="hero-copy">覆盖销售表现、品类结构、库存健康与采购协同的经营分析工作台。'
        '通过统一的数据视图，快速识别增长机会、利润空间与供应链风险。</div>'
        '<span class="hero-chip">● 规则驱动决策辅助 · 非实时交易系统</span></div>',
        unsafe_allow_html=True,
    )

    if sales_filtered.empty:
        st.warning("没有可用于总览的数据。请确认 data/processed/sales_daily.csv 已上传到项目仓库。")
    else:
        d = as_numeric(sales_filtered, ["revenue", "gross_profit", "sales_volume", "visitors", "orders"])
        revenue = d["revenue"].sum() if "revenue" in d else 0
        gross_profit = d["gross_profit"].sum() if "gross_profit" in d else 0
        volume = d["sales_volume"].sum() if "sales_volume" in d else 0
        visitors = d["visitors"].sum() if "visitors" in d else 0
        orders = d["orders"].sum() if "orders" in d else 0
        margin = safe_div(gross_profit, revenue)
        cvr = safe_div(orders, visitors)
        a, b, c, e = st.columns(4)
        with a: metric_card("累计销售额", money(revenue, True), "筛选周期内商品销售收入", "↗", "#D94841", "#FFF0EE")
        with b: metric_card("累计毛利", money(gross_profit, True), "销售额减商品采购成本", "◆", "#16866A", "#EAF6F1")
        with c: metric_card("综合毛利率", percent(margin), "毛利 / 销售额", "%", "#5278B8", "#EEF3FB")
        with e: metric_card("销售件数", number(volume), "按销售明细数量汇总", "▤", "#C8872B", "#FFF6E8")

        a, b, c, e = st.columns(4)
        with a: metric_card("访客量", number(visitors), "销售明细记录的访客汇总", "◎", "#5278B8", "#EEF3FB")
        with b: metric_card("订单量（模拟口径）", number(orders), "由模拟销售数据生成", "▣", "#8B6DB0", "#F5F0FA")
        with c: metric_card("访客成交率", percent(cvr, 2), "订单量 / 访客量", "⌁", "#16866A", "#EAF6F1")
        with e: metric_card("覆盖 SKU", number(d["sku_id"].nunique() if "sku_id" in d else 0), "筛选周期内有销售记录的 SKU", "◇", "#C8872B", "#FFF6E8")

        st.markdown("")
        left, right = st.columns([1.65, 1])
        with left:
            section("销售趋势", "按日观察销售额与毛利变化", "DAILY TREND")
            if "date" in d.columns and "revenue" in d.columns:
                trend = d.groupby("date", as_index=False).agg(revenue=("revenue", "sum"), gross_profit=("gross_profit", "sum"))
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=trend["date"], y=trend["revenue"], name="销售额", mode="lines", line=dict(color="#D94841", width=2.5), fill="tozeroy", fillcolor="rgba(217,72,65,.07)"))
                fig.add_trace(go.Scatter(x=trend["date"], y=trend["gross_profit"], name="毛利", mode="lines", line=dict(color="#D9A04A", width=2)))
                polish_fig(fig, 330)
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
            else:
                empty_state("销售趋势字段不完整")
        with right:
            section("品类销售贡献", "销售额排名前 6 的品类", "CATEGORY MIX")
            if "category_name" in d.columns and "revenue" in d.columns:
                mix = d.groupby("category_name", as_index=False)["revenue"].sum().sort_values("revenue", ascending=False).head(6)
                fig = px.pie(mix, names="category_name", values="revenue", hole=.68, color_discrete_sequence=["#D94841", "#E98A75", "#E8B66C", "#6D8DBD", "#8CB8A6", "#B5A2C9"])
                fig.update_traces(textposition="inside", textinfo="percent", marker=dict(line=dict(color="white", width=3)))
                polish_fig(fig, 330)
                fig.update_layout(showlegend=True, legend=dict(orientation="v", x=1.02, y=.5))
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
            else:
                empty_state("暂无品类维度数据")

        section("经营观察", "基于当前筛选结果生成的描述性指标")
        i1, i2, i3 = st.columns(3)
        if "category_name" in d.columns and "revenue" in d.columns:
            cat = d.groupby("category_name")["revenue"].sum().sort_values(ascending=False)
            top_cat = str(cat.index[0]) if not cat.empty else "暂无"
            top_share = safe_div(float(cat.iloc[0]), revenue) if not cat.empty else np.nan
        else:
            top_cat, top_share = "暂无", np.nan
        if "sku_id" in d.columns and "gross_profit" in d.columns:
            sku_gp = d.groupby("sku_id")["gross_profit"].sum().sort_values(ascending=False)
            top_sku = str(sku_gp.index[0]) if not sku_gp.empty else "暂无"
        else:
            top_sku = "暂无"
        with i1: insight_card("销售额贡献最高品类", top_cat, f"品类销售额占比 {percent(top_share)}")
        with i2: insight_card("毛利贡献最高 SKU", top_sku, "按筛选周期累计毛利排序")
        with i3: insight_card("数据覆盖周期", f"{len(d):,} 条销售明细", f"{d['sku_id'].nunique() if 'sku_id' in d else 0} 个 SKU 参与统计")

        st.markdown('<div class="notice">口径提示：此处毛利按销售额减商品采购成本计算，未扣除平台佣金、物流、营销及其他经营费用；订单量与转化率属于模拟数据口径，不代表真实平台经营结果。</div>', unsafe_allow_html=True)

# ============================================================
# 页面 2：品类经营
# ============================================================
elif current_page == "品类经营":
    page_header("CATEGORY PERFORMANCE", "品类经营分析", "从销售规模、毛利贡献和转化表现三个维度，比较不同酒类品类的经营结构。")
    if sales_filtered.empty or "category_name" not in sales_filtered.columns:
        empty_state("缺少销售数据或品类字段。")
    else:
        d = as_numeric(sales_filtered, ["revenue", "gross_profit", "sales_volume", "visitors", "orders"])
        agg_dict = {}
        for col in ["revenue", "gross_profit", "sales_volume", "visitors", "orders"]:
            if col in d.columns: agg_dict[col] = (col, "sum")
        summary = d.groupby("category_name", as_index=False).agg(**agg_dict)
        summary["gross_margin"] = summary.apply(lambda r: safe_div(r.get("gross_profit", 0), r.get("revenue", 0)), axis=1)
        summary["conversion_rate"] = summary.apply(lambda r: safe_div(r.get("orders", 0), r.get("visitors", 0)), axis=1)
        summary = summary.sort_values("revenue", ascending=False)
        total_rev = summary["revenue"].sum() if "revenue" in summary else 0
        cols = st.columns(4)
        with cols[0]: metric_card("覆盖品类", number(len(summary)), "当前筛选范围", "▦")
        with cols[1]: metric_card("品类销售额", money(total_rev, True), "全部可见品类合计", "↗", "#D94841")
        with cols[2]: metric_card("平均毛利率", percent(summary["gross_profit"].sum() / total_rev if total_rev else np.nan), "按销售额加权", "%", "#16866A", "#EAF6F1")
        with cols[3]: metric_card("销售件数", number(summary["sales_volume"].sum() if "sales_volume" in summary else 0), "按销售数量汇总", "▤", "#5278B8", "#EEF3FB")
        section("品类销售额对比", "识别主要销售贡献来源")
        fig = px.bar(summary.sort_values("revenue"), x="revenue", y="category_name", orientation="h", text_auto=".3s", color="revenue", color_continuous_scale=["#F8D9D5", "#D94841"])
        fig.update_layout(coloraxis_showscale=False)
        polish_fig(fig, 370)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        section("品类经营明细", "可导出当前筛选范围的品类汇总表")
        display = summary.rename(columns={"category_name":"品类", "revenue":"销售额（元）", "gross_profit":"毛利（元）", "sales_volume":"销售件数", "visitors":"访客量", "orders":"订单量（模拟）", "gross_margin":"毛利率", "conversion_rate":"访客成交率"})
        for col in ["销售额（元）", "毛利（元）"]:
            if col in display: display[col] = display[col].map(lambda x: f"¥{x:,.2f}")
        for col in ["毛利率", "访客成交率"]:
            if col in display: display[col] = display[col].map(percent)
        show_table(display, 420)
        download_csv(summary, "category_performance.csv", "下载品类汇总")

# ============================================================
# 页面 3：SKU 诊断
# ============================================================
elif current_page == "SKU 诊断":
    page_header("SKU DEEP DIVE", "单品经营诊断", "围绕单个 SKU 查看销售趋势、库存状态、竞品价格与供应商配置，辅助定位单品经营问题。")
    if products_filtered.empty or "sku_id" not in products_filtered.columns:
        empty_state("缺少商品档案 products.csv，无法进行 SKU 诊断。")
    else:
        p = products_filtered.copy()
        p["sku_id"] = p["sku_id"].astype(str)
        p["display_name"] = p.get("product_name", p["sku_id"]).astype(str) + "  ·  " + p["sku_id"]
        selected_label = st.selectbox("选择商品", p["display_name"].tolist())
        selected_sku = p.loc[p["display_name"] == selected_label, "sku_id"].iloc[0]
        product_row = p[p["sku_id"] == selected_sku].iloc[0]
        product_sales = sales_filtered[sales_filtered["sku_id"] == selected_sku].copy() if not sales_filtered.empty and "sku_id" in sales_filtered else pd.DataFrame()
        product_sales = as_numeric(product_sales, ["revenue", "gross_profit", "sales_volume", "visitors", "orders"])
        sku_rev = product_sales["revenue"].sum() if "revenue" in product_sales else 0
        sku_gp = product_sales["gross_profit"].sum() if "gross_profit" in product_sales else 0
        sku_qty = product_sales["sales_volume"].sum() if "sales_volume" in product_sales else 0
        inv_row = inventory[inventory["sku_id"].astype(str) == selected_sku].iloc[0] if not inventory.empty and "sku_id" in inventory and (inventory["sku_id"].astype(str) == selected_sku).any() else None

        st.markdown(f"<div class='panel' style='margin:8px 0 15px 0'><div style='font-size:11px;color:#929AA5;font-weight:700'>{html.escape(str(product_row.get('category_name','未分类')))} / {html.escape(str(product_row.get('subcategory','')))}</div><div style='font-size:20px;font-weight:800;color:#252B33;margin:5px 0'>{html.escape(str(product_row.get('product_name',selected_sku)))}</div><div style='font-size:11px;color:#858E99'>SKU：{html.escape(selected_sku)}　·　品牌：{html.escape(str(product_row.get('brand','—')))}　·　规格：{html.escape(str(product_row.get('specification','—')))}</div></div>", unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns(4)
        with c1: metric_card("筛选期销售额", money(sku_rev, True), "商品销售收入", "↗")
        with c2: metric_card("筛选期毛利", money(sku_gp, True), "未扣其他经营费用", "◆", "#16866A", "#EAF6F1")
        with c3: metric_card("销售件数", number(sku_qty), "销售明细合计", "▤", "#5278B8", "#EEF3FB")
        with c4: metric_card("当前商品售价", money(product_row.get("selling_price")), "商品档案标价", "￥", "#C8872B", "#FFF6E8")

        left, right = st.columns([1.55, 1])
        with left:
            section("单品销售趋势", "按日观察该 SKU 销售额与销量")
            if not product_sales.empty and "date" in product_sales and "revenue" in product_sales:
                trend = product_sales.groupby("date", as_index=False).agg(revenue=("revenue", "sum"), sales_volume=("sales_volume", "sum"))
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=trend["date"], y=trend["revenue"], name="销售额", mode="lines", line=dict(color="#D94841", width=2.5), fill="tozeroy", fillcolor="rgba(217,72,65,.07)"))
                polish_fig(fig, 300)
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
            else: empty_state("当前 SKU 在筛选周期内没有销售记录")
        with right:
            section("库存与商品信息", "当前库存快照")
            if inv_row is not None:
                inv_cov = inv_row.get("inventory_coverage_days", np.nan)
                st.markdown(f"<div class='panel'><div style='display:flex;justify-content:space-between;padding:7px 0;border-bottom:1px solid #F0F2F5'><span style='color:#89929D;font-size:11px'>可用库存</span><b>{number(inv_row.get('available_stock'))} 件</b></div><div style='display:flex;justify-content:space-between;padding:7px 0;border-bottom:1px solid #F0F2F5'><span style='color:#89929D;font-size:11px'>在途库存</span><b>{number(inv_row.get('on_order_stock'))} 件</b></div><div style='display:flex;justify-content:space-between;padding:7px 0;border-bottom:1px solid #F0F2F5'><span style='color:#89929D;font-size:11px'>安全库存</span><b>{number(inv_row.get('safety_stock'))} 件</b></div><div style='display:flex;justify-content:space-between;padding:7px 0'><span style='color:#89929D;font-size:11px'>库存覆盖天数</span><b style='color:#D94841'>{number(inv_cov,1)} 天</b></div></div>", unsafe_allow_html=True)
            else:
                st.info("库存快照中未找到该 SKU。")
            st.caption(f"采购成本：{money(product_row.get('purchase_cost'))}　|　商品毛利率：{percent(product_row.get('gross_margin'))}")

        t1, t2, t3 = st.tabs(["竞品价格", "供应商配置", "促销记录"])
        with t1:
            comp = competitors[competitors["sku_id"].astype(str) == selected_sku].copy() if not competitors.empty and "sku_id" in competitors else pd.DataFrame()
            if not comp.empty:
                view_cols = [c for c in ["competitor_name", "competitor_brand", "competitor_channel", "competitor_price", "price_type", "price_position"] if c in comp]
                comp_show = comp[view_cols].rename(columns={"competitor_name":"竞品名称", "competitor_brand":"竞品品牌（模拟）", "competitor_channel":"渠道", "competitor_price":"竞品价格", "price_type":"价格类型", "price_position":"价格位置"})
                show_table(comp_show, 250)
            else: empty_state("没有该 SKU 的竞品价格记录")
        with t2:
            mapping = product_supplier[product_supplier["sku_id"].astype(str) == selected_sku].copy() if not product_supplier.empty and "sku_id" in product_supplier else pd.DataFrame()
            if not mapping.empty:
                cols = [c for c in ["supplier_name", "supplier_level", "is_primary", "supplier_quote_cost", "avg_lead_time_days", "supplier_status"] if c in mapping]
                show_table(mapping[cols].rename(columns={"supplier_name":"供应商", "supplier_level":"供应商层级", "is_primary":"是否主供", "supplier_quote_cost":"报价成本", "avg_lead_time_days":"平均交期（天）", "supplier_status":"合作状态"}), 240)
            else: empty_state("没有找到该 SKU 的供应商映射")
        with t3:
            promo = promotion_details[promotion_details["sku_id"].astype(str) == selected_sku].copy() if not promotion_details.empty and "sku_id" in promotion_details else pd.DataFrame()
            if not promo.empty:
                cols = [c for c in ["promotion_id", "discount_rate", "promotion_price", "promotion_gross_margin", "target_quantity", "profit_warning", "data_type"] if c in promo]
                show_table(promo[cols].rename(columns={"promotion_id":"促销活动", "discount_rate":"折扣率", "promotion_price":"促销价", "promotion_gross_margin":"促销毛利率", "target_quantity":"目标销量", "profit_warning":"利润提示", "data_type":"数据类型"}), 240)
            else: empty_state("没有该 SKU 的促销明细")

# ============================================================
# 页面 4：库存健康
# ============================================================
elif current_page == "库存健康":
    page_header("INVENTORY HEALTH", "库存健康与风险预警", "基于库存快照与库存覆盖天数，识别潜在缺货、库存偏高和需要优先关注的商品。")
    if inventory.empty:
        empty_state("缺少 inventory_snapshot.csv。请将库存数据文件一并上传到 GitHub。")
    else:
        inv = inventory.copy()
        inv = as_numeric(inv, ["available_stock", "safety_stock", "on_order_stock", "inventory_coverage_days", "inventory_cost", "avg_daily_sales_30d"])
        if selected_categories and "category_name" in inv:
            inv = inv[inv["category_name"].astype(str).isin(selected_categories)]
        cov = inv.get("inventory_coverage_days", pd.Series(dtype=float))
        inv["risk_status"] = np.select([cov <= 7, cov <= 15, cov >= 75], ["紧急缺货风险", "库存偏低", "库存偏高"], default="库存正常")
        shortage = int((inv["risk_status"] == "紧急缺货风险").sum())
        low = int((inv["risk_status"] == "库存偏低").sum())
        high = int((inv["risk_status"] == "库存偏高").sum())
        c1,c2,c3,c4 = st.columns(4)
        with c1: metric_card("库存 SKU", number(len(inv)), "库存快照商品数", "▤")
        with c2: metric_card("库存总量", number(inv["available_stock"].sum() if "available_stock" in inv else 0), "可用库存件数", "▦", "#5278B8", "#EEF3FB")
        with c3: metric_card("紧急缺货风险", number(shortage), "覆盖天数 ≤ 7 天", "!", "#D94841", "#FFF0EE")
        with c4: metric_card("库存偏高", number(high), "覆盖天数 ≥ 75 天", "◷", "#C8872B", "#FFF6E8")

        left, right = st.columns([1.1, 1.5])
        with left:
            section("库存风险分布", "按库存覆盖天数划分")
            risk_counts = inv["risk_status"].value_counts().reindex(["紧急缺货风险", "库存偏低", "库存正常", "库存偏高"], fill_value=0).reset_index()
            risk_counts.columns = ["风险状态", "SKU 数量"]
            fig = px.pie(risk_counts, names="风险状态", values="SKU 数量", hole=.65, color="风险状态", color_discrete_map={"紧急缺货风险":"#D94841", "库存偏低":"#E9A24B", "库存正常":"#78B69C", "库存偏高":"#8A9DBB"})
            fig.update_traces(textinfo="label+value", textposition="outside")
            polish_fig(fig, 310)
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        with right:
            section("库存覆盖天数分布", "观察库存结构是否集中在特定区间")
            if "inventory_coverage_days" in inv:
                fig = px.histogram(inv, x="inventory_coverage_days", nbins=18, color_discrete_sequence=["#D96A61"])
                fig.update_traces(marker_line_width=0)
                polish_fig(fig, 310)
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        section("库存风险商品清单", "优先关注缺货风险与高库存商品", "ACTION LIST")
        risk_filter = st.selectbox("风险类型", ["全部风险", "紧急缺货风险", "库存偏低", "库存正常", "库存偏高"])
        risk_view = inv if risk_filter == "全部风险" else inv[inv["risk_status"] == risk_filter]
        risk_view = risk_view.sort_values("inventory_coverage_days", ascending=True)
        cols = [c for c in ["sku_id", "product_name", "category_name", "brand", "available_stock", "safety_stock", "on_order_stock", "inventory_coverage_days", "inventory_cost", "risk_status"] if c in risk_view]
        display = risk_view[cols].rename(columns={"sku_id":"SKU", "product_name":"商品名称", "category_name":"品类", "brand":"品牌", "available_stock":"可用库存", "safety_stock":"安全库存", "on_order_stock":"在途库存", "inventory_coverage_days":"覆盖天数", "inventory_cost":"库存成本（元）", "risk_status":"风险等级"})
        show_table(display, 430)
        download_csv(risk_view, "inventory_risk_list.csv", "下载库存风险清单")
        if not batches.empty:
            with st.expander("查看批次与效期信息"):
                batch_view = batches.copy()
                if selected_categories and "category_name" in batch_view:
                    batch_view = batch_view[batch_view["category_name"].astype(str).isin(selected_categories)]
                batch_cols = [c for c in ["batch_id", "sku_id", "product_name", "category_name", "production_date", "expiry_date", "remaining_quantity", "batch_inventory_cost"] if c in batch_view]
                show_table(batch_view[batch_cols], 300)

# ============================================================
# 页面 5：供应商管理
# ============================================================
elif current_page == "供应商管理":
    page_header("SUPPLIER MANAGEMENT", "供应商绩效与合作策略", "综合交付、准时性与订单完成情况，查看供应商评分、分级和建议管理策略。")
    if supplier_ratings.empty:
        empty_state("缺少 supplier_ratings_v2.csv。请检查文件是否已上传。")
    else:
        sr = supplier_ratings.copy()
        if selected_categories and "main_category" in sr:
            sr = sr[sr["main_category"].astype(str).isin(selected_categories)]
        sr = as_numeric(sr, ["total_score", "fulfillment_rate", "on_time_delivery_rate", "order_completion_rate", "due_order_count", "due_quantity", "due_received_quantity"])
        c1,c2,c3,c4 = st.columns(4)
        avg_score = sr["total_score"].mean() if "total_score" in sr else np.nan
        with c1: metric_card("供应商数量", number(len(sr)), "当前筛选范围", "♧")
        with c2: metric_card("平均综合评分", number(avg_score,1), "评分满分 100", "★", "#5278B8", "#EEF3FB")
        with c3: metric_card("A级 / B级", number(sr["supplier_grade"].isin(["A", "B"]).sum() if "supplier_grade" in sr else 0), "高等级供应商数", "◆", "#16866A", "#EAF6F1")
        with c4: metric_card("待观察供应商", number((sr["evaluation_status"] == "待观察").sum() if "evaluation_status" in sr else 0), "样本不足或暂无有效评分", "◷", "#C8872B", "#FFF6E8")

        left, right = st.columns([1, 1.5])
        with left:
            section("供应商等级分布", "按综合评级统计")
            if "supplier_grade" in sr:
                grades = sr["supplier_grade"].fillna("未评级").value_counts().reindex(["A", "B", "C", "D", "未评级"], fill_value=0).reset_index()
                grades.columns = ["等级", "数量"]
                fig = px.bar(grades, x="等级", y="数量", text="数量", color="等级", color_discrete_map={"A":"#16866A", "B":"#82B99E", "C":"#E8B15E", "D":"#D94841", "未评级":"#A8AFB8"})
                fig.update_layout(showlegend=False)
                polish_fig(fig, 290)
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        with right:
            section("供应商评分分布", "比较综合评分与交付表现")
            if all(c in sr for c in ["total_score", "fulfillment_rate", "supplier_name"]):
                fig = px.scatter(sr, x="fulfillment_rate", y="total_score", color="supplier_grade" if "supplier_grade" in sr else None, hover_name="supplier_name", size="due_order_count" if "due_order_count" in sr else None, color_discrete_sequence=["#D94841", "#D9A04A", "#6E91BD", "#86B59C"])
                fig.update_xaxes(tickformat=".0%")
                polish_fig(fig, 290)
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        if not supplier_strategies.empty:
            merged = sr.merge(supplier_strategies, on="supplier_id", how="left", suffixes=("", "_strategy")) if "supplier_id" in sr and "supplier_id" in supplier_strategies else sr.copy()
        else:
            merged = sr.copy()
        section("供应商绩效清单", "评分结果与采购合作建议")
        search = st.text_input("搜索供应商", placeholder="输入供应商名称或编号")
        if search:
            mask = pd.Series(False, index=merged.index)
            for col in ["supplier_name", "supplier_id"]:
                if col in merged: mask |= merged[col].astype(str).str.contains(search, case=False, na=False)
            merged = merged[mask]
        cols = [c for c in ["supplier_id", "supplier_name", "main_category", "supplier_level", "total_score", "supplier_grade", "fulfillment_rate", "on_time_delivery_rate", "order_completion_rate", "cooperation_level", "purchase_priority", "risk_control_action", "management_advice"] if c in merged]
        show_table(merged[cols].rename(columns={"supplier_id":"供应商编号", "supplier_name":"供应商名称", "main_category":"主营品类", "supplier_level":"供应商层级", "total_score":"综合评分", "supplier_grade":"评级", "fulfillment_rate":"交付率", "on_time_delivery_rate":"准时交付率", "order_completion_rate":"订单完成率", "cooperation_level":"合作策略", "purchase_priority":"采购优先级", "risk_control_action":"风险控制", "management_advice":"管理建议"}), 440)
        download_csv(merged, "supplier_performance_and_strategy.csv", "下载供应商绩效表")
        st.markdown('<div class="notice">评分口径提示：当前评分来自项目设定的模拟采购订单与收货记录；订单是否到期、拆分收货及统计截止日期会影响交付率、准时率和完成率。该评分用于演示供应商管理逻辑，不代表真实供应商信用评价。</div>', unsafe_allow_html=True)

# ============================================================
# 页面 6：备选供应商
# ============================================================
elif current_page == "备选供应商":
    page_header("BACKUP SUPPLIER OPTIONS", "备选供应商决策", "将主供与备选供应商的综合评分、报价成本和交期进行横向比较，辅助评估替代可行性。")
    if backup_recs.empty:
        empty_state("缺少 backup_supplier_recommendations.csv。")
    else:
        rec = backup_recs.copy()
        if selected_categories and "category_name" in rec:
            rec = rec[rec["category_name"].astype(str).isin(selected_categories)]
        decision_col = "decision" if "decision" in rec else None
        counts = rec[decision_col].value_counts() if decision_col else pd.Series(dtype=int)
        c1,c2,c3,c4 = st.columns(4)
        with c1: metric_card("SKU 覆盖", number(len(rec)), "已建立主供/备选对比的商品", "▤")
        with c2: metric_card("维持主供", number(counts.get("维持主供", 0)), "当前主供仍具备综合优势", "✓", "#16866A", "#EAF6F1")
        with c3: metric_card("考虑备选", number(counts.get("考虑备选", 0)), "可进一步评估切换条件", "⇄", "#C8872B", "#FFF6E8")
        with c4: metric_card("暂无建议", number(counts.get("暂无建议", 0)), "信息不足或状态不满足条件", "—", "#5278B8", "#EEF3FB")

        section("建议分布", "各类供应商决策建议数量")
        if decision_col:
            dc = rec[decision_col].value_counts().reset_index(); dc.columns = ["决策建议", "SKU 数量"]
            fig = px.bar(dc, x="决策建议", y="SKU 数量", text="SKU 数量", color="决策建议", color_discrete_sequence=["#D94841", "#E7A64D", "#8A9DBB"])
            fig.update_layout(showlegend=False)
            polish_fig(fig, 280)
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        section("主供与备选对比清单", "支持按建议类型筛选并导出")
        choices = ["全部建议"] + sorted(rec[decision_col].dropna().astype(str).unique().tolist()) if decision_col else ["全部建议"]
        choice = st.selectbox("决策建议", choices)
        rec_view = rec if choice == "全部建议" or not decision_col else rec[rec[decision_col].astype(str) == choice]
        cols = [c for c in ["sku_id", "product_name", "category_name", "primary_supplier_name", "primary_supplier_score", "primary_quote_cost", "primary_lead_time_days", "backup_supplier_name", "backup_supplier_score", "backup_quote_cost", "backup_lead_time_days", "backup_cost_change_rate", "backup_lead_time_difference", "decision", "recommendation_reason"] if c in rec_view]
        display = rec_view[cols].rename(columns={"sku_id":"SKU", "product_name":"商品名称", "category_name":"品类", "primary_supplier_name":"主供供应商", "primary_supplier_score":"主供评分", "primary_quote_cost":"主供报价", "primary_lead_time_days":"主供交期（天）", "backup_supplier_name":"备选供应商", "backup_supplier_score":"备选评分", "backup_quote_cost":"备选报价", "backup_lead_time_days":"备选交期（天）", "backup_cost_change_rate":"备选成本变化率", "backup_lead_time_difference":"交期差异（天）", "decision":"决策建议", "recommendation_reason":"建议原因"})
        show_table(display, 440)
        download_csv(rec_view, "backup_supplier_recommendations.csv", "下载备选供应商建议")
        st.markdown('<div class="notice">决策建议是规则模型输出的辅助信息，不能直接替代采购合同、资质审核、质量验证、供应商产能确认与人工谈判；“考虑备选”不等于系统自动切换主供。</div>', unsafe_allow_html=True)

# ============================================================
# 页面 7：竞品价格
# ============================================================
elif current_page == "竞品价格":
    page_header("COMPETITIVE PRICE INTELLIGENCE", "竞品价格对标", "对比商品自身售价与模拟竞品报价，识别价格差距和可能需要复核的商品。")
    if competitors.empty:
        empty_state("缺少 competitor_prices.csv。")
    else:
        cp = competitors.copy()
        if selected_categories and "category_name" in cp:
            cp = cp[cp["category_name"].astype(str).isin(selected_categories)]
        cp = as_numeric(cp, ["competitor_price", "own_selling_price", "price_difference", "price_difference_rate"])
        c1,c2,c3,c4 = st.columns(4)
        with c1: metric_card("竞品报价记录", number(len(cp)), "模拟采集记录", "◎")
        with c2: metric_card("覆盖 SKU", number(cp["sku_id"].nunique() if "sku_id" in cp else 0), "存在竞品价格的商品", "▤", "#5278B8", "#EEF3FB")
        with c3: metric_card("低于自身售价", number((cp["competitor_price"] < cp["own_selling_price"]).sum() if all(c in cp for c in ["competitor_price","own_selling_price"]) else 0), "竞品价格更低的记录数", "↓", "#C8872B", "#FFF6E8")
        with c4: metric_card("竞品均价", money(cp["competitor_price"].mean() if "competitor_price" in cp else np.nan), "全部竞品记录均值", "￥", "#16866A", "#EAF6F1")

        if not products_filtered.empty and "sku_id" in products_filtered:
            sku_labels = products_filtered.copy()
            sku_labels["sku_id"] = sku_labels["sku_id"].astype(str)
            sku_labels["display_name"] = sku_labels.get("product_name", sku_labels["sku_id"]).astype(str) + " · " + sku_labels["sku_id"]
            selected = st.selectbox("选择 SKU 查看价格对比", sku_labels["display_name"].tolist(), key="competitor_sku")
            sku = sku_labels.loc[sku_labels["display_name"] == selected, "sku_id"].iloc[0]
            one = cp[cp["sku_id"].astype(str) == sku].copy()
            if not one.empty:
                own_price = one["own_selling_price"].iloc[0] if "own_selling_price" in one else np.nan
                section("单品价格对比", f"当前商品自身售价：{money(own_price)}")
                bar = one.copy()
                bar["对比对象"] = bar.get("competitor_name", bar.index.astype(str)).astype(str)
                bar = pd.concat([bar[["对比对象", "competitor_price"]].rename(columns={"competitor_price":"价格"}), pd.DataFrame([{"对比对象":"本商品售价", "价格":own_price}])], ignore_index=True)
                fig = px.bar(bar.sort_values("价格"), x="价格", y="对比对象", orientation="h", color="对比对象", color_discrete_sequence=["#D94841", "#E89A80", "#D8A34F", "#7895BD", "#8DB5A2"])
                fig.update_layout(showlegend=False)
                polish_fig(fig, 300)
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
                cols = [c for c in ["competitor_name", "competitor_brand", "competitor_channel", "competitor_price", "price_type", "price_position", "price_difference_rate"] if c in one]
                show_table(one[cols].rename(columns={"competitor_name":"竞品名称", "competitor_brand":"竞品品牌（模拟）", "competitor_channel":"渠道", "competitor_price":"竞品价", "price_type":"价格类型", "price_position":"相对位置", "price_difference_rate":"价差率"}), 240)
            else: empty_state("该 SKU 暂无竞品价格记录")
        else:
            empty_state("商品档案不可用，无法选择 SKU。")
        with st.expander("查看全部竞品价格记录"):
            cols = [c for c in ["sku_id", "product_name", "category_name", "competitor_name", "competitor_channel", "competitor_price", "own_selling_price", "price_difference", "price_position"] if c in cp]
            show_table(cp[cols], 360)
            download_csv(cp, "competitor_price_comparison.csv", "下载竞品价格数据")
        st.markdown('<div class="notice">数据说明：本项目竞品名称、竞品品牌、渠道及报价均为模拟数据，用于演示竞品价格监测和横向比较方法，不代表真实市场采集结果。</div>', unsafe_allow_html=True)

# ============================================================
# 页面 8：促销测算
# ============================================================
elif current_page == "促销测算":
    page_header("PROMOTION PROFIT SIMULATOR", "促销利润测算", "调整折扣率和预计销量，快速测算促销价、单件毛利、毛利率及活动毛利空间。")
    if products_filtered.empty:
        empty_state("缺少商品档案，无法进行促销测算。")
    else:
        p = products_filtered.copy()
        p["sku_id"] = p["sku_id"].astype(str)
        p["display_name"] = p.get("product_name", p["sku_id"]).astype(str) + " · " + p["sku_id"]
        selected = st.selectbox("选择测算商品", p["display_name"].tolist(), key="promotion_sku")
        sku = p.loc[p["display_name"] == selected, "sku_id"].iloc[0]
        pr = p[p["sku_id"] == sku].iloc[0]
        original_price = float(pr.get("selling_price", 0) or 0)
        cost = float(pr.get("purchase_cost", 0) or 0)

        left, right = st.columns([1, 1.25])
        with left:
            section("设置促销参数", "模型仅做静态毛利测算")
            st.markdown(f"<div class='panel'><div style='font-size:11px;color:#929AA5'>商品档案</div><div style='font-size:16px;font-weight:800;color:#2B313A;margin:5px 0 12px'>{html.escape(str(pr.get('product_name',sku)))}</div><div style='display:flex;justify-content:space-between;padding:8px 0;border-top:1px solid #F0F2F5'><span style='font-size:11px;color:#89929D'>日常售价</span><b>{money(original_price)}</b></div><div style='display:flex;justify-content:space-between;padding:8px 0;border-top:1px solid #F0F2F5'><span style='font-size:11px;color:#89929D'>采购成本</span><b>{money(cost)}</b></div></div>", unsafe_allow_html=True)
            discount = st.slider("促销折扣", min_value=0.50, max_value=1.00, value=0.90, step=0.01, format="%.0f%%")
            quantity = st.number_input("预计促销销量（件）", min_value=1, max_value=1_000_000, value=100, step=10)
            days = st.number_input("活动持续天数", min_value=1, max_value=90, value=7, step=1)
        promo_price = original_price * discount
        unit_profit = promo_price - cost
        promo_margin = safe_div(unit_profit, promo_price)
        original_profit = original_price - cost
        original_total_gp = original_profit * quantity
        promo_total_gp = unit_profit * quantity
        promo_revenue = promo_price * quantity
        delta_gp = promo_total_gp - original_total_gp
        with right:
            section("测算结果", "促销价格与利润空间")
            c1,c2 = st.columns(2)
            with c1: metric_card("促销成交价", money(promo_price), f"原价的 {percent(discount)}", "￥")
            with c2: metric_card("单件毛利", money(unit_profit), "促销价 - 采购成本", "◆", "#16866A", "#EAF6F1")
            c1,c2 = st.columns(2)
            with c1: metric_card("促销毛利率", percent(promo_margin), "单件毛利 / 促销价", "%", "#5278B8", "#EEF3FB")
            with c2: metric_card("预计活动毛利", money(promo_total_gp, True), f"预计销售 {number(quantity)} 件", "↗", "#C8872B", "#FFF6E8")
            fig = go.Figure(go.Bar(x=["日常售价", "促销成交价"], y=[original_price, promo_price], marker_color=["#AAB4C1", "#D94841"], text=[money(original_price), money(promo_price)], textposition="outside"))
            polish_fig(fig, 230)
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        if promo_price < cost:
            st.error(f"利润预警：促销价低于采购成本，单件亏损 {money(abs(unit_profit))}。不建议按当前参数执行。")
        elif promo_margin < .10:
            st.warning(f"利润预警：促销毛利率低于 10%，当前毛利率为 {percent(promo_margin)}，建议复核折扣、采购成本和活动预算。")
        else:
            st.success(f"当前参数下促销价高于采购成本，静态毛利率为 {percent(promo_margin)}。仍需评估营销、物流及平台费用。")
        section("促销前后毛利对比", "相同预计销量下的理论毛利对比")
        comp = pd.DataFrame({"场景":["日常销售", "促销销售"], "预计毛利":[original_total_gp, promo_total_gp]})
        fig = px.bar(comp, x="场景", y="预计毛利", text_auto=".2s", color="场景", color_discrete_map={"日常销售":"#AAB4C1", "促销销售":"#D94841"})
        fig.update_layout(showlegend=False)
        polish_fig(fig, 260)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        st.markdown('<div class="notice">测算边界：本工具仅基于商品售价和采购成本计算静态毛利，不包含平台佣金、履约物流、营销费用、税费、退货损耗与库存机会成本。预计销量为用户输入，不是销量预测；测算结果不能直接视为活动真实利润。</div>', unsafe_allow_html=True)
        if not promotion_details.empty:
            with st.expander("查看历史模拟促销规则明细"):
                promo_view = promotion_details[promotion_details["sku_id"].astype(str) == sku] if "sku_id" in promotion_details else pd.DataFrame()
                if not promo_view.empty:
                    show_table(promo_view, 250)
                else:
                    empty_state("该商品没有已生成的促销活动明细")

# ============================================================
# 页面 9：经营助手（规则驱动）
# ============================================================
elif current_page == "经营助手":
    page_header("RULE-BASED BUSINESS ASSISTANT", "采销经营助手", "输入一个经营问题，系统根据关键词调用本地统计规则生成分析提示。此版本不调用外部 API，也不是 LLM 自主规划 Agent。")
    question = st.text_input("描述你想分析的问题", placeholder="例如：哪些商品有缺货风险？哪个品类销售额最高？备选供应商有哪些？")
    run = st.button("生成分析建议", type="primary")
    if run:
        q = question.strip()
        if not q:
            st.warning("请先输入一个问题。")
        else:
            st.markdown('<div class="panel">', unsafe_allow_html=True)
            st.markdown(f"**你的问题：** {html.escape(q)}")
            if any(k in q for k in ["库存", "缺货", "覆盖", "效期"]):
                if not inventory.empty:
                    inv = inventory.copy()
                    inv = as_numeric(inv, ["inventory_coverage_days", "available_stock"])
                    if selected_categories and "category_name" in inv: inv = inv[inv["category_name"].astype(str).isin(selected_categories)]
                    risk = inv[inv["inventory_coverage_days"] <= 7].sort_values("inventory_coverage_days") if "inventory_coverage_days" in inv else pd.DataFrame()
                    st.markdown(f"**分析结果：** 当前库存快照中有 **{len(risk)}** 个 SKU 的库存覆盖天数不超过 7 天。")
                    if not risk.empty:
                        show_table(risk[[c for c in ["sku_id","product_name","category_name","available_stock","inventory_coverage_days"] if c in risk]].head(10), 260)
                    st.info("建议优先核对近 7/14/30 天销量、在途到货时间与供应商交付状态，再决定是否补货。")
                else: st.warning("当前没有库存快照数据。")
            elif any(k in q for k in ["供应商", "主供", "备选", "采购"]):
                if not backup_recs.empty:
                    rec = backup_recs.copy()
                    if selected_categories and "category_name" in rec: rec = rec[rec["category_name"].astype(str).isin(selected_categories)]
                    st.markdown(f"**分析结果：** 当前筛选范围内共有 **{len(rec)}** 条主供与备选供应商对比记录。")
                    if "decision" in rec:
                        show_table(rec["decision"].value_counts().rename_axis("决策建议").reset_index(name="SKU 数量"), 220)
                    st.info("建议对备选供应商进一步核实质量、产能、资质、结算条件和真实报价；系统推荐仅作为初筛。")
                elif not supplier_ratings.empty:
                    st.markdown(f"**分析结果：** 当前可查看 {len(supplier_ratings)} 家供应商的绩效评分。")
                    show_table(supplier_ratings.head(10), 240)
                else: st.warning("当前没有供应商绩效或映射数据。")
            elif any(k in q for k in ["竞品", "价格", "售价", "价差"]):
                if not competitors.empty:
                    cp = competitors.copy()
                    if selected_categories and "category_name" in cp: cp = cp[cp["category_name"].astype(str).isin(selected_categories)]
                    cp = as_numeric(cp, ["competitor_price", "own_selling_price"])
                    lower = cp[cp["competitor_price"] < cp["own_selling_price"]] if all(c in cp for c in ["competitor_price","own_selling_price"]) else pd.DataFrame()
                    st.markdown(f"**分析结果：** 当前竞品价格记录中，有 **{len(lower)}** 条竞品报价低于本商品售价。")
                    show_table(lower.head(12), 270)
                    st.info("建议先按品牌、规格、渠道和促销状态核对可比性，再判断是否需要调整售价。")
                else: st.warning("当前没有竞品价格数据。")
            elif any(k in q for k in ["促销", "折扣", "毛利", "利润"]):
                st.markdown("**分析结果：** 可前往「促销测算」页面，选择 SKU 并调整折扣和预计销量，查看促销价、单件毛利与毛利率。")
                st.info("建议重点关注促销价是否低于采购成本，以及促销毛利率是否低于项目设定的 10% 预警线。")
            elif any(k in q for k in ["品类", "销售额", "销量", "增长"]):
                if not sales_filtered.empty and "category_name" in sales_filtered:
                    d = as_numeric(sales_filtered, ["revenue", "gross_profit"])
                    cat = d.groupby("category_name", as_index=False).agg(revenue=("revenue","sum"), gross_profit=("gross_profit","sum")).sort_values("revenue", ascending=False)
                    if not cat.empty:
                        st.markdown(f"**分析结果：** 当前销售额排名第一的品类为 **{cat.iloc[0]['category_name']}**，销售额 {money(cat.iloc[0]['revenue'])}。")
                        show_table(cat, 270)
                else: st.warning("当前没有可用销售数据。")
            else:
                st.info("暂未识别问题类型。可以尝试询问：库存风险、供应商绩效、备选供应商、竞品价格、促销折扣或品类销售。")
            st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('<div class="notice">能力边界：当前助手使用关键词识别和固定分析规则，不具备大语言模型理解、动态工具规划或多轮自主调用能力。简历与演示时建议称为“规则驱动经营分析助手 / Agent 原型”，不要表述为已接入真实 LLM Tool Calling。</div>', unsafe_allow_html=True)

# ============================================================
# 页面 10：数据说明
# ============================================================
elif current_page == "数据说明":
    page_header("DATA & METHODOLOGY", "数据资产与口径说明", "查看当前 Demo 所依赖的数据文件、业务覆盖范围和关键指标的计算边界。")
    data_info = [
        ("products.csv", products, "商品档案", "SKU、品类、品牌、规格、售价、采购成本"),
        ("sales_daily.csv", sales, "日销售明细", "按日期与 SKU 生成的模拟销售记录"),
        ("inventory_snapshot.csv", inventory, "库存快照", "单日可用库存、安全库存、在途库存与覆盖天数"),
        ("inventory_batches.csv", batches, "库存批次", "批次数量、生产日期、效期与库存成本"),
        ("suppliers.csv", suppliers, "供应商档案", "供应商层级、主营品类与状态"),
        ("supplier_ratings_v2.csv", supplier_ratings, "供应商评分", "交付、准时性与订单完成情况综合评分"),
        ("supplier_strategies.csv", supplier_strategies, "供应商策略", "合作级别、采购优先级与风险控制建议"),
        ("backup_supplier_recommendations.csv", backup_recs, "备选供应商", "主供与备选供应商的综合比较"),
        ("competitor_prices.csv", competitors, "竞品价格", "模拟竞品报价、渠道和价格位置"),
        ("promotions.csv", promotions, "促销活动", "模拟活动名称、类型、周期和状态"),
        ("promotion_details.csv", promotion_details, "促销明细", "折扣率、促销价、毛利率与利润预警"),
        ("product_supplier_mapping.csv", product_supplier, "商品供应商映射", "SKU 对应的主供及备选供应商"),
        ("purchase_orders.csv", purchase_orders, "采购订单", "采购数量、金额、到货状态"),
        ("purchase_receipts.csv", receipts, "采购收货", "分批收货与实际收货数量"),
    ]
    status_rows = []
    for filename, frame, cn, desc in data_info:
        status_rows.append({"文件名":filename, "数据主题":cn, "记录数":len(frame), "状态":"已加载" if not frame.empty else "未找到", "用途":desc})
    show_table(pd.DataFrame(status_rows), 470)
    st.markdown('<div class="notice">重要声明：项目数据为自行构造的模拟数据，用于展示酒水采销、库存、供应商及促销分析流程。商品、品牌、供应商、竞品、价格、交易与促销记录不代表真实企业或市场数据。页面中的“经营建议”由规则计算生成，仅作演示和分析参考。</div>', unsafe_allow_html=True)
    section("核心指标口径", "查看重要指标如何计算")
    definitions = pd.DataFrame([
        {"指标":"销售额", "计算方式":"销售明细 revenue 汇总", "注意事项":"模拟销售收入，不等于实际回款"},
        {"指标":"毛利", "计算方式":"销售额 - 商品采购成本", "注意事项":"未扣除佣金、物流、营销、税费等费用"},
        {"指标":"毛利率", "计算方式":"毛利 ÷ 销售额", "注意事项":"按当前统计范围汇总后计算"},
        {"指标":"访客成交率", "计算方式":"模拟订单量 ÷ 访客量", "注意事项":"订单量为模拟字段，不代表真实平台转化"},
        {"指标":"库存覆盖天数", "计算方式":"由库存快照中的日均销量与可用库存计算", "注意事项":"库存为单日快照，不是完整历史库存流水"},
        {"指标":"供应商综合评分", "计算方式":"交付率、准时率、订单完成率按设定权重合成", "注意事项":"受统计截止日期和到期订单范围影响"},
        {"指标":"促销毛利", "计算方式":"(促销价 - 采购成本) × 预计销量", "注意事项":"不含其他经营费用；销量为输入或模拟值"},
    ])
    show_table(definitions, 330)

# Footer
st.markdown(
    '<div class="footer-note">BEVERAGE PROCUREMENT INTELLIGENCE · 规则驱动演示系统<br>'
    '本系统为个人作品集项目，数据为模拟构造，不构成真实采购、定价或供应商准入建议。</div>',
    unsafe_allow_html=True,
)
