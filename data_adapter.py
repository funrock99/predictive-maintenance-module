from typing import Dict, Any

class DataAdapter:
    """
    資料適配層 (Adapter Pattern)
    負責將來自不同資料源（內部模擬器、外部 CIM WebSocket 等）的原始資料
    轉換為機器學習模型與 API 邏輯可接受的標準化格式。
    """
    
    @staticmethod
    def normalize_sensor_data(raw_data: Dict[str, Any], source: str = "simulator") -> Dict[str, Any]:
        """
        將原始資料正規化。
        :param raw_data: 來源資料字典
        :param source: 'simulator' (本機) 或 'cim' (外部 CIM 系統)
        :return: 正規化後的標準格式字典
        """
        if source == "simulator":
            # 本機模擬器的格式已經很接近標準格式
            return {
                "machine_id": raw_data.get("machine_id", "unknown"),
                "timestamp": raw_data.get("timestamp"),
                "temperature": float(raw_data.get("temperature", 0.0)),
                "pressure": float(raw_data.get("pressure", 0.0)),
                "vibration": float(raw_data.get("vibration", 0.0)),
                "status": raw_data.get("status", "running"),
                "source": source
            }
        elif source == "cim":
            # 假設未來 CIM 系統傳來的格式可能有巢狀結構，例如:
            # {"equipment_id": "EQP-01", "metrics": {"temp": 25.0, "pres": 1.2, "vib": 0.5}, "time": "..."}
            # 在此進行轉換
            metrics = raw_data.get("metrics", {})
            return {
                "machine_id": raw_data.get("equipment_id", raw_data.get("machine_id", "unknown")),
                "timestamp": raw_data.get("time", raw_data.get("timestamp")),
                "temperature": float(metrics.get("temp", raw_data.get("temperature", 0.0))),
                "pressure": float(metrics.get("pres", raw_data.get("pressure", 0.0))),
                "vibration": float(metrics.get("vib", raw_data.get("vibration", 0.0))),
                "status": raw_data.get("status", "running"),
                "source": source
            }
        else:
            raise ValueError(f"Unknown data source: {source}")
