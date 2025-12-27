"""
WaveTrend 扫描器 - Streamlit 网页界面
"""

import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime
import yfinance as yf
import numpy as np

# ============================================================================
# 页面配置
# ============================================================================

st.set_page_config(
    page_title="WaveTrend 扫描器",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# 样式
# ============================================================================

st.markdown("""
<style>
    .big-font {
        font-size: 24px !important;
        font-weight: bold;
    }
    .metric-card {
        background-color: #1E1E1E;
        border-radius: 10px;
        padding: 20px;
        margin: 10px 0;
    }
    .oversold {
        color: #00FF88;
    }
    .overbought {
        color: #FF4444;
    }
    .neutral {
        color: #FFAA00;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# WaveTrend 计算函数
# ============================================================================

def calc_wavetrend(df, n1=10, n2=21):
    """计算 WaveTrend 指标"""
    ap = (df['High'] + df['Low'] + df['Close']) / 3
    esa = ap.ewm(span=n1, adjust=False).mean()
    d = (ap - esa).abs().ewm(span=n1, adjust=False).mean()
    d = d.replace(0, np.nan)
    ci = (ap - esa) / (0.015 * d)
    wt1 = ci.ewm(span=n2, adjust=False).mean()
    wt2 = wt1.rolling(window=4).mean()
    return wt1, wt2

# ============================================================================
# 股票池定义
# ============================================================================

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

EXTRA_WATCHLIST = [
    "MSTR", "COIN", "HOOD", "CRWV", "PLTR", "SOFI", "RKLB", "IONQ", "RGTI", "QUBT"
]

# ============================================================================
# 扫描函数
# ============================================================================

@st.cache_data(ttl=300)  # 缓存5分钟
def scan_single_stock(symbol):
    """扫描单只股票"""
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="3mo")
        
        if len(df) < 50:
            return None
        
        info = ticker.info
        market_cap = info.get('marketCap', 0)
        
        wt1, wt2 = calc_wavetrend(df)
        
        if wt1.isna().iloc[-1]:
            return None
        
        current_wt1 = wt1.iloc[-1]
        current_wt2 = wt2.iloc[-1]
        prev_wt1 = wt1.iloc[-2] if len(wt1) > 1 else current_wt1
        prev_wt2 = wt2.iloc[-2] if len(wt2) > 1 else current_wt2
        current_price = df['Close'].iloc[-1]
        prev_price = df['Close'].iloc[-2] if len(df) > 1 else current_price
        price_change = (current_price / prev_price - 1) * 100
        
        # 判断交叉
        cross = ""
        if current_wt1 > current_wt2 and prev_wt1 <= prev_wt2:
            cross = "🔼 金叉"
        elif current_wt1 < current_wt2 and prev_wt1 >= prev_wt2:
            cross = "🔽 死叉"
        
        wt_direction = "↑" if current_wt1 > prev_wt1 else "↓" if current_wt1 < prev_wt1 else "→"
        
        # 信号判断
        if current_wt1 >= 60:
            signal = "🔴 超买"
            signal_type = "overbought"
        elif current_wt1 <= -60:
            signal = "🟢 超卖"
            signal_type = "oversold"
        elif current_wt1 >= 53:
            signal = "🟡 接近超买"
            signal_type = "approaching_ob"
        elif current_wt1 <= -53:
            signal = "🟡 接近超卖"
            signal_type = "approaching_os"
        else:
            signal = "⚪ 中性"
            signal_type = "neutral"
        
        return {
            'symbol': symbol,
            'price': round(current_price, 2),
            'price_change': round(price_change, 2),
            'wt1': round(current_wt1, 2),
            'wt2': round(current_wt2, 2),
            'wt_direction': wt_direction,
            'cross': cross,
            'market_cap_b': round(market_cap / 1e9, 1) if market_cap else 0,
            'signal': signal,
            'signal_type': signal_type
        }
    except Exception as e:
        return None

def scan_all_stocks(symbols, min_market_cap_b=10, progress_bar=None):
    """扫描所有股票"""
    results = []
    
    for i, symbol in enumerate(symbols):
        if progress_bar:
            progress_bar.progress((i + 1) / len(symbols), f"扫描中: {symbol}")
        
        result = scan_single_stock(symbol)
        if result and result['market_cap_b'] >= min_market_cap_b:
            results.append(result)
    
    return results

# ============================================================================
# 主界面
# ============================================================================

def main():
    st.title("📊 WaveTrend 日线扫描器")
    st.markdown("扫描纳斯达克100及高波动股票，寻找超买/超卖机会")
    
    # 侧边栏设置
    with st.sidebar:
        st.header("⚙️ 设置")
        
        min_market_cap = st.slider(
            "最小市值 (十亿美元)",
            min_value=1,
            max_value=100,
            value=10,
            step=1
        )
        
        ob_level = st.slider(
            "超买阈值",
            min_value=50,
            max_value=80,
            value=60
        )
        
        os_level = st.slider(
            "超卖阈值",
            min_value=-80,
            max_value=-50,
            value=-60
        )
        
        include_extra = st.checkbox("包含高波动股票 (MSTR, COIN等)", value=True)
        
        st.markdown("---")
        st.markdown("### 📖 WaveTrend 说明")
        st.markdown("""
        - **WT1 ≥ 60**: 超买，可能见顶
        - **WT1 ≤ -60**: 超卖，可能见底
        - **金叉**: WT1上穿WT2，看涨
        - **死叉**: WT1下穿WT2，看跌
        """)
    
    # 股票池
    symbols = NASDAQ_100.copy()
    if include_extra:
        symbols = list(set(symbols + EXTRA_WATCHLIST))
    
    # 扫描按钮
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        scan_button = st.button("🔍 开始扫描", type="primary", use_container_width=True)
    with col2:
        st.metric("股票池", f"{len(symbols)} 只")
    with col3:
        st.metric("市值筛选", f"≥ {min_market_cap}B")
    
    if scan_button:
        # 进度条
        progress_bar = st.progress(0, "准备扫描...")
        
        # 扫描
        results = scan_all_stocks(symbols, min_market_cap, progress_bar)
        progress_bar.empty()
        
        # 分类结果
        oversold = [r for r in results if r['wt1'] <= os_level]
        overbought = [r for r in results if r['wt1'] >= ob_level]
        approaching_os = [r for r in results if os_level < r['wt1'] <= -53]
        approaching_ob = [r for r in results if 53 <= r['wt1'] < ob_level]
        
        # 显示统计
        st.markdown("---")
        st.subheader("📈 扫描结果统计")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("🟢 超卖", len(oversold), help="潜在做多机会")
        with col2:
            st.metric("🟡 接近超卖", len(approaching_os))
        with col3:
            st.metric("🔴 超买", len(overbought), help="潜在见顶/止盈")
        with col4:
            st.metric("🟡 接近超买", len(approaching_ob))
        
        st.markdown("---")
        
        # Tab 显示详细结果
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            f"🟢 超卖 ({len(oversold)})",
            f"🟡 接近超卖 ({len(approaching_os)})",
            f"🔴 超买 ({len(overbought)})",
            f"🟡 接近超买 ({len(approaching_ob)})",
            "📋 全部"
        ])
        
        def display_table(data, title):
            if data:
                df = pd.DataFrame(data)
                df = df[['symbol', 'price', 'price_change', 'wt1', 'wt2', 'wt_direction', 'cross', 'market_cap_b', 'signal']]
                df.columns = ['股票', '价格', '涨跌%', 'WT1', 'WT2', '方向', '交叉', '市值(B)', '信号']
                st.dataframe(
                    df,
                    hide_index=True,
                    use_container_width=True,
                    column_config={
                        "价格": st.column_config.NumberColumn(format="$%.2f"),
                        "涨跌%": st.column_config.NumberColumn(format="%.2f%%"),
                        "WT1": st.column_config.NumberColumn(format="%.2f"),
                        "WT2": st.column_config.NumberColumn(format="%.2f"),
                        "市值(B)": st.column_config.NumberColumn(format="%.1f"),
                    }
                )
            else:
                st.info(f"没有{title}信号")
        
        with tab1:
            st.subheader("🟢 超卖股票 (WT1 ≤ -60)")
            st.markdown("*潜在做多机会，注意确认反转信号*")
            oversold_sorted = sorted(oversold, key=lambda x: x['wt1'])
            display_table(oversold_sorted, "超卖")
        
        with tab2:
            st.subheader("🟡 接近超卖 (-60 < WT1 ≤ -53)")
            st.markdown("*观察名单，可能即将触发超卖*")
            approaching_os_sorted = sorted(approaching_os, key=lambda x: x['wt1'])
            display_table(approaching_os_sorted, "接近超卖")
        
        with tab3:
            st.subheader("🔴 超买股票 (WT1 ≥ 60)")
            st.markdown("*潜在见顶信号，考虑止盈或观望*")
            overbought_sorted = sorted(overbought, key=lambda x: x['wt1'], reverse=True)
            display_table(overbought_sorted, "超买")
        
        with tab4:
            st.subheader("🟡 接近超买 (53 ≤ WT1 < 60)")
            st.markdown("*观察名单，可能即将触发超买*")
            approaching_ob_sorted = sorted(approaching_ob, key=lambda x: x['wt1'], reverse=True)
            display_table(approaching_ob_sorted, "接近超买")
        
        with tab5:
            st.subheader("📋 全部扫描结果")
            all_sorted = sorted(results, key=lambda x: x['wt1'])
            display_table(all_sorted, "")
        
        # 保存结果到 session state
        st.session_state['last_scan'] = {
            'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'results': results,
            'oversold': oversold,
            'overbought': overbought
        }
        
        st.markdown("---")
        st.caption(f"⏰ 扫描完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 显示上次扫描结果
    elif 'last_scan' in st.session_state:
        st.info(f"📅 上次扫描时间: {st.session_state['last_scan']['time']}")
        st.markdown("点击 **开始扫描** 获取最新数据")

# ============================================================================
# 运行
# ============================================================================

if __name__ == "__main__":
    main()
