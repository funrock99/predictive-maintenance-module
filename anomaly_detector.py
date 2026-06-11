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
    def __init__(self, window_size: int = 30, threshold_z: float = 3.0, use_ml: bool = True):
        self.window_size = window_size
        self.threshold_z = threshold_z
        self.use_ml = use_ml
        
        # 架構優化展示點 (面試用)：
        # 改存多維度向量 [temperature, pressure, vibration]
        # 以便提供給 Isolation Forest 進行聯合分佈評估
        self.buffers: Dict[str, deque] = {}
        
        # 呼應履歷：預留 Isolation Forest 擴充介面
        if self.use_ml:
            if HAS_SKLEARN:
                # contamination: 預期異常的比例。這裡設定 0.05 代表我們假設 5% 是異常
                self.if_model = IsolationForest(contamination=0.05, random_state=42)
                logger.info("已啟用 Isolation Forest 進階多維度異常偵測模式")
            else:
                self.use_ml = False
                logger.warning("未安裝 scikit-learn，降級回 Z-Score 模式")

    def _init_machine_buffer(self, machine_id: str):
        if machine_id not in self.buffers:
            self.buffers[machine_id] = deque(maxlen=self.window_size)

    def detect(self, data: dict) -> dict:
        """
        接收單筆標準化數據，回傳檢測結果
        """
        machine_id = data.get("machine_id")
        if not machine_id:
            return {"is_anomaly": False, "reason": "No machine_id provided"}

        self._init_machine_buffer(machine_id)
        
        # 提取特徵向量
        features = [
            data.get("temperature", 0.0),
            data.get("pressure", 0.0),
            data.get("vibration", 0.0)
        ]
        feature_names = ["temperature", "pressure", "vibration"]
        
        buffer = self.buffers[machine_id]
        
        result = {
            "is_anomaly": False,
            "anomalies": {},
            "ml_score": 0.0
        }

        # 必須要有足夠的歷史資料才能進行檢測 (至少累積 20 筆作為滑動視窗基準)
        if len(buffer) >= 20: 
            X = np.array(buffer)
            latest_point = np.array(features).reshape(1, -1)
            
            if self.use_ml:
                # === Isolation Forest 多維度異常偵測 ===
                # 此處因無預先資料，採用動態擬合 (Dynamic Fit) 最新 Window 進行示範。
                self.if_model.fit(X)
                
                # 預測最新的一筆資料 (1 為正常，-1 為異常)
                prediction = self.if_model.predict(latest_point)
                score = self.if_model.decision_function(latest_point)[0] # 分數越低越異常
                
                result["ml_score"] = round(float(score), 3)
                
                if prediction[0] == -1:
                    result["is_anomaly"] = True
                    result["anomalies"]["isolation_forest"] = {
                        "message": "多維度聯合異常 (Multiple sensors deviated simultaneously)",
                        "ml_score": result["ml_score"]
                    }
                    
                    # 特徵歸因 (Feature Attribution)：簡單找出偏離均值最多的特徵提供提示
                    means = np.mean(X, axis=0)
                    stds = np.std(X, axis=0) + 1e-6
                    z_scores = np.abs(latest_point[0] - means) / stds
                    max_z_idx = np.argmax(z_scores)
                    
                    result["anomalies"]["root_cause_hint"] = {
                        "feature": feature_names[max_z_idx],
                        "deviation_z_score": round(z_scores[max_z_idx], 2)
                    }
            else:
                # === 降級：單變量 Z-Score ===
                means = np.mean(X, axis=0)
                stds = np.std(X, axis=0) + 1e-6
                
                z_scores = np.abs(latest_point[0] - means) / stds
                
                for i, z in enumerate(z_scores):
                    if z > self.threshold_z:
                        result["is_anomaly"] = True
                        result["anomalies"][feature_names[i]] = {
                            "value": latest_point[0][i],
                            "z_score": round(z, 2),
                            "mean": round(means[i], 2)
                        }

        # 將新資料加入緩衝區 (放在檢測之後，避免異常值過度影響當前判定基準)
        buffer.append(features)

        return result
