"""
Telegram 通知模块
在 GitHub Actions 中运行，发送扫描结果到 Telegram
"""

import os
import json
import requests
from datetime import datetime

def send_telegram_message(bot_token, chat_id, message):
    """
    发送 Telegram 消息
    """
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        print("✅ Telegram 通知发送成功")
        return True
    except Exception as e:
        print(f"❌ Telegram 通知发送失败: {e}")
        return False

def format_message(scan_results):
    """
    格式化扫描结果为 Telegram 消息
    """
    oversold = scan_results.get('oversold', [])
    overbought = scan_results.get('overbought', [])
    scan_time = scan_results.get('scan_time', datetime.now().strftime('%Y-%m-%d %H:%M'))
    
    lines = [
        f"📊 <b>WaveTrend 日线扫描报告</b>",
        f"⏰ {scan_time}",
        ""
    ]
    
    # 超卖（做多机会）
    if oversold:
        lines.append(f"🟢 <b>超卖信号 (WT1 ≤ -60)</b> [{len(oversold)}只]")
        for s in oversold[:5]:  # 最多显示5只
            cross_info = f" {s['cross']}" if s['cross'] else ""
            lines.append(f"  • <code>{s['symbol']}</code> ${s['price']} | WT1: {s['wt1']}{cross_info}")
        if len(oversold) > 5:
            lines.append(f"  ...还有 {len(oversold) - 5} 只")
        lines.append("")
    else:
        lines.append("🟢 超卖信号: 无")
        lines.append("")
    
    # 超买（做空/止盈）
    if overbought:
        lines.append(f"🔴 <b>超买信号 (WT1 ≥ 60)</b> [{len(overbought)}只]")
        for s in overbought[:5]:
            cross_info = f" {s['cross']}" if s['cross'] else ""
            lines.append(f"  • <code>{s['symbol']}</code> ${s['price']} | WT1: {s['wt1']}{cross_info}")
        if len(overbought) > 5:
            lines.append(f"  ...还有 {len(overbought) - 5} 只")
        lines.append("")
    else:
        lines.append("🔴 超买信号: 无")
        lines.append("")
    
    # 摘要
    lines.append("📈 <b>统计</b>")
    lines.append(f"  超卖: {len(oversold)} | 超买: {len(overbought)}")
    
    return "\n".join(lines)

def main():
    # 从环境变量获取配置
    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID')
    
    if not bot_token or not chat_id:
        print("❌ 缺少 TELEGRAM_BOT_TOKEN 或 TELEGRAM_CHAT_ID 环境变量")
        return
    
    # 读取扫描结果
    try:
        with open('data/latest_scan.json', 'r') as f:
            scan_results = json.load(f)
    except FileNotFoundError:
        print("❌ 找不到扫描结果文件")
        return
    
    # 格式化并发送
    message = format_message(scan_results)
    send_telegram_message(bot_token, chat_id, message)

if __name__ == "__main__":
    main()
