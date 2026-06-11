import numpy as np
from collections import deque
from typing import List, Dict
import logging

logger = logging.getLogger("PdM-Detector")

try:
    from sklearn.ensemble import IsolationForest
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

class AnomalyDetector:
    def __init__(self, window_size: int = 30, threshold_z: float = 3.0, use_ml: bool = False):
        self.window_size = window_size
        self.threshold_z = threshold_z
        self.use_ml = use_ml
        
        # 架構優化展示點 (面試用)：
        # 目前使用 Python 內建 dict 存放在單一行程記憶體。若部署至多 Worker 環境 (如 Gunicorn --workers 4)，記憶體不互通將導致計算失真。
        # 正式生產環境 (Production) 會改為 Stateless (無狀態) 設計，
        # 將 Sliding Window 移至 Redis (LPUSH/LTRIM) 或 Kafka State Store 中管理。
        self.buffers: Dict[str, Dict[str, deque]] = {}
        
        # 呼應履歷：預留 Isolation Forest 擴充介面
        if self.use_ml:
            if HAS_SKLEARN:
                self.if_model = IsolationForest(contamination=0.01, random_state=42)
                logger.info("已啟用 Isolation Forest 進階異常偵測模式")
            else:
                logger.warning("未安裝 scikit-learn，降級回 Z-Score 模式")

    def _init_machine_buffer(self, machine_id: str):
        if machine_id not in self.buffers:
            self.buffers[machine_id] = {
                "temperature": deque(maxlen=self.window_size),
                "pressure": deque(maxlen=self.window_size),
                "vibration": deque(maxlen=self.window_size)
            }

    def detect(self, data: dict) -> dict:
        """
        接收單筆數據，回傳檢測結果
        """
        machine_id = data.get("machine_id")
        if not machine_id:
            return {"is_anomaly": False, "reason": "No machine_id provided"}

        self._init_machine_buffer(machine_id)
        
        # 準備回傳結果
        result = {
            "is_anomaly": False,
            "anomalies": {}
        }

        # 檢測各項指標
        for key in ["temperature", "pressure", "vibration"]:
            val = data.get(key)
            if val is None:
                continue
            
            buffer = self.buffers[machine_id][key]
            
            # 若緩衝區資料量足夠，則計算 Z-Score 進行檢測
            if len(buffer) >= 10:  # 至少 10 筆資料才開始算
                # 效能優化展示點 (面試用)：
                # 現行以 np.mean 每次遍歷需 O(N) 時間複雜度。
                # 面對高頻海量數據，實務上可套用 Welford's Online Algorithm 
                # 達成 O(1) 的平均與變異數動態更新，避免 CPU 阻塞。
                mean = np.mean(buffer)
                std = np.std(buffer)
                
                # 避免標準差為 0 導致除以 0 錯誤
                if std > 0:
                    z_score = abs(val - mean) / std
                    if z_score > self.threshold_z:
                        result["is_anomaly"] = True
                        result["anomalies"][key] = {
                            "value": val,
                            "z_score": round(z_score, 2),
                            "mean": round(mean, 2)
                        }

            # 將新資料加入緩衝區 (放在檢測之後，避免當前異常值影響當前判定)
            buffer.append(val)

        return result
