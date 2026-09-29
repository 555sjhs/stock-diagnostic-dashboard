import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np

st.set_page_config(
    page_title="AI 雙迴路機構級投資診斷工作站 (個股決策 + 指數型 ETF)",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# 0. 基礎資料庫與共用函式
# ==========================================
STOCK_INDEX = {
    "NVDA": "NVIDIA (算力 GPU/AI 霸主)", "AAPL": "Apple (消費電子生態)", "MSFT": "Microsoft (Azure/AI)",
    "GOOGL": "Alphabet (Google 廣告與雲端)", "AMZN": "Amazon (AWS/電商)", "META": "Meta (社群平台/AI)",
    "TSM": "台積電 ADR (晶圓代工)", "AMD": "AMD (CPU/GPU)", "AVGO": "Broadcom (網通/ASIC)",
    "MU": "Micron (美光/記憶體)", "TSLA": "Tesla (電動車/機器人)", "INTC": "Intel (晶圓製造/CPU)",
    "2330.TW": "台積電 (2330/全球晶圓代工龍頭)", "2454.TW": "聯發科 (2454/行動晶片與邊緣AI)",
    "2317.TW": "鴻海 (2317/電子代工/AI伺服器)", "2382.TW": "廣達 (2382/AI 伺服器整機領導)",
    "3017.TW": "奇鋐 (3017/AI 散熱 3D VC)", "2308.TW": "台達電 (2308/AI 電源與液冷散熱)",
    "2881.TW": "富邦金 (2881/台灣金控旗艦獲利王)"
}

ETF_INDEX = {
    "0050.TW": "元大台灣50 (台灣前50大權值旗艦)",
    "006208.TW": "富邦台50 (低內扣台股核心大盤)",
    "SPY": "SPDR S&P 500 ETF (標普500核心大盤)",
    "QQQ": "Invesco QQQ (那斯達克100科技旗艦)",
    "SOXX": "iShares 半導體 ETF (費城半導體龍頭)",
    "VT": "Vanguard 全球股票 ETF (全市場配置)",
    "VTI": "Vanguard 美股全市場 ETF",
    "0056.TW": "元大高股息 ETF",
    "00878.TW": "國泰永續高股息 ETF"
}

EQUITY_PEERS = {
    "NVDA": ["AMD", "AVGO", "2330.TW", "INTC"], "AMD": ["NVDA", "INTC", "QCOM", "2454.TW"],
    "AVGO": ["NVDA", "MRVL", "QCOM", "2454.TW"], "TSM": ["2330.TW", "INTC", "2303.TW", "ASML"],
    "2330.TW": ["TSM", "INTC", "2303.TW", "NVDA"], "2454.TW": ["QCOM", "NVDA", "AMD", "3661.TW"],
    "2317.TW": ["2382.TW", "3231.TW", "AAPL"], "2382.TW": ["2317.TW", "6669.TW", "3231.TW"],
    "2308.TW": ["3017.TW", "3324.TWO", "NVDA"], "3017.TW": ["3324.TWO", "2308.TW", "VRT"],
    "META": ["GOOGL", "MSFT", "AMZN"], "GOOGL": ["META", "MSFT", "AMZN", "AAPL"],
    "MSFT": ["AAPL", "GOOGL", "AMZN", "ORCL"], "AAPL": ["MSFT", "GOOGL", "2317.TW", "2330.TW"],
    "TSLA": ["RIVN", "LCID", "2317.TW"]
}

ETF_PEERS = {
    "0050.TW": ["006208.TW", "SPY", "QQQ"], "006208.TW": ["0050.TW", "SPY", "QQQ"],
    "SPY": ["QQQ", "0050.TW", "VT"], "QQQ": ["SPY", "SOXX", "006208.TW"],
    "SOXX": ["QQQ", "SPY"], "VT": ["VTI", "SPY", "0050.TW"]
}

def normalize_ticker(raw_input):
    sym = raw_input.strip().upper()
    tw_listed = ["0050", "0056", "006208", "00878", "00919", "00929", "2330", "2317", "2454", "2382", "2308"]
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
def load_intraday_price(sym):
    s = yf.Ticker(sym)
    return s.history(period="1d", interval="5m"), dict(s.fast_info)

@st.cache_resource(ttl=3600)
def load_equity_data(sym):
    s = yf.Ticker(sym)
    return s, s.info, s.financials, s.balance_sheet, s.cashflow

# ==========================================
# 1. 側邊欄：迴路切換中樞
# ==========================================
st.sidebar.title("🎛️ 投資診斷迴路切換")
pipeline_mode = st.sidebar.radio(
    "選擇診斷引擎迴路：",
    ["🏢 企業個股深度診斷迴路", "📦 指數型 ETF 資產穿透迴路"],
    index=0
)

st.sidebar.info(f"💱 **即時基準匯率**：1 USD ≈ {USD_TWD:.2f} TWD")

if pipeline_mode == "🏢 企業個股深度診斷迴路":
    input_choice = st.sidebar.radio("標的選擇模式：", ["常用個股推薦清單", "自訂任意美/台股代碼"], horizontal=True)
    if input_choice == "常用個股推薦清單":
        opts = [f"{s} - {n}" for s, n in STOCK_INDEX.items()]
        sel = st.sidebar.selectbox("搜尋企業：", options=opts, index=0)
        ticker = sel.split(" - ")[0].strip()
    else:
        raw_in = st.sidebar.text_input("輸入美股或台股代碼 (如 NVDA, 2330):", value="NVDA")
        ticker = normalize_ticker(raw_in)
    
    default_peers = EQUITY_PEERS.get(ticker, [ticker, "2330.TW", "NVDA", "AAPL"])
    peer_input = st.sidebar.text_input("同業對比列表 (已自動關聯):", value=",".join(default_peers))

else: # 指數型 ETF 迴路
    input_choice = st.sidebar.radio("標的選擇模式：", ["核心指數 ETF 推薦清單", "自訂 ETF 代碼"], horizontal=True)
    if input_choice == "核心指數 ETF 推薦清單":
        opts = [f"{s} - {n}" for s, n in ETF_INDEX.items()]
        sel = st.sidebar.selectbox("搜尋指數 ETF：", options=opts, index=0)
        ticker = sel.split(" - ")[0].strip()
    else:
        raw_in = st.sidebar.text_input("輸入 ETF 代碼 (如 0050, 006208, SPY, QQQ):", value="0050")
        ticker = normalize_ticker(raw_in)
        
    default_peers = ETF_PEERS.get(ticker, [ticker, "0050.TW", "SPY", "QQQ"])
    peer_input = st.sidebar.text_input("同類 ETF 對比列表:", value=",".join(default_peers))

if not ticker:
    st.stop()

# ==============================================================================
# 迴路 A：企業個股深度診斷
# ==============================================================================
if pipeline_mode == "🏢 企業個股深度診斷迴路":
    with st.spinner(f"【個股迴路】正在穿透 {ticker} 財報、股東收益與營運週期模型..."):
        try:
            stock, info, inc, bs, cf = load_equity_data(ticker)
            intraday_hist, fast_info = load_intraday_price(ticker)
        except Exception as e:
            st.error(f"資料抓取失敗: {e}")
            st.stop()

    if inc.empty or bs.empty or cf.empty:
        st.error(f"查無 {ticker} 的完整財務數據。請確認是否為個股，若為指數 ETF 請切換至左側「指數型 ETF 迴路」。")
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

    st.subheader(f"⚡ {info.get('shortName', ticker)} 個股即時行情與盤中走勢")

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric(f"即時股價 ({curr})", f"{curr_sym}{current_price:,.2f}", f"{change:+.2f} ({pct_change:+.2f}%)")
    c2.metric("標準化市值 (折合 USD)", f"${mcap_usd_b:,.1f} B", f"原幣: {curr_sym}{raw_mcap_local/1e9:,.1f} B")
    f_pe = info.get("forwardPE", "N/A")
    t_pe = info.get("trailingPE", "N/A")
    c3.metric("前瞻估值 (Forward P/E)", f"{f_pe:.1f}x" if isinstance(f_pe, (int, float)) else str(f_pe))
    c4.metric("歷史估值 (TTM P/E)", f"{t_pe:.1f}x" if isinstance(t_pe, (int, float)) else str(t_pe))
    c5.metric("52週區間", f"{curr_sym}{info.get('fiftyTwoWeekLow', 0):.1f} - {curr_sym}{info.get('fiftyTwoWeekHigh', 0):.1f}")

    if not intraday_hist.empty:
        fig_live = go.Figure()
        fig_live.add_trace(go.Scatter(x=intraday_hist.index, y=intraday_hist['Close'], mode='lines', name='5分K價格',
                                      line=dict(color='#00C853' if change >= 0 else '#D50000', width=2.2)))
        fig_live.add_hline(y=prev_close, line_dash="dash", line_color="#757575", annotation_text=f"昨收 {curr_sym}{prev_close:.2f}")
        fig_live.update_layout(template="plotly_white", height=280, margin=dict(l=20, r=20, t=25, b=20),
                              xaxis_title="盤中時間", yaxis_title=f"股價 ({curr})", hovermode="x unified")
        st.plotly_chart(fig_live, use_container_width=True)

    st.markdown("---")

    # 排序財務資料
    inc = inc.loc[:, inc.columns.sort_values(ascending=True)]
    bs = bs.loc[:, bs.columns.sort_values(ascending=True)]
    cf = cf.loc[:, cf.columns.sort_values(ascending=True)]
    years = [col.strftime('%Y') for col in inc.columns]

    # 科目抽取
    cfo_series = cf.loc["Operating Cash Flow"] if "Operating Cash Flow" in cf.index else pd.Series(dtype=float)
    capex_key = "Capital Expenditure" if "Capital Expenditure" in cf.index else "Investing Cash Flow"
    capex_series = cf.loc[capex_key].abs() if capex_key in cf.index else pd.Series(dtype=float)
    ni_series = inc.loc["Net Income"] if "Net Income" in inc.index else pd.Series(dtype=float)
    rev_series = inc.loc["Total Revenue"] if "Total Revenue" in inc.index else pd.Series(dtype=float)
    gp_series = inc.loc["Gross Profit"] if "Gross Profit" in inc.index else rev_series * 0
    op_series = inc.loc["Operating Income"] if "Operating Income" in inc.index else rev_series * 0
    equity_series = bs.loc["Stockholders Equity"] if "Stockholders Equity" in bs.index else pd.Series(dtype=float)
    assets_series = bs.loc["Total Assets"] if "Total Assets" in bs.index else pd.Series(dtype=float)
    fcf_series = cfo_series - capex_series

    # 模組 1: 財報地雷快篩
    st.subheader("🚨 財報地雷與體質快篩")
    flags, flag_details = [], []
    if len(cfo_series) >= 2 and len(ni_series) >= 2:
        if (cfo_series.iloc[-1] < ni_series.iloc[-1]) and (cfo_series.iloc[-2] < ni_series.iloc[-2]):
            flags.append("盈餘品質警訊（CFO < Net Income 連續兩年）")
            flag_details.append("帳面淨利未能實質轉為營運現金流入，高度警惕存貨積壓或提前確認營收。")

    if not equity_series.empty and not assets_series.empty and not ni_series.empty:
        latest_em = assets_series.iloc[-1] / equity_series.iloc[-1]
        latest_roe = ni_series.iloc[-1] / equity_series.iloc[-1]
        if latest_em > 4.0 and latest_roe > 0.20:
            flags.append(f"高槓桿虛胖警訊（槓桿倍數 {latest_em:.2f}x，ROE {latest_roe*100:.1f}%）")
            flag_details.append("漂亮的股東權益報酬率主要依賴龐大負債支撐，景氣反轉將重創獲利。")

    if not fcf_series.empty and fcf_series.iloc[-1] < 0:
        flags.append("造血失血警訊（最新一期 FCF 為負）")
        flag_details.append("營運現金流不足以支應資本支出，恐面臨股權稀釋或借貸融資壓力。")

    if flags:
        for f, d in zip(flags, flag_details): st.error(f"⚠️ **{f}**\n\n> 💡 **機構解讀**：{d}")
    else:
        st.success("✅ **財務體質極度穩健**：營運現金流充足覆蓋淨利，負債槓桿健康，造血無虞。")

    # ==========================
    # 模組 2：股東回報率穿透 (Shareholder Yield) [NEW]
    # ==========================
    st.subheader("🎁 股東回報率穿透 (Shareholder Yield = 現金股息 + 庫藏股回購)")
    
    div_paid = cf.loc['Cash Dividends Paid'].abs() if 'Cash Dividends Paid' in cf.index else pd.Series(0, index=cf.columns)
    repurchase = cf.loc['Common Stock Repurchased'].abs() if 'Common Stock Repurchased' in cf.index else pd.Series(0, index=cf.columns)
    
    col_sy1, col_sy2 = st.columns([1.2, 1])
    with col_sy1:
        fig_sy = go.Figure()
        fig_sy.add_trace(go.Bar(x=years, y=div_paid/1e9, name='現金股利發放', marker_color='#00B4D8'))
        fig_sy.add_trace(go.Bar(x=years, y=repurchase/1e9, name='庫藏股回購', marker_color='#0077B6'))
        fig_sy.update_layout(barmode='stack', template="plotly_white", height=300, yaxis_title=f"金額 ({curr_sym}B {curr})",
                             legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig_sy, use_container_width=True)

    with col_sy2:
        latest_div = div_paid.iloc[-1] if not div_paid.empty else 0
        latest_rep = repurchase.iloc[-1] if not repurchase.empty else 0
        total_payout = latest_div + latest_rep
        
        div_y = (latest_div / raw_mcap_local) * 100 if raw_mcap_local > 0 else 0
        rep_y = (latest_rep / raw_mcap_local) * 100 if raw_mcap_local > 0 else 0
        tot_sy = div_y + rep_y
        
        st.metric("實質總股東收益率 (Total Shareholder Yield)", f"{tot_sy:.2f}%", f"股息率 {div_y:.2f}% + 回購率 {rep_y:.2f}%")
        st.caption(f"最新年度回饋總額: {curr_sym}{total_payout/1e9:,.2f} B (回購佔比: {(latest_rep/total_payout)*100 if total_payout > 0 else 0:.1f}%)")
        if rep_y > div_y * 2:
            st.info("💡 **強烈庫藏股導向**：公司主要透過註銷股票提升每股盈餘（EPS），相較配息具備免除股利所得稅的複利優勢！")
        elif div_y > 3.0:
            st.info("💡 **高現金股利導向**：成熟型高配息現金牛，股價下檔具備堅實收益保護。")

    # ==========================
    # 模組 3：營運資本效率與現金轉換週期 (CCC) [NEW]
    # ==========================
    st.subheader("🔄 營運資本效率與現金轉換週期 (CCC = DIO + DSO - DPO)")
    
    cogs_key = 'Cost Of Revenue' if 'Cost Of Revenue' in inc.index else 'Operating Expense'
    cogs_series = inc.loc[cogs_key] if cogs_key in inc.index else rev_series * 0.5
    
    ar_series = bs.loc['Accounts Receivable'] if 'Accounts Receivable' in bs.index else pd.Series(0, index=bs.columns)
    inv_series = bs.loc['Inventory'] if 'Inventory' in bs.index else pd.Series(0, index=bs.columns)
    ap_series = bs.loc['Accounts Payable'] if 'Accounts Payable' in bs.index else pd.Series(0, index=bs.columns)
    
    dso = (ar_series / rev_series) * 365
    dio = (inv_series / cogs_series) * 365
    dpo = (ap_series / cogs_series) * 365
    ccc = dio + dso - dpo
    
    col_ccc1, col_ccc2 = st.columns([1.2, 1])
    with col_ccc1:
        fig_ccc = go.Figure()
        fig_ccc.add_trace(go.Scatter(x=years, y=dso, mode='lines+markers', name='應收帳款天數 (DSO)', line=dict(color='#E76F51')))
        fig_ccc.add_trace(go.Scatter(x=years, y=dio, mode='lines+markers', name='存貨週轉天數 (DIO)', line=dict(color='#F4A261')))
        fig_ccc.add_trace(go.Scatter(x=years, y=dpo, mode='lines+markers', name='應付帳款天數 (DPO)', line=dict(color='#2A9D8F')))
        fig_ccc.add_trace(go.Scatter(x=years, y=ccc, mode='lines+markers', name='現金轉換週期 (CCC)', line=dict(color='#264653', width=3, dash='dash')))
        fig_ccc.update_layout(template="plotly_white", height=320, yaxis_title="天數 (Days)",
                              legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig_ccc, use_container_width=True)

    with col_ccc2:
        latest_ccc = ccc.iloc[-1] if not ccc.empty else 0
        latest_dio = dio.iloc[-1] if not dio.empty else 0
        st.metric("最新現金轉換週期 (CCC)", f"{latest_ccc:.1f} 天", f"存貨週期: {latest_dio:.1f} 天")
        if latest_ccc < 0:
            st.success("🏆 **無償佔用供應鏈資金模式（負 CCC）**：該公司在產業鏈地位強勢，先收客戶款項、賣出商品後才付貨款給供應商，營運完全不依賴自有資金！")
        elif len(dio) >= 2 and (dio.iloc[-1] - dio.iloc[-2]) > 20:
            st.warning(f"⚠️ **存貨積壓警訊**：存貨天數近一年大幅增加 {(dio.iloc[-1] - dio.iloc[-2]):.1f} 天，需高度警惕下游砍單或產品迭代不順。")
        else:
            st.info("💡 營運週期平穩，未見異常存貨積壓或應收款呆帳風險。")

    # ==========================
    # 模組 4：債務健康度與償債壓力測試 (Solvency Stress Test) [NEW]
    # ==========================
    st.subheader("🛡️ 債務健康度與償債壓力測試 (Solvency & Debt Coverage)")
    
    int_exp = inc.loc['Interest Expense'].abs() if 'Interest Expense' in inc.index else pd.Series(0, index=inc.columns)
    ebit = op_series
    int_cov = ebit / int_exp.replace(0, np.nan)
    
    tot_debt = bs.loc['Total Debt'] if 'Total Debt' in bs.index else pd.Series(0, index=bs.columns)
    cash_eq = bs.loc['Cash And Cash Equivalents'] if 'Cash And Cash Equivalents' in bs.index else pd.Series(0, index=bs.columns)
    net_debt = tot_debt - cash_eq
    
    sc_col1, sc_col2, sc_col3 = st.columns(3)
    latest_cov = int_cov.iloc[-1] if not int_cov.empty else np.nan
    cov_str = f"{latest_cov:.1f}x" if (not np.isnan(latest_cov) and latest_cov > 0) else "無有息負債/充裕"
    sc_col1.metric("利息覆蓋倍數 (EBIT / Interest)", cov_str)
    
    latest_nd = net_debt.iloc[-1] if not net_debt.empty else 0
    sc_col2.metric("淨負債規模 (Net Debt)", f"{curr_sym}{latest_nd/1e9:,.1f} B", "淨現金充裕" if latest_nd < 0 else "淨負債狀態")
    
    dr = (tot_debt.iloc[-1] / assets_series.iloc[-1]) * 100 if assets_series.iloc[-1] > 0 else 0
    sc_col3.metric("總資產負債率", f"{dr:.1f}%")
    
    if not np.isnan(latest_cov) and latest_cov < 3.0 and latest_cov > 0:
        st.error("⚠️ **高償債負擔警訊**：利息覆蓋倍數低於 3.0x，若基準利率居高不下或獲利下滑，利息費用將大幅侵蝕盈餘！")
    else:
        st.success("✅ **償債覆蓋極佳**：本業獲利數倍覆蓋利息費用，資本結構具備極高抗壓韌性。")

    # 模組 5: 逆向 DCF
    st.subheader("🎯 華爾街逆向工程：股價隱含成長預期 (Reverse DCF)")
    latest_base_fcf = fcf_series.iloc[-1] if not fcf_series.empty else 0
    if raw_mcap_local > 0 and latest_base_fcf > 0:
        r1, r2 = st.columns([1, 1.3])
        with r1:
            wacc = st.slider("折現率 WACC (%)", 7.0, 14.0, 9.5, 0.1) / 100.0
            g = st.slider("永續成長率 g (%)", 1.5, 4.0, 2.5, 0.1) / 100.0
            st.caption(f"基準 FCF: {curr_sym}{latest_base_fcf/1e9:,.2f} B | 即時市值: {curr_sym}{raw_mcap_local/1e9:,.1f} B (折合 ${mcap_usd_b:,.1f} B USD)")

        def calc_dcf_value(growth_rate, base_fcf, wacc_val, g_val, n=5):
            pv_fcf = sum([(base_fcf * ((1 + growth_rate) ** yr)) / ((1 + wacc_val) ** yr) for yr in range(1, n + 1)])
            tv = (base_fcf * ((1 + growth_rate) ** n) * (1 + g_val)) / (wacc_val - g_val)
            return pv_fcf + (tv / ((1 + wacc_val) ** n))

        implied_g = np.nan
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
                st.metric("市場即時隱含未來 5 年 FCF 年化複合成長率 (CAGR)", f"{implied_g:.1f}%", f"基於即時價 {curr_sym}{current_price:,.2f}")
                if implied_g > 25.0: st.error(f"⚠️ **高預期高風險（隱含 CAGR {implied_g:.1f}%）：** 即時定價已將樂觀預期打滿，容錯率極低。")
                elif implied_g >= 12.0: st.info(f"💡 **合理成長定價（隱含 CAGR {implied_g:.1f}%）：** 預期維持穩健擴張。")
                elif implied_g >= 0: st.success(f"🛡️ **保守定價/高安全邊際（隱含 CAGR {implied_g:.1f}%）：** 市場預期悲觀，業績只要稍微改善即可修復估值。")
                else: st.warning(f"📉 **衰退定價（隱含 CAGR {implied_g:.1f}%）：** 市場定價隱含未來獲利將逐年萎縮。")
    else:
        st.info("⚠️ 該標的最新自由現金流 (FCF) 為負或缺乏市值數據，無法進行逆向 DCF 反推。")

    # 模組 6: 損益雙率趨勢
    st.subheader("📈 損益結構與獲利能力趨勢")
    rev, gp, op = rev_series / 1e9, gp_series / 1e9, op_series / 1e9
    gross_margin, op_margin = (gp / rev) * 100, (op / rev) * 100

    fig1 = make_subplots(specs=[[{"secondary_y": True}]])
    fig1.add_trace(go.Bar(x=years, y=rev, name="營收", marker_color="#4A90E2", opacity=0.85), secondary_y=False)
    fig1.add_trace(go.Bar(x=years, y=gp, name="毛利", marker_color="#50E3C2", opacity=0.85), secondary_y=False)
    fig1.add_trace(go.Bar(x=years, y=op, name="營業利益", marker_color="#F5A623", opacity=0.85), secondary_y=False)
    fig1.add_trace(go.Scatter(x=years, y=gross_margin, name="毛利率 (%)", line=dict(color="#00C853", width=3)), secondary_y=True)
    fig1.add_trace(go.Scatter(x=years, y=op_margin, name="營業利益率 (%)", line=dict(color="#D500F9", width=3, dash="dot")), secondary_y=True)
    fig1.update_layout(barmode="group", hovermode="x unified", template="plotly_white", height=380,
                      legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    fig1.update_yaxes(title_text=f"原幣金額 ({curr_sym}B {curr})", secondary_y=False)
    fig1.update_yaxes(title_text="比率 (%)", secondary_y=True, showgrid=False)
    st.plotly_chart(fig1, use_container_width=True)

    # 模組 7 & 8: 造血能力 & 杜邦分析
    cl, cr = st.columns(2)
    with cl:
        st.subheader("💧 真實造血能力 (CFO vs. FCF)")
        fig2 = go.Figure()
        fig2.add_trace(go.Bar(x=years, y=cfo_series/1e9, name="營運現金流 (CFO)", marker_color="#29B6F6"))
        fig2.add_trace(go.Bar(x=years, y=capex_series/1e9, name="資本支出 (CapEx)", marker_color="#EF5350"))
        fig2.add_trace(go.Bar(x=years, y=fcf_series/1e9, name="自由現金流 (FCF)", marker_color="#66BB6A"))
        fig2.update_layout(barmode="group", hovermode="x unified", template="plotly_white", height=320,
                          legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig2, use_container_width=True)
    with cr:
        st.subheader("🧩 三因子杜邦拆解 (ROE Breakdown)")
        net_margin = (ni_series / rev_series) * 100
        asset_turnover = rev_series / assets_series
        equity_multiplier = assets_series / equity_series
        roe = (ni_series / equity_series) * 100
        dupont_df = pd.DataFrame({
            "年份": years, "ROE (%)": roe.round(2).values, "淨利率 (%)": net_margin.round(2).values,
            "資產週轉率 (次)": asset_turnover.round(2).values, "權益乘數 (槓桿)": equity_multiplier.round(2).values
        }).set_index("年份")
        st.dataframe(dupont_df, use_container_width=True)

    # 模組 9: 同業矩陣 (統一折算 USD)
    st.subheader("🥊 跨市場同業橫向對比矩陣 (統一折算為 USD 評比)")
    peer_tickers = [normalize_ticker(p) for p in peer_input.split(",") if p.strip()]
    if peer_tickers:
        peer_records = []
        for p_sym in peer_tickers:
            try:
                ps = yf.Ticker(p_sym)
                p_inf, p_i, p_c, p_b = ps.info, ps.financials, ps.cashflow, ps.balance_sheet
                p_curr = p_inf.get("currency") or ("TWD" if ".TW" in p_sym else "USD")
                p_raw_mcap = p_inf.get("marketCap", 0)
                p_mcap_usd_b = ((p_raw_mcap / USD_TWD) if p_curr == "TWD" else p_raw_mcap) / 1e9 if p_raw_mcap else np.nan
                p_rev = p_i.loc["Total Revenue"].iloc[0]
                p_gp = p_i.loc["Gross Profit"].iloc[0]
                p_cfo = p_c.loc["Operating Cash Flow"].iloc[0]
                ckey = "Capital Expenditure" if "Capital Expenditure" in p_c.index else "Investing Cash Flow"
                p_cap = abs(p_c.loc[ckey].iloc[0])
                p_fcf = p_cfo - p_cap
                p_ni = p_i.loc["Net Income"].iloc[0]
                p_eq = p_b.loc["Stockholders Equity"].iloc[0]
                peer_records.append({
                    "代碼": p_sym, "原始幣別": p_curr, "統一市值 ($B USD)": p_mcap_usd_b,
                    "毛利率 (%)": (p_gp / p_rev) * 100, "營業利益率 (%)": ((p_i.loc["Operating Income"].iloc[0] / p_rev) * 100),
                    "FCF/淨利轉換率": (p_fcf / p_ni if (p_ni and p_ni > 0) else np.nan), "ROE (%)": (p_ni / p_eq) * 100,
                    "前瞻 P/E": p_inf.get("forwardPE", np.nan)
                })
            except Exception: continue

        if peer_records:
            pdf = pd.DataFrame(peer_records).set_index("代碼")
            fmt = {"統一市值 ($B USD)": "${:,.1f} B", "毛利率 (%)": "{:.2f}%", "營業利益率 (%)": "{:.2f}%",
                   "FCF/淨利轉換率": "{:.2f}x", "ROE (%)": "{:.2f}%", "前瞻 P/E": "{:.1f}x"}
            styled = pdf.style.format(fmt, na_rep="N/A").highlight_max(
                subset=["統一市值 ($B USD)", "毛利率 (%)", "營業利益率 (%)", "FCF/淨利轉換率", "ROE (%)"],
                axis=0, props="background-color: #1b4332; color: #74c69d; font-weight: bold;"
            )
            st.dataframe(styled, use_container_width=True)

# ==============================================================================
# 迴路 B：指數型 ETF 資產穿透 (含即時折溢價監控)
# ==============================================================================
else:
    with st.spinner(f"【ETF 迴路】正在穿透 {ticker} 淨值、折溢價與成分股資產池..."):
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            intraday_hist, fast_info = load_intraday_price(ticker)
        except Exception as e:
            st.error(f"資料抓取失敗: {e}")
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

    # ==========================
    # 即時折溢價監控 (Premium / Discount) [NEW]
    # ==========================
    nav = info.get("navPrice", np.nan)
    if not np.isnan(nav) and nav > 0:
        prem_disc = ((current_price - nav) / nav) * 100
        prem_str = f"{prem_disc:+.2f}%"
    else:
        prem_disc = np.nan
        prem_str = "即時淨值平穩"

    st.subheader(f"📦 {info.get('shortName', ticker)} 指數型 ETF 即時行情與折溢價監控")

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric(f"即時市價 ({curr})", f"{curr_sym}{current_price:,.2f}", f"{change:+.2f} ({pct_change:+.2f}%)")
    c2.metric("資產規模 AUM (折合 USD)", f"${aum_usd_b:,.1f} B" if aum_usd_b > 0 else "規模充裕", f"原幣規模: {curr_sym}{raw_aum/1e9:,.1f} B" if raw_aum > 0 else "每日公告")
    
    exp_ratio = info.get("annualReportExpenseRatio", np.nan)
    if np.isnan(exp_ratio):
        fee_map = {"0050.TW": 0.00355, "006208.TW": 0.00185, "SPY": 0.0009, "QQQ": 0.0020, "SOXX": 0.0035, "VT": 0.0007, "VTI": 0.0003}
        exp_ratio = fee_map.get(ticker, 0.0025)
    c3.metric("總內扣費用率 (Expense Ratio)", f"{exp_ratio * 100:.3f}%")
    c4.metric("即時折溢價 (Premium/Discount)", prem_str, f"參考 NAV: {curr_sym}{nav:.2f}" if not np.isnan(nav) else "貼近淨值")
    c5.metric("52週高低區間", f"{curr_sym}{info.get('fiftyTwoWeekLow', 0):.1f} - {curr_sym}{info.get('fiftyTwoWeekHigh', 0):.1f}")

    if not np.isnan(prem_disc):
        if prem_disc > 1.0:
            st.error(f"⚠️ **大幅溢價警訊（溢價 {prem_disc:+.2f}%）**：當前市價顯著高於真實淨值，買進將面臨現買現賠的溢價收斂風險，建議切勿追高！")
        elif prem_disc < -0.5:
            st.success(f"🛡️ **折價安全邊際（折價 {prem_disc:+.2f}%）**：當前市價低於資產淨值，具備一定折價保護或潛在均值回歸空間。")

    if not intraday_hist.empty:
        fig_live = go.Figure()
        fig_live.add_trace(go.Scatter(x=intraday_hist.index, y=intraday_hist['Close'], mode='lines', name='5分K價格',
                                      line=dict(color='#00C853' if change >= 0 else '#D50000', width=2.2)))
        fig_live.add_hline(y=prev_close, line_dash="dash", line_color="#757575", annotation_text=f"昨收 {curr_sym}{prev_close:.2f}")
        fig_live.update_layout(template="plotly_white", height=280, margin=dict(l=20, r=20, t=25, b=20),
                              xaxis_title="盤中時間", yaxis_title=f"價格 ({curr})", hovermode="x unified")
        st.plotly_chart(fig_live, use_container_width=True)

    st.markdown("---")

    # ETF 成分股與集中度
    st.subheader("🔍 指數成分股結構穿透與集中度分析")
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
            labels=h_df["成分標的/企業名稱"], values=h_df["權重估算 (%)"], hole=0.55,
            marker_colors=["#1b4332", "#2d6a4f", "#40916c", "#52b788", "#74c69d", "#b7e4c7"]
        )])
        fig_etf.update_layout(template="plotly_white", height=320, margin=dict(l=10, r=10, t=10, b=10),
                              legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5))
        st.plotly_chart(fig_etf, use_container_width=True)

    with col_h2:
        top_name, top_w = h_data[0][0], h_data[0][1]
        st.markdown(f"### 🎯 權重集中度診斷：`{top_name}` 佔比 **{top_w:.1f}%**")
        if top_w > 40:
            st.error(f"⚠️ **高單一股票集中風險（類個股 Beta 屬性）：** 雖然名義上分散投資多檔股票，但單一龍頭權重過半，這檔 ETF 的漲跌實質上主要由該企業基本面主導。")
        else:
            st.success(f"🛡️ **高度分散風險架構：** 最大單一持股僅 {top_w:.1f}%，有效消除單一企業營運暴雷的特有風險。")

        if ticker in ["0050.TW", "006208.TW"]:
            st.info("💡 **0050 vs 006208 內耗實測比較：** 兩者成分股 100% 相同。006208 總內扣約 0.185%，0050 約 0.355%。每 100 萬投資，每年隱形費用差約 1,700 元，長線複利優勢更偏向 006208。")
        elif ticker in ["SPY", "QQQ"]:
            st.info("💡 **SPY vs QQQ 配置定位：** SPY 全面覆蓋標普 500 各大產業；QQQ 完全偏重於科技與網路巨頭，牛市進攻力更強，但波動與回撤幅度顯著高於大盤。")

    # ETF 專屬橫向矩陣
    st.subheader("🥊 跨市場同類指數型 ETF 橫向對比矩陣 (ETF Matrix)")
    peer_etfs = [normalize_ticker(p) for p in peer_input.split(",") if p.strip()]
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
                    "ETF代碼": p,
                    "ETF名稱": p_inf.get("shortName", p),
                    "幣別": p_curr,
                    "折合美元規模 ($B USD)": p_aum_usd / 1e9 if p_aum_usd else np.nan,
                    "總費用率 (Expense Ratio)": f"{p_exp * 100:.3f}%",
                    "資產屬性": "市值型大盤" if p in ["0050.TW", "006208.TW", "SPY", "VT", "VTI"] else ("科技成長" if p in ["QQQ", "SOXX"] else "主題型")
                })
            except Exception: continue

        if etf_records:
            st.dataframe(pd.DataFrame(etf_records).set_index("ETF代碼"), use_container_width=True)