# Feedback API

問題回報服務 - 支援圖片上傳與郵件通知。

## 功能

- **POST /api/feedback** - 提交問題回報，支援圖片附件
  - `description`: 問題描述（必填）
  - `email`: 用戶 Email（選填）
  - `images`: 最多 3 張圖片，每張最大 5MB

## 環境變數

```bash
# GCS 設定（用於圖片上傳）
GCS_SERVICE_ACCOUNT_JSON=<base64 encoded service account json>
GCS_BUCKET_NAME=<bucket name>

# SMTP 設定（用於發送郵件）
SMTP_HOST=<smtp host>
SMTP_PORT=<smtp port>
SMTP_USERNAME=<smtp username>
SMTP_PASSWORD=<smtp password>
SMTP_RECIPIENTS=<comma separated emails>
```

## 本地開發

```bash
# 安裝依賴
pip install -r requirements.txt

# 啟動服務
uvicorn app.main:app --reload
```

## 部署

專案已配置 Vercel 部署，直接 push 到 Git 即可自動部署。
