"""
WaveTrend 日线筛选报警系统 V2.0
升级功能：
- 背离检测（摆动点方法）
- RSI 双重确认
- 成交量分析
- 综合评分系统
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import json
import os

# ============================================================================
# 1. 股票池
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
# 2. 技术指标计算
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

def calc_rsi(df, period=14):
    """计算 RSI"""
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calc_volume_ratio(df, period=20):
    """计算成交量比率 (当前量 / 均量)"""
    vol_ma = df['Volume'].rolling(window=period).mean()
    vol_ratio = df['Volume'] / vol_ma
    return vol_ratio

# ============================================================================
# 3. 摆动点检测
# ============================================================================

def find_swing_lows(df, window=5):
    """
    找局部低点（摆动低点）
    条件：该点是前后 window 根K线中的最低点
    返回：低点的索引列表
    """
    lows = []
    for i in range(window, len(df) - window):
        current_low = df['Low'].iloc[i]
        range_low = df['Low'].iloc[i-window:i+window+1].min()
        if current_low == range_low:
            lows.append(i)
    return lows

def find_swing_highs(df, window=5):
    """
    找局部高点（摆动高点）
    条件：该点是前后 window 根K线中的最高点
    返回：高点的索引列表
    """
    highs = []
    for i in range(window, len(df) - window):
        current_high = df['High'].iloc[i]
        range_high = df['High'].iloc[i-window:i+window+1].max()
        if current_high == range_high:
            highs.append(i)
    return highs

# ============================================================================
# 4. 背离检测
# ============================================================================

def detect_divergence(df, wt1, lookback=30, swing_window=5):
    """
    检测背离
    
    返回:
        bullish_div: 看涨背离 (价格新低，WT1 没新低)
        bearish_div: 看跌背离 (价格新高，WT1 没新高)
        div_details: 背离详情
    """
    bullish_div = False
    bearish_div = False
    div_details = ""
    
    # 只看最近 lookback 天的数据
    recent_df = df.iloc[-lookback:].copy()
    recent_wt1 = wt1.iloc[-lookback:].copy()
    
    # 找摆动低点
    swing_lows = find_swing_lows(recent_df, window=swing_window)
    
    if len(swing_lows) >= 2:
        # 最近两个低点
        latest_idx = swing_lows[-1]
        prev_idx = swing_lows[-2]
        
        # 实际索引（相对于原始 df）
        actual_latest = len(df) - lookback + latest_idx
        actual_prev = len(df) - lookback + prev_idx
        
        price_latest = recent_df['Low'].iloc[latest_idx]
        price_prev = recent_df['Low'].iloc[prev_idx]
        wt1_latest = recent_wt1.iloc[latest_idx]
        wt1_prev = recent_wt1.iloc[prev_idx]
        
        # 看涨背离：价格更低，但 WT1 更高
        if price_latest < price_prev and wt1_latest > wt1_prev:
            bullish_div = True
            div_details = f"底背离: 价格 {price_prev:.1f}→{price_latest:.1f}, WT1 {wt1_prev:.1f}→{wt1_latest:.1f}"
    
    # 找摆动高点
    swing_highs = find_swing_highs(recent_df, window=swing_window)
    
    if len(swing_highs) >= 2:
        latest_idx = swing_highs[-1]
        prev_idx = swing_highs[-2]
        
        price_latest = recent_df['High'].iloc[latest_idx]
        price_prev = recent_df['High'].iloc[prev_idx]
        wt1_latest = recent_wt1.iloc[latest_idx]
        wt1_prev = recent_wt1.iloc[prev_idx]
        
        # 看跌背离：价格更高，但 WT1 更低
        if price_latest > price_prev and wt1_latest < wt1_prev:
            bearish_div = True
            div_details = f"顶背离: 价格 {price_prev:.1f}→{price_latest:.1f}, WT1 {wt1_prev:.1f}→{wt1_latest:.1f}"
    
    return bullish_div, bearish_div, div_details

# ============================================================================
# 5. 综合评分
# ============================================================================

def calc_reversal_score(result, is_oversold=True):
    """
    计算反转信号评分
    
    超卖（做多机会）评分项：
    - WT1 超卖 (≤-60): +1
    - WT1 金叉: +2
    - WT1 拐头向上: +1
    - 看涨背离: +2
    - RSI 超卖 (<30): +1
    - 成交量萎缩 (<0.8): +1 (卖压衰竭)
    - 成交量放大 (>1.5) + 上涨: +1 (买方进场)
    
    满分: 9分
    """
    score = 0
    details = []
    
    if is_oversold:
        # 做多机会评分
        
        # 1. WT1 超卖
        if result['wt1'] <= -60:
            score += 1
            details.append("WT超卖+1")
        
        # 2. 金叉
        if "金叉" in result.get('cross', ''):
            score += 2
            details.append("金叉+2")
        
        # 3. WT1 拐头向上
        if result.get('wt_direction') == '↑':
            score += 1
            details.append("拐头↑+1")
        
        # 4. 看涨背离
        if result.get('bullish_div'):
            score += 2
            details.append("底背离+2")
        
        # 5. RSI 超卖
        if result.get('rsi', 50) < 30:
            score += 1
            details.append("RSI<30+1")
        
        # 6. 成交量
        vol_ratio = result.get('vol_ratio', 1.0)
        price_change = result.get('price_change', 0)
        
        if vol_ratio < 0.8:
            score += 1
            details.append("缩量+1")
        elif vol_ratio > 1.5 and price_change > 0:
            score += 1
            details.append("放量涨+1")
    
    else:
        # 做空/止盈机会评分
        
        # 1. WT1 超买
        if result['wt1'] >= 60:
            score += 1
            details.append("WT超买+1")
        
        # 2. 死叉
        if "死叉" in result.get('cross', ''):
            score += 2
            details.append("死叉+2")
        
        # 3. WT1 拐头向下
        if result.get('wt_direction') == '↓':
            score += 1
            details.append("拐头↓+1")
        
        # 4. 看跌背离
        if result.get('bearish_div'):
            score += 2
            details.append("顶背离+2")
        
        # 5. RSI 超买
        if result.get('rsi', 50) > 70:
            score += 1
            details.append("RSI>70+1")
        
        # 6. 成交量
        vol_ratio = result.get('vol_ratio', 1.0)
        price_change = result.get('price_change', 0)
        
        if vol_ratio < 0.8:
            score += 1
            details.append("缩量+1")
        elif vol_ratio > 1.5 and price_change < 0:
            score += 1
            details.append("放量跌+1")
    
    return score, details

def get_score_grade(score):
    """评分等级"""
    if score >= 5:
        return "A", "⭐⭐⭐"
    elif score >= 3:
        return "B", "⭐⭐"
    elif score >= 2:
        return "C", "⭐"
    else:
        return "D", ""

# ============================================================================
# 6. 获取股票数据
# ============================================================================

def get_stock_data(symbol, period="3mo"):
    """获取股票日线数据和基本信息"""
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period)
        
        if len(df) < 50:
            return None, None
        
        info = ticker.info
        market_cap = info.get('marketCap', 0)
        
        return df, market_cap
    except Exception as e:
        print(f"  ⚠️ 获取 {symbol} 数据失败: {e}")
        return None, None

# ============================================================================
# 7. 扫描函数
# ============================================================================

def scan_stocks(symbols, min_market_cap=10e9, ob_level=60, os_level=-60):
    """
    扫描股票池
    """
    results = []
    total = len(symbols)
    
    for i, symbol in enumerate(symbols):
        print(f"\r  扫描进度: {i+1}/{total} - {symbol}    ", end="", flush=True)
        
        df, market_cap = get_stock_data(symbol)
        
        if df is None:
            continue
        
        # 市值筛选
        if market_cap and market_cap < min_market_cap:
            continue
        
        # 计算指标
        wt1, wt2 = calc_wavetrend(df)
        rsi = calc_rsi(df)
        vol_ratio = calc_volume_ratio(df)
        
        if wt1.isna().iloc[-1]:
            continue
        
        # 当前值
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
        
        # WT1 方向
        wt_direction = "↑" if current_wt1 > prev_wt1 else "↓" if current_wt1 < prev_wt1 else "→"
        
        # 背离检测
        bullish_div, bearish_div, div_details = detect_divergence(df, wt1)
        
        # 成交量状态
        if current_vol_ratio >= 2.0:
            vol_status = "🔥 暴量"
        elif current_vol_ratio >= 1.5:
            vol_status = "📈 放量"
        elif current_vol_ratio < 0.7:
            vol_status = "📉 缩量"
        else:
            vol_status = "正常"
        
        # RSI 状态
        if current_rsi < 30:
            rsi_status = "🟢 超卖"
        elif current_rsi > 70:
            rsi_status = "🔴 超买"
        else:
            rsi_status = "中性"
        
        # 构建结果
        result = {
            'symbol': symbol,
            'price': round(current_price, 2),
            'price_change': round(price_change, 2),
            'wt1': round(current_wt1, 2),
            'wt2': round(current_wt2, 2),
            'wt_direction': wt_direction,
            'cross': cross,
            'rsi': round(current_rsi, 1),
            'rsi_status': rsi_status,
            'vol_ratio': round(current_vol_ratio, 2),
            'vol_status': vol_status,
            'bullish_div': bullish_div,
            'bearish_div': bearish_div,
            'div_details': div_details,
            'market_cap': market_cap,
            'market_cap_b': round(market_cap / 1e9, 1) if market_cap else 0,
        }
        
        # 分类和评分
        if current_wt1 <= os_level:
            result['signal'] = '🟢 超卖'
            result['signal_type'] = 'oversold'
            score, score_details = calc_reversal_score(result, is_oversold=True)
        elif current_wt1 >= ob_level:
            result['signal'] = '🔴 超买'
            result['signal_type'] = 'overbought'
            score, score_details = calc_reversal_score(result, is_oversold=False)
        elif current_wt1 <= -53:
            result['signal'] = '🟡 接近超卖'
            result['signal_type'] = 'approaching_os'
            score, score_details = calc_reversal_score(result, is_oversold=True)
        elif current_wt1 >= 53:
            result['signal'] = '🟡 接近超买'
            result['signal_type'] = 'approaching_ob'
            score, score_details = calc_reversal_score(result, is_oversold=False)
        else:
            result['signal'] = '⚪ 中性'
            result['signal_type'] = 'neutral'
            score, score_details = 0, []
        
        result['score'] = score
        result['score_details'] = ', '.join(score_details)
        result['grade'], result['stars'] = get_score_grade(score)
        
        results.append(result)
    
    print("\r  扫描完成!                              ")
    
    # 分类结果
    oversold = sorted([r for r in results if r['signal_type'] == 'oversold'], key=lambda x: x['score'], reverse=True)
    overbought = sorted([r for r in results if r['signal_type'] == 'overbought'], key=lambda x: x['score'], reverse=True)
    approaching_os = sorted([r for r in results if r['signal_type'] == 'approaching_os'], key=lambda x: x['score'], reverse=True)
    approaching_ob = sorted([r for r in results if r['signal_type'] == 'approaching_ob'], key=lambda x: x['score'], reverse=True)
    
    return {
        'all': results,
        'oversold': oversold,
        'overbought': overbought,
        'approaching_os': approaching_os,
        'approaching_ob': approaching_ob,
        'scan_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }

# ============================================================================
# 8. 打印报告
# ============================================================================

def print_report(scan_results):
    """打印扫描报告"""
    print("\n" + "="*100)
    print(f"📊 WaveTrend 日线扫描报告 V2.0 (含背离+RSI+成交量)")
    print(f"⏰ 扫描时间: {scan_results['scan_time']}")
    print(f"📈 扫描股票数: {len(scan_results['all'])}")
    print("="*100)
    
    # 超卖（做多机会）
    oversold = scan_results['oversold']
    if oversold:
        print(f"\n🟢 超卖信号 (WT1 ≤ -60) - 潜在做多机会 [{len(oversold)}只] 【按评分排序】")
        print("-"*100)
        print(f"{'评分':6} | {'股票':8} | {'价格':>10} | {'涨跌%':>7} | {'WT1':>7} | {'方向':3} | {'RSI':>5} | {'成交量':8} | {'背离':6} | {'交叉':8}")
        print("-"*100)
        for s in oversold:
            div_mark = "✅底背离" if s['bullish_div'] else ""
            print(f"{s['score']}/9 {s['stars']:4} | {s['symbol']:8} | ${s['price']:>8.2f} | {s['price_change']:>+6.2f}% | {s['wt1']:>7.2f} | {s['wt_direction']:3} | {s['rsi']:>5.1f} | {s['vol_status']:8} | {div_mark:6} | {s['cross']:8}")
            if s['score_details']:
                print(f"         └─ {s['score_details']}")
    else:
        print("\n🟢 超卖信号: 无")
    
    # 接近超卖
    approaching_os = scan_results['approaching_os']
    if approaching_os:
        print(f"\n🟡 接近超卖 (-60 < WT1 ≤ -53) - 观察名单 [{len(approaching_os)}只]")
        print("-"*100)
        for s in approaching_os[:10]:
            div_mark = "✅底背离" if s['bullish_div'] else ""
            print(f"{s['score']}/9 {s['stars']:4} | {s['symbol']:8} | ${s['price']:>8.2f} | {s['price_change']:>+6.2f}% | {s['wt1']:>7.2f} | {s['wt_direction']:3} | {s['rsi']:>5.1f} | {s['vol_status']:8} | {div_mark:6} | {s['cross']:8}")
    
    # 超买（做空/止盈机会）
    overbought = scan_results['overbought']
    if overbought:
        print(f"\n🔴 超买信号 (WT1 ≥ 60) - 潜在见顶/止盈 [{len(overbought)}只] 【按评分排序】")
        print("-"*100)
        print(f"{'评分':6} | {'股票':8} | {'价格':>10} | {'涨跌%':>7} | {'WT1':>7} | {'方向':3} | {'RSI':>5} | {'成交量':8} | {'背离':6} | {'交叉':8}")
        print("-"*100)
        for s in overbought:
            div_mark = "✅顶背离" if s['bearish_div'] else ""
            print(f"{s['score']}/9 {s['stars']:4} | {s['symbol']:8} | ${s['price']:>8.2f} | {s['price_change']:>+6.2f}% | {s['wt1']:>7.2f} | {s['wt_direction']:3} | {s['rsi']:>5.1f} | {s['vol_status']:8} | {div_mark:6} | {s['cross']:8}")
            if s['score_details']:
                print(f"         └─ {s['score_details']}")
    else:
        print("\n🔴 超买信号: 无")
    
    # 接近超买
    approaching_ob = scan_results['approaching_ob']
    if approaching_ob:
        print(f"\n🟡 接近超买 (53 ≤ WT1 < 60) - 观察名单 [{len(approaching_ob)}只]")
        print("-"*100)
        for s in approaching_ob[:10]:
            div_mark = "✅顶背离" if s['bearish_div'] else ""
            print(f"{s['score']}/9 {s['stars']:4} | {s['symbol']:8} | ${s['price']:>8.2f} | {s['price_change']:>+6.2f}% | {s['wt1']:>7.2f} | {s['wt_direction']:3} | {s['rsi']:>5.1f} | {s['vol_status']:8} | {div_mark:6} | {s['cross']:8}")
    
    print("\n" + "="*100)
    
    # 统计摘要
    print("\n📊 统计摘要:")
    print(f"  超卖 (WT1 ≤ -60): {len(oversold)} 只")
    print(f"  接近超卖: {len(approaching_os)} 只")
    print(f"  超买 (WT1 ≥ 60): {len(overbought)} 只")
    print(f"  接近超买: {len(approaching_ob)} 只")
    
    # 高评分股票
    high_score_oversold = [s for s in oversold if s['score'] >= 3]
    high_score_overbought = [s for s in overbought if s['score'] >= 3]
    
    if high_score_oversold:
        print(f"\n⭐ 高评分做多机会 (≥3分): {', '.join([s['symbol'] for s in high_score_oversold])}")
    if high_score_overbought:
        print(f"⭐ 高评分做空/止盈 (≥3分): {', '.join([s['symbol'] for s in high_score_overbought])}")
    
    # 评分说明
    print("\n📖 评分说明 (满分9分):")
    print("  +1: WT超买/超卖 | +2: 金叉/死叉 | +1: 拐头 | +2: 背离 | +1: RSI确认 | +1: 成交量确认")
    print("  A级(≥5分)⭐⭐⭐: 强反转信号 | B级(3-4分)⭐⭐: 中等信号 | C级(2分)⭐: 弱信号")

# ============================================================================
# 9. 保存结果
# ============================================================================

def save_results(scan_results, output_dir="data"):
    """保存扫描结果"""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    filepath = os.path.join(output_dir, "latest_scan.json")
    with open(filepath, 'w') as f:
        json.dump(scan_results, f, indent=2, ensure_ascii=False)
    
    date_str = datetime.now().strftime('%Y%m%d')
    history_path = os.path.join(output_dir, f"scan_{date_str}.json")
    with open(history_path, 'w') as f:
        json.dump(scan_results, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 结果已保存到: {filepath}")
    
    return filepath

# ============================================================================
# 10. 主程序
# ============================================================================

def main():
    print("\n" + "="*100)
    print("🔍 WaveTrend 扫描器 V2.0 启动")
    print("   新增: 背离检测 | RSI双重确认 | 成交量分析 | 综合评分")
    print("="*100)
    
    all_symbols = list(set(NASDAQ_100 + EXTRA_WATCHLIST))
    print(f"\n📋 股票池: {len(all_symbols)} 只股票")
    print(f"📊 市值筛选: ≥ 100亿美元")
    print(f"📈 超买阈值: WT1 ≥ 60")
    print(f"📉 超卖阈值: WT1 ≤ -60")
    
    print("\n⏳ 开始扫描...")
    
    scan_results = scan_stocks(
        symbols=all_symbols,
        min_market_cap=10e9,
        ob_level=60,
        os_level=-60
    )
    
    print_report(scan_results)
    save_results(scan_results)
    
    return scan_results

if __name__ == "__main__":
    main()
