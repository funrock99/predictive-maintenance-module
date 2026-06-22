import os
import json

from fastapi import FastAPI, BackgroundTasks, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn
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
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        import asyncio
        # 取得當前連線快照，避免異步執行時 active_connections 發生變動
        connections_snapshot = list(self.active_connections)
        if not connections_snapshot:
            return
            
        # 優化：使用 asyncio.gather 達成真正的非同步並發推送，避免在 for 迴圈中造成後續連線阻塞
        tasks = [connection.send_text(message) for connection in connections_snapshot]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 處理異常斷線：如果推播失敗，自動清除該失效連線
        for connection, result in zip(connections_snapshot, results):
            if isinstance(result, Exception):
                self.disconnect(connection)

manager = ConnectionManager()

# 掛載靜態檔案 (前端頁面)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def get_index():
    return FileResponse("static/index.html")

@app.post("/api/v1/sensors")
async def receive_sensor_data(
    data: dict,
    background_tasks: BackgroundTasks,
    source: str = Query(default="simulator", pattern="^(simulator|cim)$")
):
    effective_source = data.get("source", source)
    if effective_source not in {"simulator", "cim"}:
        raise HTTPException(status_code=400, detail="Unsupported source. Use 'simulator' or 'cim'.")

    if effective_source == "simulator" and not data.get("machine_id"):
        raise HTTPException(status_code=422, detail="Simulator payload requires 'machine_id'.")

    if effective_source == "cim":
        cim_payload = data.get("cim_payload") if isinstance(data.get("cim_payload"), dict) else data
        if not cim_payload.get("equipment_id") and not cim_payload.get("machine_id"):
            raise HTTPException(status_code=422, detail="CIM payload requires 'equipment_id' or 'machine_id'.")

    try:
        normalized_data = DataAdapter.normalize_sensor_data(data, source=effective_source)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=f"Invalid sensor payload: {exc}") from exc
    
    # 進行進階異常偵測
    detection_result = detector.detect(normalized_data)
    
    if detection_result.get("is_anomaly"):
        # 優化 (Phase 3)：觸發 Notification Manager 移至 BackgroundTasks，確保 Sensor API 瞬間回傳 200 OK
        background_tasks.add_task(
            notifier.send_alert,
            normalized_data["machine_id"],
            detection_result.get("anomalies", {})
        )

    # Phase 4: 透過 WebSocket 廣播給前端 Dashboard
    payload = {
        "machine_id": normalized_data["machine_id"],
        "timestamp": normalized_data["timestamp"],
        "temperature": normalized_data["temperature"],
        "pressure": normalized_data["pressure"],
        "vibration": normalized_data["vibration"],
        "status": normalized_data["status"],
        "source": normalized_data["source"],
        "is_anomaly": detection_result.get("is_anomaly", False),
        "anomalies": detection_result.get("anomalies", {}),
        "ml_score": detection_result.get("ml_score", 0.0)
    }
    await manager.broadcast(json.dumps(payload))

    return {
        "status": "success",
        "machine_id": normalized_data["machine_id"],
        "source": normalized_data["source"],
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
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PDM_PORT", "8001")), reload=True)
