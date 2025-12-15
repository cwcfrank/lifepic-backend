# ParkRadar Backend API

停車場資料中台服務 - 整合 TDX 運輸資料流通服務

## 功能特色

- 🚗 整合 TDX API 抓取全台停車場資料
- 📊 提供 RESTful API 供前端 App 使用
- 🗄️ 使用 Aiven PostgreSQL 儲存資料
- ☁️ 部署於 Vercel Serverless

## 專案結構

```
parkradar-backend/
├── api/index.py          # Vercel 入口點
├── app/
│   ├── main.py           # FastAPI 應用程式
│   ├── config.py         # 設定管理
│   ├── database.py       # 資料庫連線
│   ├── models/           # SQLAlchemy 模型
│   ├── schemas/          # Pydantic 資料結構
│   ├── services/         # TDX 整合服務
│   └── routers/          # API 路由
├── requirements.txt
├── vercel.json
└── .env
```

## API 端點

### 停車場查詢
| 方法 | 路徑 | 說明 |
|------|------|------|
| GET | `/api/parking` | 查詢停車場列表 |
| GET | `/api/parking/{park_id}` | 查詢單一停車場 |
| GET | `/api/parking/nearby` | 查詢附近停車場 |
| GET | `/api/parking/cities` | 取得支援的縣市列表 |

### 資料同步
| 方法 | 路徑 | 說明 |
|------|------|------|
| POST | `/api/sync/trigger` | 觸發資料同步（需 API Key） |
| GET | `/api/sync/status` | 查詢同步狀態 |

## 本地開發

```bash
# 安裝依賴
pip install -r requirements.txt

# 設定環境變數
cp .env.example .env
# 編輯 .env 填入實際憑證

# 啟動開發伺服器
uvicorn app.main:app --reload

# 存取 API 文件
open http://localhost:8000/docs
```

## 部署至 Vercel

```bash
# 安裝 Vercel CLI
npm i -g vercel

# 登入
vercel login

# 部署
vercel

# 設定環境變數
vercel env add DATABASE_URL
vercel env add TDX_CLIENT_ID
vercel env add TDX_CLIENT_SECRET
vercel env add SYNC_API_KEY
```

## 觸發資料同步

```bash
# 同步所有縣市
curl -X POST "https://your-app.vercel.app/api/sync/trigger" \
  -H "X-API-Key: your-sync-api-key"

# 同步特定縣市
curl -X POST "https://your-app.vercel.app/api/sync/trigger" \
  -H "X-API-Key: your-sync-api-key" \
  -H "Content-Type: application/json" \
  -d '{"cities": ["Taipei", "Taichung"]}'
```

## 環境變數

| 變數名稱 | 說明 |
|----------|------|
| DATABASE_URL | PostgreSQL 連線字串 |
| TDX_CLIENT_ID | TDX API Client ID |
| TDX_CLIENT_SECRET | TDX API Client Secret |
| SYNC_API_KEY | 同步 API 驗證金鑰 |

## 定期同步

Vercel Hobby 方案不支援 Cron Jobs，建議使用：
- [cron-job.org](https://cron-job.org) - 免費定時任務服務
- GitHub Actions - 可設定 schedule workflow
- Vercel Pro - 支援 Cron Jobs
