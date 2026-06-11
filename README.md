# 機台預警與預測性維護模組 (Predictive Maintenance - PdM)

這是一個用於半導體封裝製造現場 (OSAT) 的機台預警與預測性維護 (PdM) 雛型系統。透過邊緣計算架構即時接收高頻感測器數據，結合滑動窗口與 Z-Score 演算法偵測異常，並透過 WebSocket 即時更新至具有暗黑模式與玻璃擬物化的高質感前端戰情儀表板，同時具備 Line Bot 告警擴充能力。

## ✨ 核心特色
- **高頻時序數據流接收**：使用 FastAPI 實現非同步輕量微服務，模擬邊緣運算。
- **即時異常檢測**：實作基於 Z-Score 與 Sliding Window 的串流資料檢測邏輯。
- **高質感戰情儀表板**：Glassmorphism 風格 UI，結合 Chart.js 與 WebSocket 提供順暢的實時數據折線圖。
- **即時告警機制**：支援 SysLog 與 Line Bot 通知推播。

---

## 🚀 操作步驟 (Operation Steps)

### 1. 環境準備
請確保您的系統已安裝 Python 3.8 或以上版本，並安裝所需套件：
```bash
pip install fastapi uvicorn pydantic numpy requests websockets python-dotenv httpx
```
*(備註：前端使用 CDN 引入 Chart.js，無需額外安裝 Node.js 套件。)*

### 2. 設定 Line Bot 告警推播 (選配)
本專案支援主動將機台異常警報推播至您的 Line。由於系統是單向調用 Line Push/Broadcast API，因此**本機執行即可直接發送，無須開放對外 IP 或使用 ngrok 轉址**。
1. 請將專案目錄下的 `.env.example` 複製或重新命名為 `.env`。
2. 前往 [LINE Developers Console](https://developers.line.biz/) 取得 Messaging API 的 `Channel access token (long-lived)`。
3. 將該 Token 填入 `.env` 檔案中的 `LINE_CHANNEL_ACCESS_TOKEN` 欄位。

### 3. 啟動後端 API 與儀表板服務
開啟第一個終端機 (Terminal / PowerShell)，進入專案目錄並啟動 FastAPI：
```bash
cd E:\機台預警與預測性維護模組
python main.py
```
> 服務將運行在 `http://127.0.0.1:8000`

### 4. 啟動機台數據模擬器
開啟**第二個**終端機視窗，啟動模擬器持續發送感測數據：
```bash
cd E:\機台預警與預測性維護模組
python sensor_simulator.py
```
> 模擬器會以每秒 1 筆的頻率產生溫度、壓力與震動數據，並有一定機率隨機注入「突波 (Spike)」或「緩慢偏移 (Drift)」異常。

### 5. 觀看即時戰情儀表板
請開啟瀏覽器，前往：
👉 **[http://127.0.0.1:8000](http://127.0.0.1:8000)**

您將會在畫面上看見即時更新的數據圖表。當模擬器產生異常數據時，圖表右下角將會滑出紅色的 Toast 警告，並在終端機中留下 SysLog 紀錄（若您有設定 Line Token，此時您的手機也會同步收到警報訊息）。

### 6. 停止服務
若要結束監控，請分別在兩個終端機中按下 `Ctrl + C` 終止服務。

---

## 🛠️ 專案結構
* `main.py` - FastAPI 進入點與 WebSocket 廣播邏輯。
* `anomaly_detector.py` - Z-Score 異常偵測核心演算法。
* `notifier.py` - 日誌記錄與 Line Bot API 串接管理員。
* `sensor_simulator.py` - 虛擬機台數據與異常生成器。
* `static/index.html` - 戰情儀表板前端 UI。
* `static/app.js` - WebSocket 接收與 Chart.js 動態渲染邏輯。
* `pdm_project_plan.md` - 原始開發計畫書。
