import time
import random
import json
import requests
from datetime import datetime

class SensorSimulator:
    def __init__(self, machine_id: str):
        self.machine_id = machine_id
        # 設定初始基礎值
        self.base_temperature = 75.0  # 正常溫度 75°C
        self.base_pressure = 100.0    # 正常壓力 100 kPa
        self.base_vibration = 50.0    # 正常震動 50 Hz
        
        # 狀態控制
        self.anomaly_mode = "normal"  # normal, spike, drift
        self.drift_step = 0
        
    def _add_noise(self, value: float, variance: float) -> float:
        """加入常態分佈的雜訊"""
        return value + random.gauss(0, variance)

    def trigger_anomaly(self, mode: str):
        """觸發異常注入 (手動或隨機觸發)"""
        if mode in ["spike", "drift", "normal"]:
            self.anomaly_mode = mode
            self.drift_step = 0
            print(f"[{datetime.now().isoformat()}] Machine {self.machine_id} entering {mode} mode.")

    def generate_data(self) -> dict:
        """產生單筆感測器資料"""
        # 1. 基礎值與雜訊
        temp = self._add_noise(self.base_temperature, 1.5)
        press = self._add_noise(self.base_pressure, 2.0)
        vib = self._add_noise(self.base_vibration, 0.8)

        # 2. 異常注入處理
        if self.anomaly_mode == "spike":
            # 突波：數值突然暴增
            temp += random.uniform(15.0, 25.0)
            vib += random.uniform(20.0, 30.0)
            # 突波通常是短暫的，一次後恢復正常 (可視需求調整)
            self.anomaly_mode = "normal" 
            
        elif self.anomaly_mode == "drift":
            # 緩慢偏移：數值隨時間逐漸上升
            self.drift_step += 1
            temp += self.drift_step * 0.5
            press += self.drift_step * 0.3
            # 設定一個上限避免無限增加，或讓外部控制何時結束 drift
            if self.drift_step > 20:
                 self.anomaly_mode = "normal"
                 self.drift_step = 0

        # 3. 組合資料
        payload = {
            "machine_id": self.machine_id,
            "timestamp": datetime.now().isoformat(),
            "temperature": round(temp, 2),
            "pressure": round(press, 2),
            "vibration": round(vib, 2),
            "status": "simulating"
        }
        return payload

if __name__ == "__main__":
    print("啟動機台數據模擬器...")
    simulator = SensorSimulator("MCH-001")
    
    try:
        iteration = 0
        while True:
            # 每 10 次迴圈有小機率觸發隨機異常來測試
            if iteration % 10 == 0 and iteration > 0:
                if random.random() < 0.2:
                    simulator.trigger_anomaly("spike")
                elif random.random() < 0.1:
                    simulator.trigger_anomaly("drift")

            data = simulator.generate_data()
            print(json.dumps(data))
            
            # 傳送至 FastAPI
            try:
                response = requests.post("http://127.0.0.1:8000/api/v1/sensors", json=data)
                if response.status_code != 200:
                    print(f"API Error: {response.status_code}")
            except requests.exceptions.ConnectionError:
                pass # 如果 API 沒開，先忽略錯誤

            iteration += 1
            time.sleep(1) # 每秒產生一筆
            
    except KeyboardInterrupt:
        print("\n停止模擬器。")
