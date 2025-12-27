# 📊 WaveTrend 日线扫描器

扫描纳斯达克100及高波动股票，寻找超买/超卖机会。

## 功能特点

- 🔍 扫描 100+ 只美股
- 📊 WaveTrend 指标计算
- 📈 市值筛选（默认 ≥ 100亿美元）
- 🟢 超卖信号 (WT1 ≤ -60)
- 🔴 超买信号 (WT1 ≥ 60)
- 🔔 金叉/死叉检测
- 📱 Telegram 通知（可选）
- ⏰ GitHub Actions 自动运行

## 使用方式

### 方式1：本地运行

```bash
# 安装依赖
pip install -r requirements.txt

# 运行扫描器
python scanner.py
```

### 方式2：Streamlit 网页界面

```bash
# 本地运行
streamlit run app.py

# 或部署到 Streamlit Cloud
# 1. Fork 这个仓库
# 2. 访问 share.streamlit.io
# 3. 连接你的 GitHub 仓库
# 4. 选择 app.py 作为入口
```

### 方式3：GitHub Actions 自动运行

1. Fork 这个仓库
2. 在 Settings > Secrets 添加（可选）：
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
3. 启用 Actions
4. 每天美股收盘后自动扫描

## WaveTrend 指标说明

WaveTrend 是一个基于 HLC3 的动量指标：

```
AP = (High + Low + Close) / 3
ESA = EMA(AP, 10)
D = EMA(|AP - ESA|, 10)
CI = (AP - ESA) / (0.015 * D)
WT1 = EMA(CI, 21)
WT2 = SMA(WT1, 4)
```

**信号解读：**

| WT1 值 | 信号 | 含义 |
|--------|------|------|
| ≥ 60 | 🔴 超买 | 可能见顶，考虑止盈 |
| 53-60 | 🟡 接近超买 | 观察，可能即将超买 |
| -53 to 53 | ⚪ 中性 | 无明确信号 |
| -60 to -53 | 🟡 接近超卖 | 观察，可能即将超卖 |
| ≤ -60 | 🟢 超卖 | 可能见底，寻找做多机会 |

**交叉信号：**
- 🔼 金叉：WT1 上穿 WT2，看涨
- 🔽 死叉：WT1 下穿 WT2，看跌

## 股票池

### 纳斯达克100
AAPL, MSFT, AMZN, NVDA, GOOGL, META, TSLA, AVGO, COST, PEP, CSCO, NFLX, AMD, ADBE...

### 高波动股票（可选）
MSTR, COIN, HOOD, CRWV, PLTR, SOFI, RKLB, IONQ, RGTI, QUBT

## 配置 Telegram 通知

1. 创建 Telegram Bot：
   - 找 @BotFather
   - 发送 `/newbot`
   - 获取 Bot Token

2. 获取 Chat ID：
   - 找 @userinfobot
   - 发送任意消息
   - 获取你的 Chat ID

3. 添加 GitHub Secrets：
   - `TELEGRAM_BOT_TOKEN`: 你的 Bot Token
   - `TELEGRAM_CHAT_ID`: 你的 Chat ID

4. 启用 GitHub Actions 中的 Telegram 通知

## 文件结构

```
wavetrend_scanner/
├── scanner.py              # 主扫描程序
├── app.py                  # Streamlit 网页界面
├── notify_telegram.py      # Telegram 通知模块
├── requirements.txt        # Python 依赖
├── README.md               # 说明文档
├── data/                   # 扫描结果存储
│   └── latest_scan.json
└── .github/
    └── workflows/
        └── daily_scan.yml  # GitHub Actions 配置
```

## 免责声明

本工具仅供学习和参考，不构成投资建议。投资有风险，入市需谨慎。

## License

MIT
