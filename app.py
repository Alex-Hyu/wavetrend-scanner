"""
WaveTrend 扫描器 V3.0 - Streamlit 网页界面
新增: 信号追踪模块 - 使用 Google Sheets 持久化存储
"""

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import gspread
from google.oauth2.service_account import Credentials

# ============================================================================
# 页面配置
# ============================================================================

st.set_page_config(
    page_title="WaveTrend 扫描器 V3.0",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# Google Sheets 配置
# ============================================================================

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

# 从 Streamlit Secrets 读取 Google 凭证
# 需要在 Streamlit Cloud 的 Secrets 中配置 [gcp_service_account]
@st.cache_resource
def get_google_client():
    """获取 Google Sheets 客户端"""
    try:
        credentials = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=SCOPES
        )
        client = gspread.authorize(credentials)
        return client
    except Exception as e:
        st.error(f"Google Sheets 连接失败: {e}")
        return None

@st.cache_resource
def get_spreadsheet():
    """获取或创建 Spreadsheet"""
    client = get_google_client()
    if not client:
        return None, None, None
    
    try:
        # 尝试打开已有的表格
        spreadsheet = client.open("WaveTrend_Tracking")
    except gspread.SpreadsheetNotFound:
        # 创建新表格
        spreadsheet = client.create("WaveTrend_Tracking")
        # 分享给自己（可选）
        # spreadsheet.share('your-email@gmail.com', perm_type='user', role='writer')
    
    # 获取或创建工作表
    try:
        bullish_sheet = spreadsheet.worksheet("Bullish")
    except gspread.WorksheetNotFound:
        bullish_sheet = spreadsheet.add_worksheet(title="Bullish", rows=1000, cols=10)
        bullish_sheet.append_row(["symbol", "d0_date", "d0_price", "current_price", "change_pct", "trading_days", "score", "score_details", "status", "result"])
    
    try:
        bearish_sheet = spreadsheet.worksheet("Bearish")
    except gspread.WorksheetNotFound:
        bearish_sheet = spreadsheet.add_worksheet(title="Bearish", rows=1000, cols=10)
        bearish_sheet.append_row(["symbol", "d0_date", "d0_price", "current_price", "change_pct", "trading_days", "score", "score_details", "status", "result"])
    
    return spreadsheet, bullish_sheet, bearish_sheet

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
# Google Sheets 追踪模块
# ============================================================================

def load_tracking_data_from_sheets():
    """从 Google Sheets 加载追踪数据"""
    _, bullish_sheet, bearish_sheet = get_spreadsheet()
    
    if not bullish_sheet or not bearish_sheet:
        return {"bullish": [], "bearish": []}
    
    data = {"bullish": [], "bearish": []}
    
    try:
        # 读取 Bullish 工作表
        bullish_records = bullish_sheet.get_all_records()
        data["bullish"] = bullish_records if bullish_records else []
        
        # 读取 Bearish 工作表
        bearish_records = bearish_sheet.get_all_records()
        data["bearish"] = bearish_records if bearish_records else []
    except Exception as e:
        st.error(f"读取数据失败: {e}")
    
    return data

def save_to_sheets(sheet, item):
    """保存一条记录到工作表"""
    try:
        row = [
            item["symbol"],
            item["d0_date"],
            item["d0_price"],
            item["current_price"],
            item["change_pct"],
            item["trading_days"],
            item["score"],
            item["score_details"],
            item["status"],
            item["result"]
        ]
        sheet.append_row(row)
        return True
    except Exception as e:
        st.error(f"保存失败: {e}")
        return False

def update_sheet_row(sheet, row_index, item):
    """更新工作表中的一行"""
    try:
        row = [
            item["symbol"],
            item["d0_date"],
            item["d0_price"],
            item["current_price"],
            item["change_pct"],
            item["trading_days"],
            item["score"],
            item["score_details"],
            item["status"],
            item["result"]
        ]
        # row_index + 2 因为：+1 是标题行，+1 是从1开始计数
        sheet.update(f'A{row_index + 2}:J{row_index + 2}', [row])
        return True
    except Exception as e:
        st.error(f"更新失败: {e}")
        return False

def delete_sheet_row(sheet, row_index):
    """删除工作表中的一行"""
    try:
        sheet.delete_rows(row_index + 2)  # +2 因为标题行和从1开始计数
        return True
    except Exception as e:
        st.error(f"删除失败: {e}")
        return False

def get_current_price(symbol):
    """获取当前价格"""
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="5d")
        if len(df) > 0:
            return round(df['Close'].iloc[-1], 2)
    except:
        pass
    return None

def get_trading_days_count(start_date_str):
    """计算从开始日期到现在经过了多少个交易日"""
    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        # 获取 SPY 的历史数据来计算交易日
        spy = yf.Ticker("SPY")
        df = spy.history(start=start_date, end=datetime.now())
        return len(df)
    except:
        return 0

def add_to_tracking(symbol, signal_type, d0_price, score, score_details):
    """添加股票到追踪列表"""
    _, bullish_sheet, bearish_sheet = get_spreadsheet()
    
    if not bullish_sheet or not bearish_sheet:
        st.error("无法连接 Google Sheets")
        return False
    
    sheet = bullish_sheet if signal_type == "bullish" else bearish_sheet
    
    # 检查是否已存在
    try:
        existing = sheet.col_values(1)  # 第一列是 symbol
        if symbol in existing:
            return False
    except:
        pass
    
    new_entry = {
        "symbol": symbol,
        "d0_date": datetime.now().strftime('%Y-%m-%d'),
        "d0_price": d0_price,
        "current_price": d0_price,
        "change_pct": 0,
        "trading_days": 0,
        "score": score,
        "score_details": score_details,
        "status": "追踪中",
        "result": "待定"
    }
    
    return save_to_sheets(sheet, new_entry)

def update_tracking_data():
    """更新所有追踪中的股票价格"""
    _, bullish_sheet, bearish_sheet = get_spreadsheet()
    
    if not bullish_sheet or not bearish_sheet:
        return {"bullish": [], "bearish": []}
    
    data = {"bullish": [], "bearish": []}
    
    for list_key, sheet in [("bullish", bullish_sheet), ("bearish", bearish_sheet)]:
        try:
            records = sheet.get_all_records()
            
            for idx, item in enumerate(records):
                if item.get("status") == "追踪中":
                    # 更新价格
                    current_price = get_current_price(item["symbol"])
                    if current_price:
                        item["current_price"] = current_price
                        d0_price = float(item["d0_price"]) if item["d0_price"] else current_price
                        item["change_pct"] = round((current_price / d0_price - 1) * 100, 2)
                    
                    # 更新交易日数
                    trading_days = get_trading_days_count(item["d0_date"])
                    item["trading_days"] = trading_days
                    
                    # 判断信号是否正确
                    change = item["change_pct"]
                    if list_key == "bullish":
                        if change > 5:
                            item["result"] = "✅ 正确"
                        elif change < -5:
                            item["result"] = "❌ 错误"
                        else:
                            item["result"] = "⏳ 待定"
                    else:
                        if change < -5:
                            item["result"] = "✅ 正确"
                        elif change > 5:
                            item["result"] = "❌ 错误"
                        else:
                            item["result"] = "⏳ 待定"
                    
                    # 30个交易日后标记完成
                    if trading_days >= 30:
                        item["status"] = "已完成"
                    
                    # 更新到 Google Sheets
                    update_sheet_row(sheet, idx, item)
                
                data[list_key].append(item)
        except Exception as e:
            st.error(f"更新 {list_key} 数据失败: {e}")
    
    return data

def remove_from_tracking(symbol, signal_type):
    """从追踪列表移除"""
    _, bullish_sheet, bearish_sheet = get_spreadsheet()
    
    if not bullish_sheet or not bearish_sheet:
        return False
    
    sheet = bullish_sheet if signal_type == "bullish" else bearish_sheet
    
    try:
        symbols = sheet.col_values(1)
        if symbol in symbols:
            row_index = symbols.index(symbol)
            if row_index > 0:  # 跳过标题行
                delete_sheet_row(sheet, row_index - 1)
                return True
    except Exception as e:
        st.error(f"移除失败: {e}")
    
    return False

def calculate_accuracy(items):
    """计算准确率"""
    completed = [item for item in items if item.get("status") == "已完成"]
    if not completed:
        return None, 0, 0
    
    correct = len([item for item in completed if "正确" in str(item.get("result", ""))])
    total = len(completed)
    accuracy = round(correct / total * 100, 1) if total > 0 else 0
    
    return accuracy, correct, total

def display_tracking_module():
    """显示追踪模块"""
    st.markdown("---")
    st.header("📈 信号追踪模块")
    
    # 检查 Google Sheets 连接
    _, bullish_sheet, bearish_sheet = get_spreadsheet()
    
    if not bullish_sheet or not bearish_sheet:
        st.error("⚠️ 无法连接 Google Sheets。请检查 Secrets 配置。")
        st.markdown("""
        ### 配置说明
        
        在 Streamlit Cloud 的 **Settings > Secrets** 中添加：
        
        ```toml
        [gcp_service_account]
        type = "service_account"
        project_id = "your-project-id"
        private_key_id = "..."
        private_key = "-----BEGIN PRIVATE KEY-----\\n...\\n-----END PRIVATE KEY-----\\n"
        client_email = "...@...iam.gserviceaccount.com"
        client_id = "..."
        auth_uri = "https://accounts.google.com/o/oauth2/auth"
        token_uri = "https://oauth2.googleapis.com/token"
        auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
        client_x509_cert_url = "..."
        ```
        """)
        return
    
    # 更新按钮
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("🔄 刷新价格", type="primary"):
            with st.spinner("更新价格中..."):
                update_tracking_data()
            st.success("价格已更新!")
            st.rerun()
    
    # 加载数据
    data = load_tracking_data_from_sheets()
    
    # 统计信息
    st.subheader("📊 追踪统计")
    
    col1, col2, col3, col4 = st.columns(4)
    
    # 计算准确率
    bullish_accuracy, bullish_correct, bullish_total = calculate_accuracy(data["bullish"])
    bearish_accuracy, bearish_correct, bearish_total = calculate_accuracy(data["bearish"])
    
    bullish_tracking = [i for i in data["bullish"] if i.get("status") == "追踪中"]
    bearish_tracking = [i for i in data["bearish"] if i.get("status") == "追踪中"]
    
    with col1:
        st.metric("🟢 做多追踪中", len(bullish_tracking))
    with col2:
        if bullish_accuracy is not None:
            st.metric("🟢 做多准确率", f"{bullish_accuracy}%", f"{bullish_correct}/{bullish_total}")
        else:
            st.metric("🟢 做多准确率", "暂无数据")
    with col3:
        st.metric("🔴 做空追踪中", len(bearish_tracking))
    with col4:
        if bearish_accuracy is not None:
            st.metric("🔴 做空准确率", f"{bearish_accuracy}%", f"{bearish_correct}/{bearish_total}")
        else:
            st.metric("🔴 做空准确率", "暂无数据")
    
    # Tab 显示详情
    tab1, tab2, tab3 = st.tabs(["🟢 做多信号追踪", "🔴 做空信号追踪", "📋 历史记录"])
    
    with tab1:
        st.subheader("🟢 做多信号追踪 (超卖反转)")
        
        if bullish_tracking:
            df = pd.DataFrame(bullish_tracking)
            display_cols = ['symbol', 'd0_date', 'd0_price', 'current_price', 'change_pct', 'trading_days', 'score', 'result']
            df = df[[c for c in display_cols if c in df.columns]]
            df.columns = ['股票', '信号日期', 'D0价格', '当前价格', '涨跌幅%', '交易日', '评分', '判定'][:len(df.columns)]
            
            st.dataframe(
                df,
                hide_index=True,
                use_container_width=True
            )
            
            # 移除按钮
            st.markdown("**移除追踪：**")
            cols = st.columns(min(len(bullish_tracking), 5))
            for idx, item in enumerate(bullish_tracking[:5]):
                with cols[idx]:
                    if st.button(f"❌ {item['symbol']}", key=f"remove_bull_{item['symbol']}"):
                        remove_from_tracking(item['symbol'], 'bullish')
                        st.rerun()
        else:
            st.info("暂无做多信号在追踪中")
    
    with tab2:
        st.subheader("🔴 做空信号追踪 (超买见顶)")
        
        if bearish_tracking:
            df = pd.DataFrame(bearish_tracking)
            display_cols = ['symbol', 'd0_date', 'd0_price', 'current_price', 'change_pct', 'trading_days', 'score', 'result']
            df = df[[c for c in display_cols if c in df.columns]]
            df.columns = ['股票', '信号日期', 'D0价格', '当前价格', '涨跌幅%', '交易日', '评分', '判定'][:len(df.columns)]
            
            st.dataframe(
                df,
                hide_index=True,
                use_container_width=True
            )
            
            # 移除按钮
            st.markdown("**移除追踪：**")
            cols = st.columns(min(len(bearish_tracking), 5))
            for idx, item in enumerate(bearish_tracking[:5]):
                with cols[idx]:
                    if st.button(f"❌ {item['symbol']}", key=f"remove_bear_{item['symbol']}"):
                        remove_from_tracking(item['symbol'], 'bearish')
                        st.rerun()
        else:
            st.info("暂无做空信号在追踪中")
    
    with tab3:
        st.subheader("📋 已完成追踪记录")
        
        completed_bullish = [i for i in data["bullish"] if i.get("status") == "已完成"]
        completed_bearish = [i for i in data["bearish"] if i.get("status") == "已完成"]
        
        if completed_bullish:
            st.markdown("**🟢 做多信号历史：**")
            df = pd.DataFrame(completed_bullish)
            display_cols = ['symbol', 'd0_date', 'd0_price', 'current_price', 'change_pct', 'score', 'result']
            df = df[[c for c in display_cols if c in df.columns]]
            df.columns = ['股票', '信号日期', 'D0价格', '最终价格', '涨跌幅%', '评分', '判定'][:len(df.columns)]
            st.dataframe(df, hide_index=True, use_container_width=True)
        
        if completed_bearish:
            st.markdown("**🔴 做空信号历史：**")
            df = pd.DataFrame(completed_bearish)
            display_cols = ['symbol', 'd0_date', 'd0_price', 'current_price', 'change_pct', 'score', 'result']
            df = df[[c for c in display_cols if c in df.columns]]
            df.columns = ['股票', '信号日期', 'D0价格', '最终价格', '涨跌幅%', '评分', '判定'][:len(df.columns)]
            st.dataframe(df, hide_index=True, use_container_width=True)
        
        if not completed_bullish and not completed_bearish:
            st.info("暂无已完成的追踪记录")

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
    
    # 高评分提示 + 一键追踪
    high_score_os = [r for r in oversold if r['score'] >= 3]
    high_score_ob = [r for r in overbought if r['score'] >= 3]
    
    if high_score_os:
        st.success(f"⭐ 高评分做多机会 (≥3分): **{', '.join([r['symbol'] for r in high_score_os])}**")
        if st.button("📌 一键追踪所有做多信号", key="track_all_bullish"):
            added = 0
            for r in high_score_os:
                if add_to_tracking(r['symbol'], 'bullish', r['price'], r['score'], r['score_details']):
                    added += 1
            st.success(f"已添加 {added} 只股票到做多追踪列表")
            st.rerun()
    
    if high_score_ob:
        st.warning(f"⭐ 高评分见顶/止盈 (≥3分): **{', '.join([r['symbol'] for r in high_score_ob])}**")
        if st.button("📌 一键追踪所有做空信号", key="track_all_bearish"):
            added = 0
            for r in high_score_ob:
                if add_to_tracking(r['symbol'], 'bearish', r['price'], r['score'], r['score_details']):
                    added += 1
            st.success(f"已添加 {added} 只股票到做空追踪列表")
            st.rerun()
    
    st.markdown("---")
    
    # Tab 显示
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        f"🟢 超卖 ({len(oversold)})",
        f"🟡 接近超卖 ({len(approaching_os)})",
        f"🔴 超买 ({len(overbought)})",
        f"🟡 接近超买 ({len(approaching_ob)})",
        "📋 全部"
    ])
    
    def display_table(data, signal_type=None):
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
            
            # 单独追踪按钮
            if signal_type:
                st.markdown("**添加到追踪：**")
                cols = st.columns(min(len(data), 6))
                for idx, item in enumerate(data[:6]):
                    with cols[idx]:
                        if st.button(f"📌 {item['symbol']}", key=f"track_{signal_type}_{item['symbol']}"):
                            if add_to_tracking(item['symbol'], signal_type, item['price'], item['score'], item['score_details']):
                                st.success(f"已添加 {item['symbol']}")
                            else:
                                st.warning(f"{item['symbol']} 已在追踪列表中")
        else:
            st.info("没有符合条件的股票")
    
    with tab1:
        st.subheader("🟢 超卖股票 (WT1 ≤ -60) - 按评分排序")
        st.markdown("*潜在做多机会，评分越高反转可能性越大*")
        display_table(oversold, "bullish")
    
    with tab2:
        st.subheader("🟡 接近超卖 (-60 < WT1 ≤ -53)")
        display_table(approaching_os)
    
    with tab3:
        st.subheader("🔴 超买股票 (WT1 ≥ 60) - 按评分排序")
        st.markdown("*潜在见顶信号，考虑止盈或观望*")
        display_table(overbought, "bearish")
    
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
    st.title("📊 WaveTrend 扫描器 V3.0")
    st.markdown("**新增**: 信号追踪模块 - Google Sheets 持久化存储")
    
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
        
        st.markdown("---")
        st.markdown("### 📈 追踪判定标准")
        st.markdown("""
        **做多信号**:
        - 涨幅 > 5% → ✅ 正确
        - 跌幅 > 5% → ❌ 错误
        
        **做空信号**:
        - 跌幅 > 5% → ✅ 正确
        - 涨幅 > 5% → ❌ 错误
        
        **追踪周期**: 30个交易日
        """)
    
    # 页面选择
    page = st.radio("选择功能", ["📊 扫描", "📈 追踪"], horizontal=True, label_visibility="collapsed")
    
    if page == "📊 扫描":
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
        
        # 显示结果
        if st.session_state.scan_results is not None:
            display_results(st.session_state.scan_results, st.session_state.scan_time)
        else:
            st.info("👆 点击 **开始扫描** 按钮开始扫描股票")
    
    else:  # 追踪页面
        display_tracking_module()

# ============================================================================
# 运行
# ============================================================================

if __name__ == "__main__":
    main()
