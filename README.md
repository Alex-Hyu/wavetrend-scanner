# WaveTrend 扫描器 V3.0 - Google Sheets 配置指南

## 📋 概述

V3.0 使用 Google Sheets 存储追踪数据，实现持久化存储。

---

## 🔧 配置步骤

### 第一步：创建 Google Cloud 项目

1. 访问 [Google Cloud Console](https://console.cloud.google.com/)
2. 创建新项目（或选择已有项目）
3. 记住项目名称

### 第二步：启用 API

1. 在 Google Cloud Console 左侧菜单，点击 **APIs & Services** > **Library**
2. 搜索并启用以下两个 API：
   - **Google Sheets API**
   - **Google Drive API**

### 第三步：创建服务账号

1. 点击 **APIs & Services** > **Credentials**
2. 点击 **Create Credentials** > **Service Account**
3. 填写服务账号名称（如 `wavetrend-tracker`）
4. 点击 **Done**

### 第四步：生成密钥

1. 在 Credentials 页面，点击刚创建的服务账号
2. 点击 **Keys** 标签
3. 点击 **Add Key** > **Create new key**
4. 选择 **JSON** 格式
5. 下载 JSON 文件（保存好，只能下载一次）

### 第五步：配置 Streamlit Secrets

1. 打开 Streamlit Cloud 的应用设置
2. 点击 **Settings** > **Secrets**
3. 粘贴以下内容（用你的 JSON 文件内容替换）：

```toml
[gcp_service_account]
type = "service_account"
project_id = "your-project-id"
private_key_id = "your-private-key-id"
private_key = "-----BEGIN PRIVATE KEY-----\nYOUR_PRIVATE_KEY_HERE\n-----END PRIVATE KEY-----\n"
client_email = "your-service-account@your-project.iam.gserviceaccount.com"
client_id = "your-client-id"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "your-cert-url"
```

⚠️ **注意**：`private_key` 中的换行符要保留为 `\n`

---

## 📝 JSON 文件转换为 TOML 格式

你下载的 JSON 文件格式如下：

```json
{
  "type": "service_account",
  "project_id": "xxx",
  "private_key_id": "xxx",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
  ...
}
```

转换为 TOML 格式时：
1. 添加 `[gcp_service_account]` 头
2. 将 JSON 的 `"key": "value"` 改为 TOML 的 `key = "value"`
3. 保持 `private_key` 中的 `\n` 不变

---

## ✅ 验证配置

配置完成后：
1. 重启 Streamlit 应用
2. 访问 **追踪** 页面
3. 如果没有错误提示，说明配置成功
4. 会自动创建名为 `WaveTrend_Tracking` 的 Google Sheets 文件

---

## 📊 Google Sheets 结构

应用会自动创建以下工作表：

### Bullish（做多信号）
| 列 | 说明 |
|---|---|
| symbol | 股票代码 |
| d0_date | 信号日期 |
| d0_price | D0 价格 |
| current_price | 当前价格 |
| change_pct | 涨跌幅 |
| trading_days | 交易日数 |
| score | 评分 |
| score_details | 评分详情 |
| status | 状态 |
| result | 判定结果 |

### Bearish（做空信号）
结构同上

---

## 🔒 安全提示

1. **不要**将 JSON 密钥文件提交到 GitHub
2. **不要**在代码中硬编码密钥
3. 只通过 Streamlit Secrets 管理敏感信息

---

## ❓ 常见问题

### Q: 提示 "无法连接 Google Sheets"
A: 检查 Secrets 配置是否正确，特别是 `private_key` 格式

### Q: 提示 "权限不足"
A: 确保已启用 Google Sheets API 和 Google Drive API

### Q: 数据没有保存
A: 检查服务账号是否有写入权限

---

## 📁 文件清单

```
wavetrend-scanner/
├── app.py              # 主程序
├── requirements.txt    # 依赖
└── README.md          # 本文档
```

---

## 🎯 使用流程

1. 扫描页面：筛选超买/超卖股票
2. 点击"一键追踪"或单独添加
3. 切换到追踪页面
4. 点击"刷新价格"更新数据
5. 查看准确率统计
