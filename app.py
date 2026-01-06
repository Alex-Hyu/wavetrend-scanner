"""
WaveTrend 扫描器 V2.0 - Streamlit 网页界面
新增: 背离检测 | RSI双重确认 | 成交量分析 | 综合评分
"""

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime

# ============================================================================
# 页面配置
# ============================================================================

st.set_page_config(
    page_title="WaveTrend 扫描器 V2.0",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# 股票池
# ============================================================================

# 纳斯达克100
NASDAQ_100 = [
    "AAPL", "MSFT", "AMZN", "NVDA", "GOOGL", "META", "GOOG", "TSLA", "AVGO", "COST",
    "PEP", "CSCO", "NFLX", "AMD", "ADBE", "TMUS", "CMCSA", "INTC", "INTU", "QCOM",
    "TXN", "AMGN", "HON", "AMAT", "BKNG", "ISRG", "SBUX", "VRTX", "LRCX", "GILD",
    "ADI", "ADP", "MDLZ", "REGN", "PANW", "MU", "KLAC", "SNPS", "CDNS", "MELI",
    "PYPL", "ASML", "MAR", "CRWD", "CTAS", "ORLY", "MRVL", "ABNB", "NXPI", "FTNT",
    "WDAY", "CSX", "PCAR", "MNST", "ADSK", "DXCM", "AEP", "CPRT", "ODFL", "PAYX",
    "AZN", "KDP", "CHTR", "ROST", "KHC", "EXC", "LULU", "IDXX", "VRSK", "MCHP",
    "FAST", "EA", "XEL", "CTSH", "GEHC", "CSGP", "BKR", "FANG", "ON", "DDOG",
    "ANSS", "BIIB", "TEAM", "ZS", "ILMN", "WBD", "ALGN", "MRNA", "DLTR", "ENPH",
    "SIRI", "CEG", "TTWO", "GFS", "LCID", "RIVN", "WBA", "JD", "PDD", "BIDU"
]

# 标普500 (不含纳斯达克100重复的)
SP500_EXTRA = [
    # 金融
    "JPM", "BAC", "WFC", "GS", "MS", "C", "BLK", "SCHW", "AXP", "USB",
    "PNC", "TFC", "COF", "BK", "STT", "AIG", "MET", "PRU", "ALL", "TRV",
    "AFL", "CB", "CME", "ICE", "MCO", "SPGI", "MMC", "AON", "MSCI",
    # 医疗
    "UNH", "JNJ", "PFE", "LLY", "ABBV", "MRK", "TMO", "ABT", "DHR", "BMY",
    "CVS", "ELV", "CI", "HCA", "HUM", "MCK", "CAH", "ZTS", "SYK",
    "BSX", "MDT", "EW", "IQV", "A", "BIO", "TECH",
    # 消费
    "WMT", "HD", "MCD", "NKE", "LOW", "TGT", "TJX", "AZO",
    "DG", "CMG", "YUM", "DPZ", "EBAY", "ETSY", "BBY",
    "KMB", "CL", "PG", "KO", "MO", "PM", "EL", "CLX", "CHD", "SJM",
    # 工业
    "CAT", "BA", "UPS", "RTX", "DE", "LMT", "GE", "MMM", "EMR",
    "ITW", "PH", "ROK", "ETN", "CMI", "WM", "RSG", "FDX", "NSC",
    "UNP", "DAL", "UAL", "LUV", "AAL",
    # 能源
    "XOM", "CVX", "COP", "SLB", "EOG", "MPC", "PSX", "VLO", "OXY", "PXD",
    "DVN", "HES", "HAL", "KMI", "WMB", "OKE",
    # 通信/媒体
    "DIS", "T", "VZ", "PARA", "FOX", "FOXA", "OMC", "IPG",
    # 公用事业
    "NEE", "DUK", "SO", "D", "SRE", "PEG", "ED", "WEC", "ES", "AWK",
    # 材料
    "LIN", "APD", "SHW", "ECL", "DD", "NEM", "FCX", "NUE", "VMC", "MLM",
    # 房地产
    "AMT", "PLD", "CCI", "EQIX", "PSA", "SPG", "O", "WELL", "DLR", "AVB",
    "EQR", "VTR", "ARE", "MAA", "UDR",
    # 其他大盘
    "BRK-B", "V", "MA", "ACN", "CRM", "ORCL", "IBM", "NOW", "UBER",
    "SQ", "SHOP", "SNOW", "NET", "ZM", "DOCU", "OKTA", "TWLO"
]

# 高波动/主题股票
EXTRA_WATCHLIST = [
    # 加密相关
    "MSTR", "COIN", "HOOD", "MARA", "RIOT", "CLSK",
    # 量子计算
    "IONQ", "RGTI", "QUBT",
    # AI/成长
    "PLTR", "SOFI", "RKLB", "PATH", "AI",
    # 中概股
    "BABA", "NIO", "XPEV", "LI"
]

# 合并所有股票池
ALL_STOCKS = list(set(NASDAQ_100 + SP500_EXTRA + EXTRA_WATCHLIST))

# ============================================================================
# 技术指标计算
# ============================================================================

def calc_wavetrend(df, n1=10, n2=21):
    ap = (df['High'] + df['Low'] + df['Close']) / 3
    esa = ap.ewm(span=n1, adjust=False).mean()
    d = (ap - esa).abs().ewm(span=n1, adjust=False).mean()
    d = d.replace(0, np.nan)
    ci = (ap - esa) / (0.015 * d)
    wt1 = ci.ewm(span=n2, adjust=False).mean()
    wt2 = wt1.rolling(window=4).mean()
    return wt1, wt2

def calc_rsi(df, period=14):
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calc_volume_ratio(df, period=20):
    vol_ma = df['Volume'].rolling(window=period).mean()
    vol_ratio = df['Volume'] / vol_ma
    return vol_ratio

# ============================================================================
# 摆动点和背离检测
# ============================================================================

def find_swing_lows(df, window=5):
    lows = []
    for i in range(window, len(df) - window):
        current_low = df['Low'].iloc[i]
        range_low = df['Low'].iloc[i-window:i+window+1].min()
        if current_low == range_low:
            lows.append(i)
    return lows

def find_swing_highs(df, window=5):
    highs = []
    for i in range(window, len(df) - window):
        current_high = df['High'].iloc[i]
        range_high = df['High'].iloc[i-window:i+window+1].max()
        if current_high == range_high:
            highs.append(i)
    return highs

def detect_divergence(df, wt1, lookback=30, swing_window=5):
    bullish_div = False
    bearish_div = False
    div_details = ""
    
    recent_df = df.iloc[-lookback:].copy()
    recent_wt1 = wt1.iloc[-lookback:].copy()
    
    # 看涨背离
    swing_lows = find_swing_lows(recent_df, window=swing_window)
    if len(swing_lows) >= 2:
        latest_idx = swing_lows[-1]
        prev_idx = swing_lows[-2]
        
        price_latest = recent_df['Low'].iloc[latest_idx]
        price_prev = recent_df['Low'].iloc[prev_idx]
        wt1_latest = recent_wt1.iloc[latest_idx]
        wt1_prev = recent_wt1.iloc[prev_idx]
        
        if price_latest < price_prev and wt1_latest > wt1_prev:
            bullish_div = True
            div_details = f"底背离: ${price_prev:.1f}→${price_latest:.1f}"
    
    # 看跌背离
    swing_highs = find_swing_highs(recent_df, window=swing_window)
    if len(swing_highs) >= 2:
        latest_idx = swing_highs[-1]
        prev_idx = swing_highs[-2]
        
        price_latest = recent_df['High'].iloc[latest_idx]
        price_prev = recent_df['High'].iloc[prev_idx]
        wt1_latest = recent_wt1.iloc[latest_idx]
        wt1_prev = recent_wt1.iloc[prev_idx]
        
        if price_latest > price_prev and wt1_latest < wt1_prev:
            bearish_div = True
            div_details = f"顶背离: ${price_prev:.1f}→${price_latest:.1f}"
    
    return bullish_div, bearish_div, div_details

# ============================================================================
# 评分系统
# ============================================================================

def calc_reversal_score(result, is_oversold=True):
    score = 0
    details = []
    
    if is_oversold:
        if result['wt1'] <= -60:
            score += 1
            details.append("WT超卖")
        if "金叉" in result.get('cross', ''):
            score += 2
            details.append("金叉")
        if result.get('wt_direction') == '↑':
            score += 1
            details.append("拐头↑")
        if result.get('bullish_div'):
            score += 2
            details.append("底背离")
        if result.get('rsi', 50) < 30:
            score += 1
            details.append("RSI<30")
        vol_ratio = result.get('vol_ratio', 1.0)
        price_change = result.get('price_change', 0)
        if vol_ratio < 0.8:
            score += 1
            details.append("缩量")
        elif vol_ratio > 1.5 and price_change > 0:
            score += 1
            details.append("放量涨")
    else:
        if result['wt1'] >= 60:
            score += 1
            details.append("WT超买")
        if "死叉" in result.get('cross', ''):
            score += 2
            details.append("死叉")
        if result.get('wt_direction') == '↓':
            score += 1
            details.append("拐头↓")
        if result.get('bearish_div'):
            score += 2
            details.append("顶背离")
        if result.get('rsi', 50) > 70:
            score += 1
            details.append("RSI>70")
        vol_ratio = result.get('vol_ratio', 1.0)
        price_change = result.get('price_change', 0)
        if vol_ratio < 0.8:
            score += 1
            details.append("缩量")
        elif vol_ratio > 1.5 and price_change < 0:
            score += 1
            details.append("放量跌")
    
    return score, details

def get_score_grade(score):
    if score >= 5:
        return "A", "⭐⭐⭐"
    elif score >= 3:
        return "B", "⭐⭐"
    elif score >= 2:
        return "C", "⭐"
    else:
        return "D", ""

# ============================================================================
# 扫描函数
# ============================================================================

@st.cache_data(ttl=300)
def scan_single_stock(symbol):
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="3mo")
        
        if len(df) < 50:
            return None
        
        info = ticker.info
        market_cap = info.get('marketCap', 0)
        
        wt1, wt2 = calc_wavetrend(df)
        rsi = calc_rsi(df)
        vol_ratio = calc_volume_ratio(df)
        
        if wt1.isna().iloc[-1]:
            return None
        
        current_wt1 = wt1.iloc[-1]
        current_wt2 = wt2.iloc[-1]
        prev_wt1 = wt1.iloc[-2] if len(wt1) > 1 else current_wt1
        prev_wt2 = wt2.iloc[-2] if len(wt2) > 1 else current_wt2
        current_price = df['Close'].iloc[-1]
        prev_price = df['Close'].iloc[-2] if len(df) > 1 else current_price
        price_change = (current_price / prev_price - 1) * 100
        current_rsi = rsi.iloc[-1]
        current_vol_ratio = vol_ratio.iloc[-1]
        
        # 金叉/死叉
        cross = ""
        if current_wt1 > current_wt2 and prev_wt1 <= prev_wt2:
            cross = "🔼 金叉"
        elif current_wt1 < current_wt2 and prev_wt1 >= prev_wt2:
            cross = "🔽 死叉"
        
        wt_direction = "↑" if current_wt1 > prev_wt1 else "↓" if current_wt1 < prev_wt1 else "→"
        
        # 背离
        bullish_div, bearish_div, div_details = detect_divergence(df, wt1)
        
        # 成交量状态
        if current_vol_ratio >= 2.0:
            vol_status = "🔥暴量"
        elif current_vol_ratio >= 1.5:
            vol_status = "📈放量"
        elif current_vol_ratio < 0.7:
            vol_status = "📉缩量"
        else:
            vol_status = "正常"
        
        result = {
            'symbol': symbol,
            'price': round(current_price, 2),
            'price_change': round(price_change, 2),
            'wt1': round(current_wt1, 2),
            'wt2': round(current_wt2, 2),
            'wt_direction': wt_direction,
            'cross': cross,
            'rsi': round(current_rsi, 1),
            'vol_ratio': round(current_vol_ratio, 2),
            'vol_status': vol_status,
            'bullish_div': bullish_div,
            'bearish_div': bearish_div,
            'div_details': div_details,
            'market_cap_b': round(market_cap / 1e9, 1) if market_cap else 0,
        }
        
        return result
    except Exception as e:
        return None

def scan_all_stocks(symbols, min_market_cap_b, ob_level, os_level, progress_bar=None):
    results = []
    skipped_no_data = 0
    skipped_market_cap = 0
    
    for i, symbol in enumerate(symbols):
        if progress_bar:
            progress_bar.progress((i + 1) / len(symbols), f"扫描中: {symbol}")
        
        result = scan_single_stock(symbol)
        
        if result is None:
            skipped_no_data += 1
            continue
        
        if result['market_cap_b'] < min_market_cap_b:
            skipped_market_cap += 1
            continue
        
        # 分类
        if result['wt1'] <= os_level:
            result['signal'] = '🟢 超卖'
            result['signal_type'] = 'oversold'
            score, details = calc_reversal_score(result, is_oversold=True)
        elif result['wt1'] >= ob_level:
            result['signal'] = '🔴 超买'
            result['signal_type'] = 'overbought'
            score, details = calc_reversal_score(result, is_oversold=False)
        elif result['wt1'] <= -53:
            result['signal'] = '🟡 接近超卖'
            result['signal_type'] = 'approaching_os'
            score, details = calc_reversal_score(result, is_oversold=True)
        elif result['wt1'] >= 53:
            result['signal'] = '🟡 接近超买'
            result['signal_type'] = 'approaching_ob'
            score, details = calc_reversal_score(result, is_oversold=False)
        else:
            result['signal'] = '⚪ 中性'
            result['signal_type'] = 'neutral'
            score, details = 0, []
        
        result['score'] = score
        result['score_details'] = ', '.join(details)
        result['grade'], result['stars'] = get_score_grade(score)
        
        results.append(result)
    
    # 调试信息
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📊 扫描统计")
    st.sidebar.markdown(f"- 总股票数: {len(symbols)}")
    st.sidebar.markdown(f"- 数据获取失败: {skipped_no_data}")
    st.sidebar.markdown(f"- 市值不足过滤: {skipped_market_cap}")
    st.sidebar.markdown(f"- 最终结果: {len(results)}")
    
    return results

# ============================================================================
# 显示结果函数
# ============================================================================

def display_results(results, scan_time):
    """显示扫描结果"""
    
    # 分类并按评分排序
    oversold = sorted([r for r in results if r['signal_type'] == 'oversold'], key=lambda x: x['score'], reverse=True)
    overbought = sorted([r for r in results if r['signal_type'] == 'overbought'], key=lambda x: x['score'], reverse=True)
    approaching_os = sorted([r for r in results if r['signal_type'] == 'approaching_os'], key=lambda x: x['score'], reverse=True)
    approaching_ob = sorted([r for r in results if r['signal_type'] == 'approaching_ob'], key=lambda x: x['score'], reverse=True)
    
    # 统计
    st.markdown("---")
    st.subheader("📈 扫描结果统计")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("🟢 超卖", len(oversold))
    with col2:
        st.metric("🟡 接近超卖", len(approaching_os))
    with col3:
        st.metric("🔴 超买", len(overbought))
    with col4:
        st.metric("🟡 接近超买", len(approaching_ob))
    
    # 高评分提示
    high_score_os = [r for r in oversold if r['score'] >= 3]
    high_score_ob = [r for r in overbought if r['score'] >= 3]
    
    if high_score_os:
        st.success(f"⭐ 高评分做多机会 (≥3分): **{', '.join([r['symbol'] for r in high_score_os])}**")
    if high_score_ob:
        st.warning(f"⭐ 高评分见顶/止盈 (≥3分): **{', '.join([r['symbol'] for r in high_score_ob])}**")
    
    st.markdown("---")
    
    # Tab 显示
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        f"🟢 超卖 ({len(oversold)})",
        f"🟡 接近超卖 ({len(approaching_os)})",
        f"🔴 超买 ({len(overbought)})",
        f"🟡 接近超买 ({len(approaching_ob)})",
        "📋 全部"
    ])
    
    def display_table(data):
        if data:
            df = pd.DataFrame(data)
            df['背离'] = df.apply(lambda x: '✅底背离' if x.get('bullish_div') else ('✅顶背离' if x.get('bearish_div') else ''), axis=1)
            df = df[['score', 'stars', 'symbol', 'price', 'price_change', 'wt1', 'wt_direction', 'rsi', 'vol_status', '背离', 'cross', 'score_details', 'market_cap_b']]
            df.columns = ['评分', '等级', '股票', '价格', '涨跌%', 'WT1', '方向', 'RSI', '成交量', '背离', '交叉', '评分详情', '市值(B)']
            st.dataframe(
                df,
                hide_index=True,
                use_container_width=True,
                column_config={
                    "价格": st.column_config.NumberColumn(format="$%.2f"),
                    "涨跌%": st.column_config.NumberColumn(format="%.2f%%"),
                    "WT1": st.column_config.NumberColumn(format="%.2f"),
                    "RSI": st.column_config.NumberColumn(format="%.1f"),
                    "市值(B)": st.column_config.NumberColumn(format="%.1f"),
                }
            )
        else:
            st.info("没有符合条件的股票")
    
    with tab1:
        st.subheader("🟢 超卖股票 (WT1 ≤ -60) - 按评分排序")
        st.markdown("*潜在做多机会，评分越高反转可能性越大*")
        display_table(oversold)
    
    with tab2:
        st.subheader("🟡 接近超卖 (-60 < WT1 ≤ -53)")
        display_table(approaching_os)
    
    with tab3:
        st.subheader("🔴 超买股票 (WT1 ≥ 60) - 按评分排序")
        st.markdown("*潜在见顶信号，考虑止盈或观望*")
        display_table(overbought)
    
    with tab4:
        st.subheader("🟡 接近超买 (53 ≤ WT1 < 60)")
        display_table(approaching_ob)
    
    with tab5:
        st.subheader("📋 全部扫描结果 - 按评分排序")
        all_sorted = sorted(results, key=lambda x: x['score'], reverse=True)
        display_table(all_sorted)
    
    st.markdown("---")
    st.caption(f"⏰ 扫描时间: {scan_time}")

# ============================================================================
# 主界面
# ============================================================================

def main():
    st.title("📊 WaveTrend 扫描器 V2.0")
    st.markdown("**新增**: 背离检测 | RSI双重确认 | 成交量分析 | 综合评分")
    
    # 初始化 session state
    if 'scan_results' not in st.session_state:
        st.session_state.scan_results = None
        st.session_state.scan_time = None
    
    # 侧边栏
    with st.sidebar:
        st.header("⚙️ 设置")
        
        min_market_cap = st.slider("最小市值 (十亿美元)", 1, 100, 10)
        ob_level = st.slider("超买阈值", 50, 80, 60)
        os_level = st.slider("超卖阈值", -80, -50, -60)
        
        if st.button("🗑️ 清除缓存"):
            st.cache_data.clear()
            st.success("缓存已清除，请重新扫描")
        
        st.markdown("---")
        st.markdown("### 📖 评分说明 (满分9分)")
        st.markdown("""
        | 条件 | 分数 |
        |------|------|
        | WT超买/超卖 | +1 |
        | 金叉/死叉 | +2 |
        | WT1拐头 | +1 |
        | 背离 | +2 |
        | RSI确认 | +1 |
        | 成交量确认 | +1 |
        """)
        st.markdown("""
        **等级**:
        - A级 (≥5分) ⭐⭐⭐ 强信号
        - B级 (3-4分) ⭐⭐ 中等
        - C级 (2分) ⭐ 弱信号
        """)
    
    # 股票池
    symbols = ALL_STOCKS.copy()
    
    # 扫描按钮
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        scan_button = st.button("🔍 开始扫描", type="primary", use_container_width=True)
    with col2:
        st.metric("股票池", f"{len(symbols)} 只")
    with col3:
        st.metric("市值筛选", f"≥ {min_market_cap}B")
    
    # 扫描逻辑
    if scan_button:
        progress_bar = st.progress(0, "准备扫描...")
        results = scan_all_stocks(symbols, min_market_cap, ob_level, os_level, progress_bar)
        progress_bar.empty()
        
        # 保存到 session state
        st.session_state.scan_results = results
        st.session_state.scan_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # 显示结果（扫描后或之前保存的）
    if st.session_state.scan_results is not None:
        display_results(st.session_state.scan_results, st.session_state.scan_time)
    else:
        st.info("👆 点击 **开始扫描** 按钮开始扫描股票")

# ============================================================================
# 运行
# ============================================================================

if __name__ == "__main__":
    main()
