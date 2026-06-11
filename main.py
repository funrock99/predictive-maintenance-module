from fastapi import FastAPI, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uvicorn
import json
from datetime import datetime
from anomaly_detector import AnomalyDetector
from notifier import Notifier
from data_adapter import DataAdapter

app = FastAPI(title="PdM Core API", description="進階機台預警與預測性維護 API", version="1.0.0")

# 初始化異常偵測器與通知器 (啟用 ML Isolation Forest)
detector = AnomalyDetector(window_size=50, threshold_z=3.0, use_ml=True)
notifier = Notifier()

# WebSocket 連線管理
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        import asyncio
        # 優化：使用 asyncio.gather 達成真正的非同步並發推送，避免在 for 迴圈中造成後續連線阻塞
        tasks = [connection.send_text(message) for connection in self.active_connections]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

manager = ConnectionManager()

# 掛載靜態檔案 (前端頁面)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def get_index():
    return FileResponse("static/index.html")

class SensorData(BaseModel):
    machine_id: str
    timestamp: str
    temperature: float
    pressure: float
    vibration: float
    status: str

@app.post("/api/v1/sensors")
async def receive_sensor_data(data: SensorData, background_tasks: BackgroundTasks):
    # 優化：使用 model_dump 兼容最新 Pydantic V2 語法，展示對套件更迭的敏銳度
    data_dict = data.model_dump() if hasattr(data, "model_dump") else data.dict()
    
    # 資料適配層：將收到的資料標準化 (預設為本機 simulator)
    normalized_data = DataAdapter.normalize_sensor_data(data_dict, source="simulator")
    
    # 進行進階異常偵測
    detection_result = detector.detect(normalized_data)
    
    if detection_result.get("is_anomaly"):
        # 優化 (Phase 3)：觸發 Notification Manager 移至 BackgroundTasks，確保 Sensor API 瞬間回傳 200 OK
        background_tasks.add_task(notifier.send_alert, data.machine_id, detection_result.get("anomalies", {}))

    # Phase 4: 透過 WebSocket 廣播給前端 Dashboard
    payload = {
        "machine_id": data.machine_id,
        "timestamp": data.timestamp,
        "temperature": data.temperature,
        "pressure": data.pressure,
        "vibration": data.vibration,
        "is_anomaly": detection_result.get("is_anomaly", False),
        "anomalies": detection_result.get("anomalies", {}),
        "ml_score": detection_result.get("ml_score", 0.0)
    }
    await manager.broadcast(json.dumps(payload))

    return {
        "status": "success",
        "machine_id": data.machine_id,
        "is_anomaly": detection_result.get("is_anomaly"),
        "anomalies": detection_result.get("anomalies", {})
    }

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # 保持連線
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

if __name__ == "__main__":
    print("啟動 PdM Core API 微服務...")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
