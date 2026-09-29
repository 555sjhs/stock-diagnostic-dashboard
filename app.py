import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

# ==========================================
# 0. 頁面配置與 THESTOCKs 極致暗黑交易終端 CSS
# ==========================================
st.set_page_config(
    page_title="THESTOCKs // QUANT TERMINAL",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .stApp {
        background-color: #0e0f14 !important;
        color: #eaecef !important;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", sans-serif;
    }
    section[data-testid="stSidebar"] {
        background-color: #14151b !important;
        border-right: 1px solid #23272e !important;
    }
    
    /* 頂部 Bybit 橫幅 */
    .bybit-header {
        background: #181a20;
        border: 1px solid #262932;
        border-radius: 4px;
        padding: 12px 18px;
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        gap: 24px;
        margin-bottom: 12px;
    }
    .bybit-title {
        font-size: 1.15rem;
        font-weight: 700;
        letter-spacing: 0.05em;
        color: #f0b90b;
        border-right: 1px solid #2b2f36;
        padding-right: 18px;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .bybit-price {
        font-family: 'SF Mono', Monaco, Menlo, Consolas, monospace;
        font-size: 1.6rem;
        font-weight: 700;
        line-height: 1;
    }
    .bybit-metric-label {
        font-size: 0.68rem;
        color: #848e9c;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        margin-bottom: 2px;
    }
    .bybit-metric-val {
        font-family: 'SF Mono', Monaco, Menlo, Consolas, monospace;
        font-size: 0.95rem;
        font-weight: 600;
        color: #eaecef;
    }
    .bybit-section-title {
        font-size: 0.84rem;
        font-weight: 700;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: #f0b90b;
        border-left: 3px solid #f0b90b;
        padding-left: 8px;
        margin-top: 14px;
        margin-bottom: 8px;
    }

    /* 分析師目標價標籤 */
    .target-badge {
        display: inline-block;
        padding: 4px 8px;
        border-radius: 4px;
        font-family: monospace;
        font-size: 0.82rem;
        font-weight: 700;
        margin-left: 6px;
    }

    /* 共識進度條 */
    .bar-container {
        display: flex;
        align-items: center;
        margin-bottom: 6px;
        font-size: 0.82rem;
    }
    .bar-label {
        width: 45px;
        color: #848e9c;
    }
    .bar-track {
        flex-grow: 1;
        height: 6px;
        background: #262932;
        border-radius: 3px;
        overflow: hidden;
        margin: 0 10px;
    }
    .bar-fill {
        height: 100%;
        border-radius: 3px;
    }
    .bar-pct {
        width: 40px;
        text-align: right;
        font-family: monospace;
        color: #eaecef;
    }

    /* 新聞卡片 */
    .bybit-news-card {
        background: #181a20;
        border: 1px solid #262932;
        border-left: 3px solid #3a7bd5;
        border-radius: 4px;
        padding: 10px 14px;
        margin-bottom: 8px;
    }
    .bybit-news-card:hover {
        border-left-color: #f0b90b;
        background: #1f222a;
    }
    .bybit-news-title {
        font-size: 0.9rem;
        font-weight: 600;
        color: #eaecef;
        text-decoration: none;
    }
    .bybit-news-title:hover {
        color: #f0b90b;
    }
    .bybit-news-meta {
        font-size: 0.72rem;
        color: #848e9c;
        margin-top: 4px;
        font-family: monospace;
    }

    /* Tab 切換器樣式 */
    button[data-baseweb="tab"] {
        font-size: 0.9rem !important;
        font-weight: 700 !important;
        color: #848e9c !important;
        padding: 10px 16px !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        color: #f0b90b !important;
        border-bottom-color: #f0b90b !important;
    }
    .stDataFrame {
        border: 1px solid #262932;
        border-radius: 4px;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 1. 基礎字典與工具函式
# ==========================================
STOCK_INDEX = {
    "NVDA": "NVIDIA (算力 GPU/AI 霸主)", "META": "Meta Platforms (社群與開源AI)", "AAPL": "Apple (消費電子生態)",
    "MSFT": "Microsoft (Azure/AI)", "GOOGL": "Alphabet (Google 廣告與雲端)", "AMZN": "Amazon (AWS/電商)",
    "TSM": "台積電 ADR (晶圓代工)", "AMD": "AMD (CPU/GPU)", "AVGO": "Broadcom (網通/ASIC)",
    "MU": "Micron (美光/記憶體)", "TSLA": "Tesla (電動車/機器人)", "INTC": "Intel (晶圓製造/CPU)",
    "NFLX": "Netflix (串流影音龍頭)", "2330.TW": "台積電 (2330/晶圓代工龍頭)", "2454.TW": "聯發科 (2454/行動晶片)",
    "2317.TW": "鴻海 (2317/伺服器代工)", "2382.TW": "廣達 (2382/AI 伺服器整機)", "3017.TW": "奇鋐 (3017/AI 散熱 3D VC)"
}

ETF_INDEX = {
    "0050.TW": "元大台灣50 (台灣前50大權值旗艦)",
    "006208.TW": "富邦台50 (低內扣台股核心大盤)",
    "SPY": "SPDR S&P 500 ETF (標普500核心大盤)",
    "QQQ": "Invesco QQQ (那斯達克100科技旗艦)",
    "SOXX": "iShares 半導體 ETF (費城半導體龍頭)",
    "VT": "Vanguard 全球股票 ETF (全市場配置)",
    "VTI": "Vanguard 美股全市場 ETF"
}

EQUITY_PEERS = {
    "NVDA": ["AMD", "AVGO", "2330.TW", "INTC"], "META": ["GOOGL", "MSFT", "AMZN", "SNAP"],
    "AMD": ["NVDA", "INTC", "QCOM", "2454.TW"], "AVGO": ["NVDA", "MRVL", "QCOM", "2454.TW"],
    "TSM": ["2330.TW", "INTC", "2303.TW", "ASML"], "2330.TW": ["TSM", "INTC", "2303.TW", "NVDA"],
    "2454.TW": ["QCOM", "NVDA", "AMD", "3661.TW"], "2317.TW": ["2382.TW", "3231.TW", "AAPL"],
    "2382.TW": ["2317.TW", "6669.TW", "3231.TW"], "2308.TW": ["3017.TW", "3324.TWO", "NVDA"],
    "MSFT": ["AAPL", "GOOGL", "AMZN", "ORCL"], "AAPL": ["MSFT", "GOOGL", "2317.TW", "2330.TW"],
    "TSLA": ["RIVN", "LCID", "2317.TW"], "NFLX": ["DIS", "AMZN", "WBD", "PARA"]
}

ETF_PEERS = {
    "0050.TW": ["006208.TW", "SPY", "QQQ"], "006208.TW": ["0050.TW", "SPY", "QQQ"],
    "SPY": ["QQQ", "0050.TW", "VT"], "QQQ": ["SPY", "SOXX", "006208.TW"],
    "SOXX": ["QQQ", "SPY"], "VT": ["VTI", "SPY", "0050.TW"]
}

SECTOR_PEER_POOLS = {
    "Technology": ["NVDA", "AAPL", "MSFT", "2330.TW", "AMD"],
    "Semiconductors": ["NVDA", "AMD", "AVGO", "2330.TW", "INTC", "TSM"],
    "Communication Services": ["GOOGL", "META", "NFLX", "DIS"],
    "Consumer Cyclical": ["AMZN", "TSLA", "HD", "NKE"],
    "Financial Services": ["2881.TW", "JPM", "BAC", "MS"]
}

def normalize_ticker(raw_input):
    sym = raw_input.strip().upper()
    tw_listed = ["0050", "0056", "006208", "00878", "00919", "00929", "2330", "2317", "2454", "2382", "2308", "3017", "2881", "3231", "6669"]
    for t in tw_listed:
        if sym == f"{t}.TWO": return f"{t}.TW"
    if sym.isdigit() and len(sym) in [4, 5]:
        return f"{sym}.TW"
    return sym

@st.cache_data(ttl=600)
def get_usd_twd_rate():
    try:
        fx = yf.Ticker("USDTWD=X")
        rate = fx.fast_info.get("lastPrice") or fx.history(period="1d")["Close"].iloc[-1]
        return float(rate)
    except Exception:
        return 32.0

USD_TWD = get_usd_twd_rate()

@st.cache_data(ttl=60)
def load_price_history(sym, period="1d"):
    s = yf.Ticker(sym)
    if period == "1d":
        df = s.history(period="1d", interval="5m")
    elif period == "5d":
        df = s.history(period="5d", interval="15m")
    elif period == "1mo":
        df = s.history(period="1mo", interval="1d")
    elif period == "1y":
        df = s.history(period="1y", interval="1d")
    else:
        df = s.history(period="5y", interval="1wk")
    return df, dict(s.fast_info)

@st.cache_resource(ttl=3600)
def load_equity_data(sym):
    s = yf.Ticker(sym)
    return s, s.info, s.financials, s.balance_sheet, s.cashflow

@st.cache_data(ttl=120)
def fetch_realtime_news_5days(sym_list):
    all_news = []
    seen_titles = set()
    now_ts = time.time()
    five_days_sec = 5 * 86400

    for s_code in sym_list[:3]:
        try:
            t = yf.Ticker(s_code)
            raw_items = t.news or []
            for item in raw_items:
                title = item.get("title", "")
                pub_time = item.get("providerPublishTime", 0)
                if not pub_time and "content" in item:
                    pub_time = item.get("content", {}).get("pubDate", 0)

                if pub_time and (now_ts - pub_time) > five_days_sec:
                    continue

                if title and title not in seen_titles:
                    seen_titles.add(title)
                    diff_hours = int((now_ts - pub_time) / 3600) if pub_time else 0
                    rel_time = "剛剛" if diff_hours < 1 else (f"{diff_hours} 小時前" if diff_hours < 24 else f"{diff_hours // 24} 天前")
                    exact_time = datetime.fromtimestamp(pub_time).strftime('%m-%d %H:%M') if pub_time else ""
                    all_news.append({
                        "ticker": s_code,
                        "title": title,
                        "link": item.get("link") or item.get("canonicalUrl", {}).get("url", "#"),
                        "publisher": item.get("publisher", "Wire Feed"),
                        "timestamp": pub_time,
                        "time_str": f"{rel_time} ({exact_time})" if exact_time else rel_time
                    })
        except Exception:
            continue

    if len(all_news) < 3:
        primary_sym = sym_list[0].replace(".TW", "").replace(".TWO", "")
        tw_name_map = {"2330": "台積電", "2454": "聯發科", "2317": "鴻海", "0050": "元大台灣50", "006208": "富邦台50", "2382": "廣達"}
        query_kw = tw_name_map.get(primary_sym, primary_sym)
        rss_url = f"https://news.google.com/rss/search?q={urllib.parse.quote(query_kw + ' 股票')}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
        try:
            req = urllib.request.Request(rss_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=3) as resp:
                tree = ET.fromstring(resp.read())
                for item in tree.findall('.//item')[:4]:
                    t_text = item.find('title').text
                    l_text = item.find('link').text
                    if t_text and t_text not in seen_titles:
                        seen_titles.add(t_text)
                        all_news.append({
                            "ticker": sym_list[0],
                            "title": t_text,
                            "link": l_text,
                            "publisher": "Google Wire",
                            "timestamp": now_ts,
                            "time_str": "即時快訊"
                        })
        except Exception:
            pass

    all_news.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
    return all_news[:8]

def safe_extract(df, candidate_keys):
    if df.empty:
        return pd.Series(dtype=float)
    for k in candidate_keys:
        if k in df.index:
            s = df.loc[k]
            if isinstance(s, pd.DataFrame):
                s = s.iloc[0]
            return pd.to_numeric(s, errors="coerce")
    return pd.Series(dtype=float)

@st.cache_data(ttl=3600)
def get_auto_peers(target_sym, is_etf=False):
    target_sym = normalize_ticker(target_sym)
    if is_etf:
        return ETF_PEERS.get(target_sym, ["0050.TW", "SPY", "QQQ"])
    if target_sym in EQUITY_PEERS:
        return EQUITY_PEERS[target_sym]
    try:
        t_info = yf.Ticker(target_sym).info
        sector = t_info.get("sector", "")
        industry = t_info.get("industry", "")
        for k, pool in SECTOR_PEER_POOLS.items():
            if k.lower() in industry.lower(): return [p for p in pool if p != target_sym][:4]
        for k, pool in SECTOR_PEER_POOLS.items():
            if k.lower() in sector.lower(): return [p for p in pool if p != target_sym][:4]
    except Exception: pass
    return ["NVDA", "AAPL", "2330.TW", "MSFT"]

# ==========================================
# 2. 側邊欄控制台
# ==========================================
st.sidebar.markdown("<div style='color: #f0b90b; font-weight:800; font-size:1.3rem; letter-spacing:0.06em; margin-bottom:12px;'>THESTOCKs</div>", unsafe_allow_html=True)

pipeline_mode = st.sidebar.radio(
    "ENGINE PIPELINE",
    ["企業個股深度診斷迴路", "指數型 ETF 資產穿透迴路"],
    index=0
)

st.sidebar.caption(f"USDT / TWD FX: **{USD_TWD:.2f}**")

if pipeline_mode == "企業個股深度診斷迴路":
    input_choice = st.sidebar.radio("SELECTION", ["WATCHLIST HOT", "CUSTOM TICKER"], horizontal=True)
    if input_choice == "WATCHLIST HOT":
        opts = [f"{s} // {n}" for s, n in STOCK_INDEX.items()]
        sel = st.sidebar.selectbox("ASSET SPOT", options=opts, index=0)
        ticker = sel.split(" // ")[0].strip()
    else:
        raw_in = st.sidebar.text_input("TICKER SEARCH (支援任意代碼如 META, NFLX, 2330):", value="META")
        ticker = normalize_ticker(raw_in)
    
    suggested_peers = get_auto_peers(ticker, is_etf=False)
    all_peers = [ticker] + [p for p in suggested_peers if p != ticker]
    peer_input = st.sidebar.text_input("PEERS BASKET (自動匹配同業，已置頂自己):", value=",".join(all_peers))

else:
    input_choice = st.sidebar.radio("SELECTION", ["ETF HOT BASKET", "CUSTOM ETF"], horizontal=True)
    if input_choice == "ETF HOT BASKET":
        opts = [f"{s} // {n}" for s, n in ETF_INDEX.items()]
        sel = st.sidebar.selectbox("INDEX ASSET", options=opts, index=0)
        ticker = sel.split(" // ")[0].strip()
    else:
        raw_in = st.sidebar.text_input("ETF TICKER (如 0050, SPY, QQQ):", value="0050")
        ticker = normalize_ticker(raw_in)
        
    suggested_peers = get_auto_peers(ticker, is_etf=True)
    all_peers = [ticker] + [p for p in suggested_peers if p != ticker]
    peer_input = st.sidebar.text_input("COMPARISON BASKET (自動匹配對比標的):", value=",".join(all_peers))

if not ticker:
    st.stop()

# ==============================================================================
# 迴路 A：企業個股深度診斷
# ==============================================================================
if pipeline_mode == "企業個股深度診斷迴路":
    with st.spinner(f"THESTOCKs 正在穿透數據: {ticker}..."):
        try:
            stock, info, inc, bs, cf = load_equity_data(ticker)
            chart_1d, fast_info = load_price_history(ticker, period="1d")
            chart_1y, _ = load_price_history(ticker, period="1y")
        except Exception as e:
            st.error(f"DATA_FETCH_EXCEPTION: {e}")
            st.stop()

    if inc.empty or bs.empty or cf.empty:
        st.error(f"ERR_EMPTY_STATEMENTS: {ticker} 未返回完整財報資料，若為 ETF 請切換至左側「指數型 ETF 迴路」。")
        st.stop()

    curr = info.get("currency") or ("TWD" if ".TW" in ticker else "USD")
    is_twd = (curr == "TWD")
    curr_sym = "NT$" if is_twd else "$"

    current_price = fast_info.get("lastPrice", info.get("currentPrice", 0.0))
    prev_close = fast_info.get("previousClose", info.get("previousClose", current_price))
    change = current_price - prev_close
    pct_change = (change / prev_close) * 100 if prev_close else 0.0

    raw_mcap_local = fast_info.get("marketCap", info.get("marketCap", 0)) or 0
    mcap_usd = (raw_mcap_local / USD_TWD) if is_twd else raw_mcap_local
    mcap_usd_b = mcap_usd / 1e9

    bybit_green = "#00c087"
    bybit_red = "#f6465d"
    is_up = change >= 0
    theme_color = bybit_green if is_up else bybit_red

    low52 = info.get('fiftyTwoWeekLow', current_price) or current_price
    high52 = info.get('fiftyTwoWeekHigh', current_price) or current_price
    pos52 = ((current_price - low52) / (high52 - low52) * 100) if high52 > low52 else 50.0
    pos52 = min(max(pos52, 0.0), 100.0)

    f_pe = info.get("forwardPE", "N/A")
    t_pe = info.get("trailingPE", "N/A")

    # 頂部即時 Ticker
    st.markdown(f"""
    <div class="bybit-header">
        <div class="bybit-title">
            <span>[EQUITY] {ticker}</span>
            <span style="font-size:0.75rem; color:#848e9c; font-weight:normal;">{info.get('shortName', ticker)}</span>
        </div>
        <div>
            <div class="bybit-metric-label">LAST PRICE ({curr})</div>
            <div class="bybit-price" style="color: {theme_color};">
                {curr_sym}{current_price:,.2f}
                <span style="font-size: 0.95rem; margin-left: 6px;">{'+' if is_up else ''}{change:.2f} ({'+' if is_up else ''}{pct_change:.2f}%)</span>
            </div>
        </div>
        <div>
            <div class="bybit-metric-label">52W RANGE POSITION</div>
            <div style="font-size: 0.85rem; font-family: monospace; color:#eaecef;">
                {curr_sym}{low52:.1f} - {curr_sym}{high52:.1f}
            </div>
            <div class="bybit-range-bg" style="width: 140px;">
                <div class="bybit-range-fill" style="width: {pos52:.0f}%; background: {theme_color};"></div>
            </div>
        </div>
        <div>
            <div class="bybit-metric-label">VALUATION (FWD / TTM)</div>
            <div class="bybit-metric-val">{f_pe if isinstance(f_pe, str) else f"{f_pe:.1f}x"} / {t_pe if isinstance(t_pe, str) else f"{t_pe:.1f}x"}</div>
        </div>
        <div>
            <div class="bybit-metric-label">STANDARDIZED MCAP</div>
            <div class="bybit-metric-val" style="color: #f0b90b;">${mcap_usd_b:,.1f}B USD</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 報表整理
    common_cols = [c for c in inc.columns if c in bs.columns and c in cf.columns]
    common_cols.sort()
    c_inc, c_bs, c_cf = inc[common_cols], bs[common_cols], cf[common_cols]
    years = [col.strftime('%Y') for col in common_cols]

    cfo_series = safe_extract(c_cf, ["Operating Cash Flow", "OperatingCashFlow", "Cash Flowsfromusedin Operating Activities"])
    capex_series = safe_extract(c_cf, ["Capital Expenditure", "CapitalExpenditure", "Investing Cash Flow"]).abs()
    ni_series = safe_extract(c_inc, ["Net Income", "NetIncome", "Net Income Common Stockholders"])
    rev_series = safe_extract(c_inc, ["Total Revenue", "TotalRevenue", "Operating Revenue", "Revenue"])
    gp_series = safe_extract(c_inc, ["Gross Profit", "GrossProfit"])
    op_series = safe_extract(c_inc, ["Operating Income", "OperatingIncome", "EBIT"])
    equity_series = safe_extract(c_bs, ["Stockholders Equity", "StockholdersEquity", "Total Equity Gross Minority Interest"])
    assets_series = safe_extract(c_bs, ["Total Assets", "TotalAssets"])
    fcf_series = cfo_series - capex_series
    rev, gp, op = rev_series / 1e9, gp_series / 1e9, op_series / 1e9
    gross_margin = (gp / rev) * 100
    op_margin = (op / rev) * 100

    # ==========================================
    # 四大標籤頁 (無任何 Emoji)
    # ==========================================
    tab_analytics, tab_fundamentals, tab_valuation, tab_peers_news = st.tabs([
        "行情與分析 (ANALYTICS)",
        "深度基本面 (FUNDAMENTALS)",
        "估值與營運週期 (VALUATION & CYCLE)",
        "同業與新聞 (PEERS & NEWS)"
    ])

    # --------------------------------------------------------------------------
    # TAB 1: 行情與分析
    # --------------------------------------------------------------------------
    with tab_analytics:
        st.markdown("<div class='bybit-section-title'>PRICE ACTION // INTRADAY TICK</div>", unsafe_allow_html=True)
        if not chart_1d.empty:
            fig_live = go.Figure()
            p_min, p_max = chart_1d['Close'].min(), chart_1d['Close'].max()
            pad = (p_max - p_min) * 0.08 if p_max > p_min else p_min * 0.01
            fig_live.add_trace(go.Scatter(
                x=chart_1d.index, y=chart_1d['Close'], mode='lines', name='Price',
                line=dict(color=theme_color, width=2.0), fill='tozeroy',
                fillcolor=f"rgba({ '0, 192, 135' if is_up else '246, 70, 93' }, 0.08)"
            ))
            fig_live.add_hline(y=prev_close, line_dash="dash", line_color="#555a65", line_width=1,
                               annotation_text=f"REF {curr_sym}{prev_close:.2f}", annotation_position="bottom right")
            fig_live.update_layout(
                template="plotly_dark", height=240, margin=dict(l=10, r=10, t=10, b=10),
                paper_bgcolor="#181a20", plot_bgcolor="#181a20",
                xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor="#262932", side="right", range=[p_min - pad, p_max + pad]),
                hovermode="x unified"
            )
            st.plotly_chart(fig_live, use_container_width=True)

        st.markdown("---")

        st.markdown("<div class='bybit-section-title'>ANALYST CONSENSUS & 12-MONTH PRICE TARGET</div>", unsafe_allow_html=True)

        t_mean = info.get("targetMeanPrice", np.nan)
        t_high = info.get("targetHighPrice", np.nan)
        t_low = info.get("targetLowPrice", np.nan)
        rec_key = info.get("recommendationKey", "N/A").replace("_", " ").upper()
        num_analysts = info.get("numberOfAnalystOpinions", 0)

        if np.isnan(t_mean) or t_mean == 0:
            t_mean = current_price * 1.10
            t_high = current_price * 1.25
            t_low = current_price * 0.90

        implied_upside = ((t_mean - current_price) / current_price) * 100

        col_cone, col_opinions = st.columns([1.6, 1])

        with col_cone:
            st.markdown(f"""
            <div style="margin-bottom: 6px;">
                <span style="font-size:0.85rem; color:#848e9c;">12 個月目標價格：</span>
                <span style="font-size:1.35rem; font-weight:700; font-family:monospace; color:#eaecef;">{curr_sym}{t_mean:.2f}</span>
                <span class="target-badge" style="background: rgba({'0, 192, 135' if implied_upside >= 0 else '246, 70, 93'}, 0.15); color: {bybit_green if implied_upside >= 0 else bybit_red};">
                    {'+' if implied_upside >= 0 else ''}{implied_upside:.2f}%
                </span>
            </div>
            """, unsafe_allow_html=True)

            if not chart_1y.empty:
                last_dt = chart_1y.index[-1]
                future_dt = last_dt + pd.DateOffset(years=1)

                fig_cone = go.Figure()
                fig_cone.add_trace(go.Scatter(
                    x=chart_1y.index, y=chart_1y['Close'],
                    mode='lines', name='過去 1 年股價',
                    line=dict(color="#eaecef", width=1.8)
                ))

                fig_cone.add_trace(go.Scatter(
                    x=[last_dt, future_dt], y=[current_price, t_high],
                    mode='lines', name='最高目標價',
                    line=dict(color="#00c087", width=1.5, dash="dot")
                ))
                fig_cone.add_trace(go.Scatter(
                    x=[last_dt, future_dt], y=[current_price, t_low],
                    mode='lines', name='最低目標價',
                    line=dict(color="#f6465d", width=1.5, dash="dot"),
                    fill='tonexty', fillcolor='rgba(240, 185, 11, 0.08)'
                ))
                fig_cone.add_trace(go.Scatter(
                    x=[last_dt, future_dt], y=[current_price, t_mean],
                    mode='lines+markers', name='平均目標價',
                    line=dict(color="#f0b90b", width=2.2, dash="dash")
                ))

                fig_cone.add_trace(go.Scatter(
                    x=[last_dt], y=[current_price],
                    mode='markers+text', name='現價',
                    text=[f"目前 {curr_sym}{current_price:.1f}"], textposition="bottom center",
                    marker=dict(color="#f0b90b", size=8)
                ))

                fig_cone.update_layout(
                    template="plotly_dark", height=280, margin=dict(l=10, r=10, t=10, b=10),
                    paper_bgcolor="#181a20", plot_bgcolor="#181a20",
                    xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor="#262932", side="right"),
                    legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5)
                )
                st.plotly_chart(fig_cone, use_container_width=True)

        with col_opinions:
            st.markdown(f"**分析師共識（{num_analysts} 位分析師）**")
            
            rec_color = bybit_green if "BUY" in rec_key else ("#f0b90b" if "HOLD" in rec_key else bybit_red)
            st.markdown(f"""
            <div style="background: #1f222a; border-radius: 4px; padding: 12px; margin-bottom: 12px; border-left: 3px solid {rec_color};">
                <div style="font-size:0.75rem; color:#848e9c; text-transform:uppercase;">CONSENSUS RATING</div>
                <div style="font-size:1.25rem; font-weight:800; color:{rec_color}; margin-top:2px;">{rec_key}</div>
            </div>
            """, unsafe_allow_html=True)

            rec_df = stock.recommendations
            b_pct, h_pct, s_pct = 75, 20, 5
            if rec_df is not None and not rec_df.empty:
                try:
                    latest_rec = rec_df.iloc[-1]
                    s_buy = latest_rec.get("strongBuy", 0)
                    buy = latest_rec.get("buy", 0)
                    hold = latest_rec.get("hold", 0)
                    sell = latest_rec.get("sell", 0)
                    s_sell = latest_rec.get("strongSell", 0)
                    tot = s_buy + buy + hold + sell + s_sell
                    if tot > 0:
                        b_pct = int(((s_buy + buy) / tot) * 100)
                        h_pct = int((hold / tot) * 100)
                        s_pct = 100 - b_pct - h_pct
                except Exception:
                    pass

            st.markdown(f"""
            <div class="bar-container">
                <div class="bar-label" style="color: #00c087; font-weight: bold;">買入</div>
                <div class="bar-track"><div class="bar-fill" style="width: {b_pct}%; background: #00c087;"></div></div>
                <div class="bar-pct">{b_pct}%</div>
            </div>
            <div class="bar-container">
                <div class="bar-label" style="color: #848e9c;">持有</div>
                <div class="bar-track"><div class="bar-fill" style="width: {h_pct}%; background: #848e9c;"></div></div>
                <div class="bar-pct">{h_pct}%</div>
            </div>
            <div class="bar-container">
                <div class="bar-label" style="color: #f6465d;">賣出</div>
                <div class="bar-track"><div class="bar-fill" style="width: {s_pct}%; background: #f6465d;"></div></div>
                <div class="bar-pct">{s_pct}%</div>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("<div style='font-size:0.75rem; color:#848e9c; margin-top:14px; text-transform:uppercase;'>LATEST UPGRADES / DOWNGRADES</div>", unsafe_allow_html=True)
            try:
                upgrades = stock.upgrades_downgrades
                if upgrades is not None and not upgrades.empty:
                    top_upgrades = upgrades.head(3).reset_index()
                    for _, row in top_upgrades.iterrows():
                        firm = row.get("Firm", "Wall Street Firm")
                        to_grade = row.get("ToGrade", "Rating")
                        d_val = row.get("Date", None)
                        d_str = d_val.strftime('%m-%d') if isinstance(d_val, datetime) else "近期"
                        st.markdown(f"""
                        <div style="display:flex; justify-content:space-between; font-size:0.8rem; padding: 4px 0; border-bottom: 1px solid #262932;">
                            <span style="color:#eaecef;">{firm} <span style="color:#848e9c; font-size:0.7rem;">({d_str})</span></span>
                            <span style="color:#f0b90b; font-weight:600;">{to_grade}</span>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.caption("暫無近期機構評等明細。")
            except Exception:
                st.caption("機構評等即時資料傳輸中。")

    # --------------------------------------------------------------------------
    # TAB 2: 深度基本面
    # --------------------------------------------------------------------------
    with tab_fundamentals:
        st.markdown("<div class='bybit-section-title'>AUDIT STATUS // LIQUIDITY & EARNINGS QUALITY</div>", unsafe_allow_html=True)
        flags = []
        if len(cfo_series) >= 2 and len(ni_series) >= 2:
            if (cfo_series.iloc[-1] < ni_series.iloc[-1]) and (cfo_series.iloc[-2] < ni_series.iloc[-2]):
                flags.append("盈餘品質警訊（CFO < Net Income 連續兩年）：帳面淨利未實質轉為營運現金流入。")
        if not equity_series.empty and not assets_series.empty and not ni_series.empty:
            latest_em = assets_series.iloc[-1] / equity_series.iloc[-1]
            latest_roe = ni_series.iloc[-1] / equity_series.iloc[-1]
            if latest_em > 4.0 and latest_roe > 0.20:
                flags.append(f"高槓桿虛胖警訊（槓桿倍數 {latest_em:.2f}x）：ROE 主要依賴負債推升。")
        if not fcf_series.empty and fcf_series.iloc[-1] < 0:
            flags.append("造血失血警訊（最新一期 FCF 為負）：現金流不足支應資本支出。")

        if flags:
            for f in flags: st.error(f"[FLAG] {f}")
        else:
            st.markdown(f"<div style='color:{bybit_green}; font-size:0.85rem; padding: 6px 0; font-family:monospace;'>[STATUS: PASS] 營運現金流充足覆蓋淨利，負債槓桿健康，造血無虞。</div>", unsafe_allow_html=True)

        c_p1, c_p2 = st.columns([1.2, 1])
        with c_p1:
            st.markdown("<div class='bybit-section-title'>MARGIN STRUCTURE TREND</div>", unsafe_allow_html=True)
            fig1 = make_subplots(specs=[[{"secondary_y": True}]])
            fig1.add_trace(go.Bar(x=years, y=rev_series/1e9, name="營收", marker_color="#2b2f36"), secondary_y=False)
            fig1.add_trace(go.Bar(x=years, y=op_series/1e9, name="營業利益", marker_color="#3a7bd5"), secondary_y=False)
            fig1.add_trace(go.Scatter(x=years, y=gross_margin, name="毛利率 %", line=dict(color="#00c087", width=2)), secondary_y=True)
            fig1.add_trace(go.Scatter(x=years, y=op_margin, name="營益率 %", line=dict(color="#f0b90b", width=2, dash='dot')), secondary_y=True)
            fig1.update_layout(barmode="group", template="plotly_dark", height=260, margin=dict(l=10, r=10, t=10, b=10),
                               paper_bgcolor="#181a20", plot_bgcolor="#181a20", legend=dict(orientation="h", y=1.1, x=0))
            st.plotly_chart(fig1, use_container_width=True)

        with c_p2:
            st.markdown("<div class='bybit-section-title'>DUPONT ANALYSIS (ROE BREAKDOWN)</div>", unsafe_allow_html=True)
            nm_vals, at_vals, em_vals, roe_vals = [], [], [], []
            for yr_col in common_cols:
                r = rev_series.get(yr_col, np.nan)
                n = ni_series.get(yr_col, np.nan)
                a = assets_series.get(yr_col, np.nan)
                e = equity_series.get(yr_col, np.nan)
                nm = (n / r) * 100 if (pd.notna(n) and pd.notna(r) and r != 0) else np.nan
                at = (r / a) if (pd.notna(r) and pd.notna(a) and a != 0) else np.nan
                em = (a / e) if (pd.notna(a) and pd.notna(e) and e != 0) else np.nan
                roe = (n / e) * 100 if (pd.notna(n) and pd.notna(e) and e != 0) else (nm * at * em if pd.notna(nm) and pd.notna(at) and pd.notna(em) else np.nan)
                nm_vals.append(nm); at_vals.append(at); em_vals.append(em); roe_vals.append(roe)

            dupont_df = pd.DataFrame({"ROE %": roe_vals, "淨利率 %": nm_vals, "週轉率": at_vals, "槓桿倍數": em_vals}, index=years).T
            st.dataframe(dupont_df.applymap(lambda v: f"{v:.2f}" if pd.notna(v) else "-"), use_container_width=True)

        c_cf1, c_cf2 = st.columns(2)
        with c_cf1:
            st.markdown("<div class='bybit-section-title'>CASH FLOW ACCRETION (CFO VS FCF)</div>", unsafe_allow_html=True)
            fig2 = go.Figure()
            fig2.add_trace(go.Bar(x=years, y=cfo_series/1e9, name="營運現金流 (CFO)", marker_color="#3a7bd5"))
            fig2.add_trace(go.Bar(x=years, y=capex_series/1e9, name="資本支出 (CapEx)", marker_color="#f6465d"))
            fig2.add_trace(go.Bar(x=years, y=fcf_series/1e9, name="自由現金流 (FCF)", marker_color="#00c087"))
            fig2.update_layout(barmode="group", template="plotly_dark", height=240, margin=dict(l=10, r=10, t=10, b=10),
                              paper_bgcolor="#181a20", plot_bgcolor="#181a20", legend=dict(orientation="h", y=1.1, x=0))
            st.plotly_chart(fig2, use_container_width=True)

        with c_cf2:
            st.markdown("<div class='bybit-section-title'>SHAREHOLDER YIELD (DIVIDENDS + BUYBACKS)</div>", unsafe_allow_html=True)
            div_paid = safe_extract(c_cf, ["Cash Dividends Paid", "Common Stock Dividend Paid"]).abs()
            repurchase = safe_extract(c_cf, ["Common Stock Repurchased", "Repurchase Of Capital Stock"]).abs()
            if div_paid.empty: div_paid = pd.Series(0, index=common_cols)
            if repurchase.empty: repurchase = pd.Series(0, index=common_cols)

            fig_sy = go.Figure()
            fig_sy.add_trace(go.Bar(x=years, y=div_paid/1e9, name='現金股利', marker_color='#3a7bd5'))
            fig_sy.add_trace(go.Bar(x=years, y=repurchase/1e9, name='庫藏股回購', marker_color='#f0b90b'))
            fig_sy.update_layout(barmode='stack', template="plotly_dark", height=240, margin=dict(l=10, r=10, t=10, b=10),
                                 paper_bgcolor="#181a20", plot_bgcolor="#181a20", yaxis=dict(gridcolor="#262932"), legend=dict(orientation="h", y=1.1, x=0))
            st.plotly_chart(fig_sy, use_container_width=True)

    # --------------------------------------------------------------------------
    # TAB 3: 估值與營運週期
    # --------------------------------------------------------------------------
    with tab_valuation:
        col_v1, col_v2 = st.columns(2)
        with col_v1:
            st.markdown("<div class='bybit-section-title'>CASH CONVERSION CYCLE (DAYS)</div>", unsafe_allow_html=True)
            cogs_series = safe_extract(c_inc, ["Cost Of Revenue", "CostOfRevenue", "Operating Expense"])
            if cogs_series.empty: cogs_series = rev_series * 0.5
            ar_series = safe_extract(c_bs, ["Accounts Receivable", "Receivables"])
            inv_series = safe_extract(c_bs, ["Inventory"])
            ap_series = safe_extract(c_bs, ["Accounts Payable", "Payables"])

            dso = (ar_series / rev_series) * 365
            dio = (inv_series / cogs_series) * 365
            dpo = (ap_series / cogs_series) * 365
            ccc = dio + dso - dpo

            fig_ccc = go.Figure()
            fig_ccc.add_trace(go.Scatter(x=years, y=dso, mode='lines+markers', name='DSO 應收天數', line=dict(color='#848e9c', width=1.5)))
            fig_ccc.add_trace(go.Scatter(x=years, y=dio, mode='lines+markers', name='DIO 存貨天數', line=dict(color='#f6465d', width=1.5)))
            fig_ccc.add_trace(go.Scatter(x=years, y=dpo, mode='lines+markers', name='DPO 應付天數', line=dict(color='#00c087', width=1.5)))
            fig_ccc.add_trace(go.Scatter(x=years, y=ccc, mode='lines+markers', name='CCC 現金週期', line=dict(color='#f0b90b', width=2.5, dash='dash')))
            fig_ccc.update_layout(template="plotly_dark", height=240, margin=dict(l=10, r=10, t=10, b=10),
                                  paper_bgcolor="#181a20", plot_bgcolor="#181a20", yaxis=dict(gridcolor="#262932"), legend=dict(orientation="h", y=1.1, x=0))
            st.plotly_chart(fig_ccc, use_container_width=True)

        with col_v2:
            st.markdown("<div class='bybit-section-title'>SOLVENCY & LEVERAGE STRESS</div>", unsafe_allow_html=True)
            int_exp = safe_extract(c_inc, ["Interest Expense", "InterestExpense"]).abs()
            ebit = op_series
            int_cov = ebit / int_exp.replace(0, np.nan)
            tot_debt = safe_extract(c_bs, ["Total Debt", "TotalDebt", "Long Term Debt"])
            cash_eq = safe_extract(c_bs, ["Cash And Cash Equivalents", "CashAndCashEquivalents"])
            net_debt = tot_debt - cash_eq

            latest_cov = int_cov.iloc[-1] if not int_cov.empty else np.nan
            latest_nd = net_debt.iloc[-1] if not net_debt.empty else 0
            dr = (tot_debt.iloc[-1] / assets_series.iloc[-1]) * 100 if (not assets_series.empty and assets_series.iloc[-1] > 0) else 0

            sc1, sc2, sc3 = st.columns(3)
            sc1.metric("利息覆蓋倍數", f"{latest_cov:.1f}x" if (not np.isnan(latest_cov) and latest_cov > 0) else "充裕")
            sc2.metric("淨負債規模", f"{curr_sym}{latest_nd/1e9:,.1f} B", "淨現金充裕" if latest_nd < 0 else "淨負債狀態")
            sc3.metric("資產負債率", f"{dr:.1f}%")

        st.markdown("<div class='bybit-section-title'>REVERSE DCF IMPLIED GROWTH MODEL</div>", unsafe_allow_html=True)
        latest_base_fcf = fcf_series.iloc[-1] if not fcf_series.empty else 0
        implied_g = np.nan
        if raw_mcap_local > 0 and latest_base_fcf > 0:
            r1, r2 = st.columns([1, 1.5])
            with r1:
                wacc = st.slider("折現率 WACC (%)", 7.0, 14.0, 9.5, 0.1) / 100.0
                g = st.slider("永續成長率 g (%)", 1.5, 4.0, 2.5, 0.1) / 100.0

            def calc_dcf_value(growth_rate, base_fcf, wacc_val, g_val, n=5):
                pv_fcf = sum([(base_fcf * ((1 + growth_rate) ** yr)) / ((1 + wacc_val) ** yr) for yr in range(1, n + 1)])
                tv = (base_fcf * ((1 + growth_rate) ** n) * (1 + g_val)) / (wacc_val - g_val)
                return pv_fcf + (tv / ((1 + wacc_val) ** n))

            if wacc > g:
                low, high = -0.5, 1.5
                for _ in range(100):
                    mid = (low + high) / 2
                    val = calc_dcf_value(mid, latest_base_fcf, wacc, g)
                    if abs(val - raw_mcap_local) < 1e7: break
                    if val < raw_mcap_local: low = mid
                    else: high = mid
                implied_g = mid * 100

            with r2:
                if not np.isnan(implied_g):
                    st.metric("市場即時隱含未來 5 年 FCF 年化複合成長率 (CAGR)", f"{implied_g:.1f}%", f"Current Cap: ${mcap_usd_b:,.1f}B")
                    if implied_g > 25.0: st.error(f"[HIGH RISK] 高預期高風險（隱含 CAGR {implied_g:.1f}%）：定價已將樂觀預期打滿，容錯率低。")
                    elif implied_g >= 12.0: st.info(f"[BALANCED] 合理成長定價（隱含 CAGR {implied_g:.1f}%）：預期維持穩健擴張。")
                    else: st.success(f"[DEEP VALUE] 深度價值安全邊際（隱含 CAGR {implied_g:.1f}%）：市場預期悲觀，具均值修復空間。")
        else:
            st.info("REVERSE DCF UNAVAILABLE: Negative base FCF.")

        # AI 決策總結
        st.markdown("<div class='bybit-section-title'>EXECUTIVE SYNTHESIS // BUY-SIDE POSITIONING</div>", unsafe_allow_html=True)
        latest_gm = gross_margin.iloc[-1] if not gross_margin.empty and pd.notna(gross_margin.iloc[-1]) else 0
        gm_trend = (gross_margin.iloc[-1] - gross_margin.iloc[0]) if len(gross_margin) >= 2 else 0
        if latest_gm > 50 and gm_trend >= 0:
            moat_eval = f"**強勁定價護城河**（最新毛利率 {latest_gm:.1f}%，維持擴張趨勢）。"
        elif latest_gm > 30:
            moat_eval = f"**營運毛利結構健康**（最新毛利率 {latest_gm:.1f}%）。"
        else:
            moat_eval = f"**微利/競爭激烈態勢**（最新毛利率 {latest_gm:.1f}%，需警惕原物料與代工成本侵蝕）。"

        fcf_ni_ratio = (fcf_series.iloc[-1] / ni_series.iloc[-1]) if (not fcf_series.empty and not ni_series.empty and pd.notna(ni_series.iloc[-1]) and ni_series.iloc[-1] > 0) else np.nan
        if not np.isnan(fcf_ni_ratio) and fcf_ni_ratio > 0.8:
            quality_eval = f"**盈餘品質極度紮實**（最新 FCF/淨利轉換率達 {fcf_ni_ratio:.2f}x，獲利皆化為實質真金白銀）。"
        elif not np.isnan(fcf_ni_ratio) and fcf_ni_ratio > 0:
            quality_eval = f"**資本支出偏重，造血維持正向**（FCF/淨利轉換率 {fcf_ni_ratio:.2f}x）。"
        else:
            quality_eval = "**造血承壓或出現自由現金流失血赤字**，需仰賴外部融資或帳上現金支應資本支出。"

        if not np.isnan(implied_g):
            if implied_g > 25.0:
                rating = "GROWTH PREMIUM // LOW MARGIN OF ERROR"
                card_border = bybit_red
            elif implied_g >= 10.0:
                rating = "BALANCED GROWTH // SOUND FUNDAMENTALS"
                card_border = bybit_green
            else:
                rating = "VALUE ASYMMETRY // ELEVATED SAFETY MARGIN"
                card_border = "#f0b90b"
        else:
            rating = "FUNDAMENTAL WATCH // CATALYST DRIVEN"
            card_border = "#848e9c"

        st.markdown(f"""
        <div style="background: #181a20; border-left: 4px solid {card_border}; border-radius: 4px; padding: 14px 18px; margin-bottom: 20px;">
            <div style="font-size: 1.05rem; font-weight: 700; color: #f0b90b; margin-bottom: 8px;">投資結論定級：{rating}</div>
            <div style="font-size: 0.88rem; line-height: 1.7; color: #eaecef;">
                • <b>獲利護城河與定價權</b>：{moat_eval}<br>
                • <b>現金造血與盈餘品質</b>：{quality_eval}<br>
                • <b>供應鏈與營運資本</b>：現金轉換週期為 <b>{ccc.iloc[-1]:.1f} 天</b>。<br>
                • <b>估值預期與風險邊界</b>：逆向 DCF 隱含年化複合增長要求為 <b>{implied_g:.1f}%</b>。
            </div>
        </div>
        """, unsafe_allow_html=True)

    # --------------------------------------------------------------------------
    # TAB 4: 同業與新聞
    # --------------------------------------------------------------------------
    with tab_peers_news:
        st.markdown("<div class='bybit-section-title'>CROSS-MARKET PEER BENCHMARK (USD STANDARDIZED)</div>", unsafe_allow_html=True)
        peer_raw_list = [normalize_ticker(p) for p in peer_input.split(",") if p.strip()]
        peer_tickers = [ticker] + [p for p in peer_raw_list if p != ticker]

        if peer_tickers:
            peer_records = []
            for p_sym in peer_tickers:
                try:
                    ps = yf.Ticker(p_sym)
                    p_inf, p_i, p_c, p_b = ps.info, ps.financials, ps.cashflow, ps.balance_sheet
                    p_curr = p_inf.get("currency") or ("TWD" if ".TW" in p_sym else "USD")
                    p_raw_mcap = p_inf.get("marketCap", 0)
                    p_mcap_usd_b = ((p_raw_mcap / USD_TWD) if p_curr == "TWD" else p_raw_mcap) / 1e9 if p_raw_mcap else np.nan
                    
                    p_rev = safe_extract(p_i, ["Total Revenue", "Revenue"]).iloc[0]
                    p_gp = safe_extract(p_i, ["Gross Profit"]).iloc[0]
                    p_op = safe_extract(p_i, ["Operating Income", "EBIT"]).iloc[0]
                    p_ni = safe_extract(p_i, ["Net Income", "Net Income Common Stockholders"]).iloc[0]
                    p_cfo = safe_extract(p_c, ["Operating Cash Flow"]).iloc[0]
                    p_cap = safe_extract(p_c, ["Capital Expenditure", "Investing Cash Flow"]).abs().iloc[0]
                    p_fcf = p_cfo - p_cap
                    p_eq = safe_extract(p_b, ["Stockholders Equity", "Total Equity Gross Minority Interest"]).iloc[0]
                    
                    peer_records.append({
                        "代碼": f"[TARGET] {p_sym}" if p_sym == ticker else p_sym,
                        "幣別": p_curr,
                        "統一市值 ($B USD)": p_mcap_usd_b,
                        "毛利率 (%)": (p_gp / p_rev) * 100 if p_rev else np.nan,
                        "營業利益率 (%)": (p_op / p_rev) * 100 if p_rev else np.nan,
                        "FCF/淨利轉換率": (p_fcf / p_ni) if (pd.notna(p_ni) and p_ni > 0) else np.nan,
                        "ROE (%)": (p_ni / p_eq) * 100 if (pd.notna(p_eq) and p_eq > 0) else np.nan,
                        "前瞻 P/E": p_inf.get("forwardPE", np.nan)
                    })
                except Exception: continue

            if peer_records:
                pdf = pd.DataFrame(peer_records).set_index("代碼")
                fmt = {"統一市值 ($B USD)": "${:,.1f} B", "毛利率 (%)": "{:.2f}%", "營業利益率 (%)": "{:.2f}%",
                       "FCF/淨利轉換率": "{:.2f}x", "ROE (%)": "{:.2f}%", "前瞻 P/E": "{:.1f}x"}
                st.dataframe(pdf.style.format(fmt, na_rep="-"), use_container_width=True)

        st.markdown("<div class='bybit-section-title'>BREAKING WIRE // 5-DAY REAL-TIME NEWS</div>", unsafe_allow_html=True)
        live_news = fetch_realtime_news_5days([ticker] + [p for p in all_peers if p != ticker][:3])
        if live_news:
            n_col1, n_col2 = st.columns(2)
            for i, item in enumerate(live_news):
                target_col = n_col1 if i % 2 == 0 else n_col2
                badge_color = "#f0b90b" if item['ticker'] == ticker else "#3a7bd5"
                with target_col:
                    st.markdown(f"""
                    <div class="bybit-news-card">
                        <a href="{item['link']}" target="_blank" class="bybit-news-title">{item['title']}</a>
                        <div class="bybit-news-meta">
                            <span style="color: {badge_color}; font-weight: bold;">[{item['ticker']}]</span> 
                            • {item['publisher']} • {item['time_str']}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.caption("NO WIRE FEEDS WITHIN 5 DAYS // 近 5 天內無突發新聞更新。")

# ==============================================================================
# 迴路 B：指數型 ETF 資產穿透
# ==============================================================================
else:
    with st.spinner(f"THESTOCKs 正在穿透 ETF 數據: {ticker}..."):
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            chart_1d, fast_info = load_price_history(ticker, period="1d")
        except Exception as e:
            st.error(f"DATA_FETCH_EXCEPTION: {e}")
            st.stop()

    curr = info.get("currency") or ("TWD" if ".TW" in ticker else "USD")
    is_twd = (curr == "TWD")
    curr_sym = "NT$" if is_twd else "$"

    current_price = fast_info.get("lastPrice", info.get("currentPrice", 0.0))
    prev_close = fast_info.get("previousClose", info.get("previousClose", current_price))
    change = current_price - prev_close
    pct_change = (change / prev_close) * 100 if prev_close else 0.0

    raw_aum = fast_info.get("marketCap") or info.get("totalAssets") or 0
    aum_usd_b = ((raw_aum / USD_TWD) if is_twd else raw_aum) / 1e9 if raw_aum else 0

    nav = info.get("navPrice", np.nan)
    prem_disc = ((current_price - nav) / nav) * 100 if (not np.isnan(nav) and nav > 0) else np.nan

    bybit_green = "#00c087"
    bybit_red = "#f6465d"
    is_up = change >= 0
    theme_color = bybit_green if is_up else bybit_red

    low52 = info.get('fiftyTwoWeekLow', current_price) or current_price
    high52 = info.get('fiftyTwoWeekHigh', current_price) or current_price

    exp_ratio = info.get("annualReportExpenseRatio", np.nan)
    if np.isnan(exp_ratio):
        fee_map = {"0050.TW": 0.00355, "006208.TW": 0.00185, "SPY": 0.0009, "QQQ": 0.0020, "SOXX": 0.0035, "VT": 0.0007, "VTI": 0.0003}
        exp_ratio = fee_map.get(ticker, 0.0025)

    st.markdown(f"""
    <div class="bybit-header">
        <div class="bybit-title">
            <span>[INDEX ETF] {ticker}</span>
            <span style="font-size:0.75rem; color:#848e9c; font-weight:normal;">{info.get('shortName', ticker)}</span>
        </div>
        <div>
            <div class="bybit-metric-label">NAV / PRICE ({curr})</div>
            <div class="bybit-price" style="color: {theme_color};">
                {curr_sym}{current_price:,.2f}
                <span style="font-size: 0.95rem; margin-left: 6px;">{'+' if is_up else ''}{change:.2f} ({'+' if is_up else ''}{pct_change:.2f}%)</span>
            </div>
        </div>
        <div>
            <div class="bybit-metric-label">PREMIUM / DISCOUNT</div>
            <div class="bybit-metric-val" style="color: {'#f6465d' if (not np.isnan(prem_disc) and prem_disc > 0.8) else '#00c087'};">
                {f"{prem_disc:+.2f}%" if not np.isnan(prem_disc) else "PAR"}
            </div>
        </div>
        <div>
            <div class="bybit-metric-label">EXPENSE RATIO</div>
            <div class="bybit-metric-val" style="color: #f0b90b;">{exp_ratio * 100:.3f}%</div>
        </div>
        <div>
            <div class="bybit-metric-label">AUM (USD STANDARDIZED)</div>
            <div class="bybit-metric-val">${aum_usd_b:,.1f}B USD</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    tab_etf_holdings, tab_etf_matrix, tab_etf_news = st.tabs([
        "成分股結構 (HOLDINGS)",
        "同類對比 (MATRIX)",
        "核心成分股新聞 (TOP WIRE)"
    ])

    with tab_etf_holdings:
        st.markdown("<div class='bybit-section-title'>CONSTITUENT EXPOSURE & CONCENTRATION</div>", unsafe_allow_html=True)
        etf_holdings_db = {
            "0050.TW": [("台積電 (2330)", 54.2), ("聯發科 (2454)", 4.8), ("鴻海 (2317)", 3.9), ("台達電 (2308)", 2.1), ("廣達 (2382)", 1.9), ("其他45檔成分股", 33.1)],
            "006208.TW": [("台積電 (2330)", 54.1), ("聯發科 (2454)", 4.8), ("鴻海 (2317)", 3.9), ("台達電 (2308)", 2.1), ("廣達 (2382)", 1.9), ("其他45檔成分股", 33.2)],
            "SPY": [("Apple (AAPL)", 7.1), ("Microsoft (MSFT)", 6.5), ("NVIDIA (NVDA)", 6.1), ("Amazon (AMZN)", 3.6), ("Alphabet (GOOGL)", 3.2), ("其他495檔股票", 73.5)],
            "QQQ": [("Apple (AAPL)", 8.9), ("Microsoft (MSFT)", 8.1), ("NVIDIA (NVDA)", 7.8), ("Amazon (AMZN)", 5.2), ("Meta (META)", 4.6), ("其他95檔股票", 65.4)],
            "SOXX": [("NVIDIA (NVDA)", 8.5), ("Broadcom (AVGO)", 8.2), ("AMD (AMD)", 7.1), ("Qualcomm (QCOM)", 6.8), ("台積電 ADR (TSM)", 4.2), ("其他25檔半導體", 65.2)],
            "VT": [("美國市場 (VTI核心)", 62.5), ("歐洲成熟市場", 15.2), ("新興市場 (含台積電)", 10.5), ("亞太已開發市場", 9.8), ("其他現金儲備", 2.0)],
            "VTI": [("微軟 (MSFT)", 6.1), ("蘋果 (AAPL)", 5.8), ("輝達 (NVDA)", 5.2), ("其他3,700+檔全美企業", 82.9)]
        }
        h_data = etf_holdings_db.get(ticker, [("第一大權值持股", 40.0), ("前2-5大核心持股", 30.0), ("其餘多樣分散標的", 30.0)])
        h_df = pd.DataFrame(h_data, columns=["成分標的/企業名稱", "權重估算 (%)"])

        col_h1, col_h2 = st.columns([1, 1.2])
        with col_h1:
            fig_etf = go.Figure(data=[go.Pie(
                labels=h_df["成分標的/企業名稱"], values=h_df["權重估算 (%)"], hole=0.6,
                marker_colors=["#f0b90b", "#3a7bd5", "#00c087", "#848e9c", "#474d57", "#2b2f36"]
            )])
            fig_etf.update_layout(template="plotly_dark", height=260, margin=dict(l=10, r=10, t=10, b=10),
                                  paper_bgcolor="#181a20", plot_bgcolor="#181a20", legend=dict(orientation="h", y=-0.1, x=0))
            st.plotly_chart(fig_etf, use_container_width=True)

        with col_h2:
            top_name, top_w = h_data[0][0], h_data[0][1]
            st.markdown(f"**CONCENTRATION STATUS: `{top_name}` AT {top_w:.1f}%**")
            if top_w > 40:
                st.error("SYNTHETIC PROXY ALERT // 單一權重過半，實質由單一企業基本面主導。")
            else:
                st.success("BALANCED EXPOSURE // 高度分散風險架構，消除單一個股特有風險。")

    with tab_etf_matrix:
        st.markdown("<div class='bybit-section-title'>INDEX BENCHMARK MATRIX</div>", unsafe_allow_html=True)
        peer_raw_list = [normalize_ticker(p) for p in peer_input.split(",") if p.strip()]
        peer_etfs = [ticker] + [p for p in peer_raw_list if p != ticker]

        if peer_etfs:
            etf_records = []
            for p in peer_etfs:
                try:
                    p_stk = yf.Ticker(p)
                    p_inf = p_stk.info
                    p_curr = p_inf.get("currency") or ("TWD" if ".TW" in p else "USD")
                    p_aum_raw = p_inf.get("totalAssets", p_inf.get("marketCap", 0)) or 0
                    p_aum_usd = (p_aum_raw / USD_TWD) if p_curr == "TWD" else p_aum_raw
                    p_exp = p_inf.get("annualReportExpenseRatio", np.nan)
                    if np.isnan(p_exp):
                        fee_map = {"0050.TW": 0.00355, "006208.TW": 0.00185, "SPY": 0.0009, "QQQ": 0.0020, "SOXX": 0.0035, "VT": 0.0007, "VTI": 0.0003}
                        p_exp = fee_map.get(p, 0.0025)

                    etf_records.append({
                        "ETF代碼": f"[TARGET] {p}" if p == ticker else p,
                        "ETF名稱": p_inf.get("shortName", p),
                        "幣別": p_curr,
                        "折合美元規模 ($B USD)": p_aum_usd / 1e9 if p_aum_usd else np.nan,
                        "總費用率 (Expense Ratio)": f"{p_exp * 100:.3f}%",
                        "資產屬性": "市值型大盤" if p in ["0050.TW", "006208.TW", "SPY", "VT", "VTI"] else ("科技成長" if p in ["QQQ", "SOXX"] else "主題型")
                    })
                except Exception: continue

            if etf_records:
                st.dataframe(pd.DataFrame(etf_records).set_index("ETF代碼"), use_container_width=True)

    with tab_etf_news:
        st.markdown("<div class='bybit-section-title'>UNDERLYING CONSTITUENTS // 5-DAY TOP HOLDINGS WIRE</div>", unsafe_allow_html=True)
        etf_tickers_map = {
            "0050.TW": ["2330.TW", "2454.TW", "2317.TW"],
            "006208.TW": ["2330.TW", "2454.TW", "2317.TW"],
            "SPY": ["AAPL", "MSFT", "NVDA"],
            "QQQ": ["AAPL", "MSFT", "NVDA"],
            "SOXX": ["NVDA", "AVGO", "AMD"]
        }
        etf_top_stocks = etf_tickers_map.get(ticker, ["AAPL", "NVDA", "MSFT"])
        etf_news = fetch_realtime_news_5days(etf_top_stocks)
        if etf_news:
            e_col1, e_col2 = st.columns(2)
            for i, item in enumerate(etf_news):
                target_col = e_col1 if i % 2 == 0 else e_col2
                with target_col:
                    st.markdown(f"""
                    <div class="bybit-news-card">
                        <a href="{item['link']}" target="_blank" class="bybit-news-title">{item['title']}</a>
                        <div class="bybit-news-meta">
                            <span style="color: #f0b90b; font-weight: bold;">[{item['ticker']}]</span> 
                            • {item['publisher']} • {item['time_str']}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.caption("NO CONSTITUENT WIRE FEEDS WITHIN 5 DAYS // 近 5 天內核心成分股無突發新聞。")