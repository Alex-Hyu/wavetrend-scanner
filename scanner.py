"""
WaveTrend 日线筛选报警系统
扫描纳斯达克100股票，当 WT1 >= 60 或 <= -60 时发出警报
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import os

# ============================================================================
# 1. 纳斯达克100成分股
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

# 额外的高波动股票（你关注的）
EXTRA_WATCHLIST = [
    "MSTR", "COIN", "HOOD", "CRWV", "PLTR", "SOFI", "RKLB", "IONQ", "RGTI", "QUBT"
]

# ============================================================================
# 2. WaveTrend 计算函数
# ============================================================================

def calc_wavetrend(df, n1=10, n2=21):
    """
    计算 WaveTrend 指标
    
    参数:
        df: DataFrame，包含 High, Low, Close
        n1: Channel Length (默认10)
        n2: Average Length (默认21)
    
    返回:
        wt1, wt2 Series
    """
    # HLC3
    ap = (df['High'] + df['Low'] + df['Close']) / 3
    
    # ESA = EMA(ap, n1)
    esa = ap.ewm(span=n1, adjust=False).mean()
    
    # D = EMA(abs(ap - esa), n1)
    d = (ap - esa).abs().ewm(span=n1, adjust=False).mean()
    
    # 避免除零
    d = d.replace(0, np.nan)
    
    # CI = (ap - esa) / (0.015 * d)
    ci = (ap - esa) / (0.015 * d)
    
    # WT1 = EMA(ci, n2)
    wt1 = ci.ewm(span=n2, adjust=False).mean()
    
    # WT2 = SMA(wt1, 4)
    wt2 = wt1.rolling(window=4).mean()
    
    return wt1, wt2

# ============================================================================
# 3. 获取股票数据和市值
# ============================================================================

def get_stock_data(symbol, period="3mo"):
    """
    获取股票日线数据和基本信息
    """
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period)
        
        if len(df) < 50:
            return None, None
        
        # 获取市值
        info = ticker.info
        market_cap = info.get('marketCap', 0)
        
        return df, market_cap
    except Exception as e:
        print(f"  ⚠️ 获取 {symbol} 数据失败: {e}")
        return None, None

# ============================================================================
# 4. 扫描函数
# ============================================================================

def scan_stocks(symbols, min_market_cap=10e9, ob_level=60, os_level=-60):
    """
    扫描股票池，找出 WaveTrend 达到极值的股票
    
    参数:
        symbols: 股票代码列表
        min_market_cap: 最小市值（默认100亿美元）
        ob_level: 超买阈值（默认60）
        os_level: 超卖阈值（默认-60）
    
    返回:
        results: 所有扫描结果
        overbought: 超买股票列表
        oversold: 超卖股票列表
    """
    results = []
    overbought = []
    oversold = []
    approaching_ob = []  # 接近超买 (53-60)
    approaching_os = []  # 接近超卖 (-60 to -53)
    
    total = len(symbols)
    
    for i, symbol in enumerate(symbols):
        print(f"\r  扫描进度: {i+1}/{total} - {symbol}    ", end="", flush=True)
        
        df, market_cap = get_stock_data(symbol)
        
        if df is None:
            continue
        
        # 市值筛选
        if market_cap and market_cap < min_market_cap:
            continue
        
        wt1, wt2 = calc_wavetrend(df)
        
        if wt1.isna().iloc[-1]:
            continue
        
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
        
        # 判断方向
        wt_direction = "↑" if current_wt1 > prev_wt1 else "↓" if current_wt1 < prev_wt1 else "→"
        
        result = {
            'symbol': symbol,
            'price': round(current_price, 2),
            'price_change': round(price_change, 2),
            'wt1': round(current_wt1, 2),
            'wt2': round(current_wt2, 2),
            'wt_direction': wt_direction,
            'cross': cross,
            'market_cap': market_cap,
            'market_cap_b': round(market_cap / 1e9, 1) if market_cap else 0,
            'signal': ''
        }
        
        # 分类
        if current_wt1 >= ob_level:
            result['signal'] = '🔴 超买'
            overbought.append(result)
        elif current_wt1 <= os_level:
            result['signal'] = '🟢 超卖'
            oversold.append(result)
        elif current_wt1 >= 53:
            result['signal'] = '🟡 接近超买'
            approaching_ob.append(result)
        elif current_wt1 <= -53:
            result['signal'] = '🟡 接近超卖'
            approaching_os.append(result)
        
        results.append(result)
    
    print("\r  扫描完成!                              ")
    
    return {
        'all': results,
        'overbought': sorted(overbought, key=lambda x: x['wt1'], reverse=True),
        'oversold': sorted(oversold, key=lambda x: x['wt1']),
        'approaching_ob': sorted(approaching_ob, key=lambda x: x['wt1'], reverse=True),
        'approaching_os': sorted(approaching_os, key=lambda x: x['wt1']),
        'scan_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }

# ============================================================================
# 5. 打印报告
# ============================================================================

def print_report(scan_results):
    """
    打印扫描报告到控制台
    """
    print("\n" + "="*70)
    print(f"📊 WaveTrend 日线扫描报告")
    print(f"⏰ 扫描时间: {scan_results['scan_time']}")
    print(f"📈 扫描股票数: {len(scan_results['all'])}")
    print("="*70)
    
    # 超卖（做多机会）
    oversold = scan_results['oversold']
    if oversold:
        print(f"\n🟢 超卖信号 (WT1 ≤ -60) - 潜在做多机会 [{len(oversold)}只]")
        print("-"*70)
        print(f"{'股票':8} | {'价格':>10} | {'涨跌%':>7} | {'WT1':>7} | {'WT2':>7} | {'方向':3} | {'市值':>8} | 交叉")
        print("-"*70)
        for s in oversold:
            print(f"{s['symbol']:8} | ${s['price']:>8.2f} | {s['price_change']:>+6.2f}% | {s['wt1']:>7.2f} | {s['wt2']:>7.2f} | {s['wt_direction']:3} | {s['market_cap_b']:>6.1f}B | {s['cross']}")
    else:
        print("\n🟢 超卖信号: 无")
    
    # 接近超卖
    approaching_os = scan_results['approaching_os']
    if approaching_os:
        print(f"\n🟡 接近超卖 (-60 < WT1 ≤ -53) - 观察名单 [{len(approaching_os)}只]")
        print("-"*70)
        for s in approaching_os[:10]:  # 只显示前10
            print(f"{s['symbol']:8} | ${s['price']:>8.2f} | {s['price_change']:>+6.2f}% | {s['wt1']:>7.2f} | {s['wt2']:>7.2f} | {s['wt_direction']:3} | {s['market_cap_b']:>6.1f}B | {s['cross']}")
    
    # 超买（做空机会或止盈）
    overbought = scan_results['overbought']
    if overbought:
        print(f"\n🔴 超买信号 (WT1 ≥ 60) - 潜在见顶/止盈 [{len(overbought)}只]")
        print("-"*70)
        print(f"{'股票':8} | {'价格':>10} | {'涨跌%':>7} | {'WT1':>7} | {'WT2':>7} | {'方向':3} | {'市值':>8} | 交叉")
        print("-"*70)
        for s in overbought:
            print(f"{s['symbol']:8} | ${s['price']:>8.2f} | {s['price_change']:>+6.2f}% | {s['wt1']:>7.2f} | {s['wt2']:>7.2f} | {s['wt_direction']:3} | {s['market_cap_b']:>6.1f}B | {s['cross']}")
    else:
        print("\n🔴 超买信号: 无")
    
    # 接近超买
    approaching_ob = scan_results['approaching_ob']
    if approaching_ob:
        print(f"\n🟡 接近超买 (53 ≤ WT1 < 60) - 观察名单 [{len(approaching_ob)}只]")
        print("-"*70)
        for s in approaching_ob[:10]:
            print(f"{s['symbol']:8} | ${s['price']:>8.2f} | {s['price_change']:>+6.2f}% | {s['wt1']:>7.2f} | {s['wt2']:>7.2f} | {s['wt_direction']:3} | {s['market_cap_b']:>6.1f}B | {s['cross']}")
    
    print("\n" + "="*70)
    
    # 统计摘要
    print("\n📊 统计摘要:")
    print(f"  超卖 (WT1 ≤ -60): {len(oversold)} 只")
    print(f"  接近超卖: {len(approaching_os)} 只")
    print(f"  超买 (WT1 ≥ 60): {len(overbought)} 只")
    print(f"  接近超买: {len(approaching_ob)} 只")

# ============================================================================
# 6. 保存结果
# ============================================================================

def save_results(scan_results, output_dir="data"):
    """
    保存扫描结果到JSON文件（供Streamlit读取）
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # 保存最新结果
    filepath = os.path.join(output_dir, "latest_scan.json")
    with open(filepath, 'w') as f:
        json.dump(scan_results, f, indent=2)
    
    # 保存历史记录（按日期）
    date_str = datetime.now().strftime('%Y%m%d')
    history_path = os.path.join(output_dir, f"scan_{date_str}.json")
    with open(history_path, 'w') as f:
        json.dump(scan_results, f, indent=2)
    
    print(f"\n💾 结果已保存到: {filepath}")
    
    return filepath

# ============================================================================
# 7. 主程序
# ============================================================================

def main():
    print("\n" + "="*70)
    print("🔍 WaveTrend 扫描器启动")
    print("="*70)
    
    # 合并股票池
    all_symbols = list(set(NASDAQ_100 + EXTRA_WATCHLIST))
    print(f"\n📋 股票池: {len(all_symbols)} 只股票")
    print(f"📊 市值筛选: ≥ 100亿美元")
    print(f"📈 超买阈值: WT1 ≥ 60")
    print(f"📉 超卖阈值: WT1 ≤ -60")
    
    print("\n⏳ 开始扫描...")
    
    # 扫描
    scan_results = scan_stocks(
        symbols=all_symbols,
        min_market_cap=10e9,  # 100亿美元
        ob_level=60,
        os_level=-60
    )
    
    # 打印报告
    print_report(scan_results)
    
    # 保存结果
    save_results(scan_results)
    
    return scan_results

# ============================================================================
# 运行
# ============================================================================

if __name__ == "__main__":
    main()
