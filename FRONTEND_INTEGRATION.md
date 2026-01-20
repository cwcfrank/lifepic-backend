# ParkRadar Backend API Integration - Flutter 前端開發指南

## 專案背景

ParkRadar 是一個停車場資訊 App，後端已部署在 Vercel，整合 TDX 運輸資料流通服務，提供全台停車場即時資訊。

## API Base URL

```
https://parkradar-backend.vercel.app
```

---

## API 端點規格

### 1. 取得支援縣市列表

**GET** `/api/parking/cities`

回應：
```json
{
  "cities": [
    {"code": "Taipei", "name_zh": "臺北市", "name_en": "Taipei City"},
    {"code": "Taichung", "name_zh": "臺中市", "name_en": "Taichung City"},
    ...
  ]
}
```

---

### 2. 查詢停車場列表

**GET** `/api/parking`

| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| city | string | ❌ | 縣市代碼（如 Taipei, Taichung） |
| has_available | boolean | ❌ | true = 只顯示有空位 |
| limit | int | ❌ | 每頁筆數 1-200，預設 50 |
| offset | int | ❌ | 分頁偏移，預設 0 |

範例請求：
```
GET /api/parking?city=Taipei&has_available=true&limit=20
```

回應：
```json
{
  "total": 113,
  "items": [
    {
      "id": "uuid",
      "park_id": "088",
      "name": "三張里地下停車場",
      "city": "Taipei",
      "address": "松平路81號地下室",
      "latitude": 25.03067,
      "longitude": 121.56693,
      "total_spaces": null,
      "available_spaces": 42,
      "fare_description": "小型車：計時 30元/時...",
      "parking_type": "OffStreet",
      "data_updated_at": "2025-12-15T20:39:29",
      "updated_at": "2025-12-15T12:41:33.177279"
    }
  ],
  "limit": 20,
  "offset": 0
}
```

---

### 3. 查詢單一停車場

**GET** `/api/parking/{park_id}`

範例請求：
```
GET /api/parking/088
```

回應：單一停車場物件（同上 items 內的結構）

---

### 4. 附近停車場搜尋（重要功能）

**GET** `/api/parking/nearby`

| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| lat | float | ✅ | 緯度 |
| lng | float | ✅ | 經度 |
| radius | int | ❌ | 搜尋半徑（公尺），100-10000，預設 1000 |
| limit | int | ❌ | 回傳筆數 1-100，預設 20 |

範例請求：
```
GET /api/parking/nearby?lat=25.0330&lng=121.5654&radius=1000&limit=10
```

回應：
```json
{
  "items": [
    {
      "park_id": "048",
      "name": "信義廣場地下停車場",
      "distance_meters": 103.99,
      "available_spaces": 0,
      "latitude": 25.03306,
      "longitude": 121.56643,
      ...
    }
  ],
  "center_lat": 25.033,
  "center_lng": 121.5654,
  "radius": 1000
}
```

**注意**：回應包含 `distance_meters` 表示距離查詢點的公尺數，已按距離排序。

---

## Flutter 實作建議

### 1. 建立 API Service

```dart
class ParkingApiService {
  static const String baseUrl = 'https://parkradar-backend.vercel.app';
  
  Future<List<ParkingLot>> getNearbyParking({
    required double lat,
    required double lng,
    int radius = 1000,
    int limit = 20,
  }) async {
    final response = await http.get(Uri.parse(
      '$baseUrl/api/parking/nearby?lat=$lat&lng=$lng&radius=$radius&limit=$limit'
    ));
    // 解析回應...
  }
}
```

### 2. 資料模型

```dart
class ParkingLot {
  final String parkId;
  final String name;
  final String city;
  final String? address;
  final double? latitude;
  final double? longitude;
  final int? totalSpaces;
  final int? availableSpaces;
  final String? fareDescription;
  final double? distanceMeters; // 只有 nearby API 會有
  final DateTime? dataUpdatedAt;
}
```

### 3. 地圖整合

搭配 Google Maps Flutter package，可使用 latitude/longitude 在地圖上標記停車場位置，並根據 available_spaces 顯示不同顏色標記。

---

## 支援的縣市代碼

```
Taipei, NewTaipei, Taoyuan, Taichung, Tainan, Kaohsiung,
Keelung, Hsinchu, HsinchuCounty, MiaoliCounty, ChanghuaCounty,
NantouCounty, YunlinCounty, ChiayiCounty, Chiayi, PingtungCounty,
YilanCounty, HualienCounty, TaitungCounty, PenghuCounty,
KinmenCounty, LienchiangCounty
```

---

## 注意事項

1. **所有 API 皆為公開端點**，無需驗證
2. **資料即時性**：available_spaces 是從 TDX 同步的即時資料
3. **CORS 已開啟**，Flutter Web 也可直接呼叫
4. **rate limit**：目前無限制，但請合理使用

## API 文件

完整互動式文件：https://parkradar-backend.vercel.app/docs
