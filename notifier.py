import os
import logging
import httpx
from datetime import datetime
from dotenv import load_dotenv

# 載入 .env 檔案中的環境變數
load_dotenv()

# 設定基本的系統日誌格式
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("PdM-Notifier")

class Notifier:
    def __init__(self):
        # 從環境變數讀取 Line Channel Access Token (若無則僅印出 Log)
        self.line_token = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
        self.line_api_url = "https://api.line.me/v2/bot/message/broadcast" # 這裡簡化使用 broadcast

    async def send_alert(self, machine_id: str, anomalies: dict):
        """處理並發送警報 (非同步版本)"""
        # 1. 系統日誌 (SysLog)
        alert_msg = f"[ALERT] 機台 {machine_id} 偵測到異常數據！"
        for key, info in anomalies.items():
             alert_msg += f" {key}: {info['value']} (Z-Score: {info['z_score']})"
        
        logger.warning(alert_msg)

        # 2. Line Bot 推播 (若有設定 Token)
        if self.line_token:
            await self._send_line_message(machine_id, alert_msg)
        else:
            logger.info("未設定 LINE_CHANNEL_ACCESS_TOKEN，略過 Line 通知發送 (模擬模式)")

    async def _send_line_message(self, machine_id: str, text: str):
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.line_token}"
        }
        
        payload = {
            "messages": [
                {
                    "type": "text",
                    "text": f"⚠️ 機台警報 ⚠️\n機台 ID: {machine_id}\n時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n詳情: {text}"
                }
            ]
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(self.line_api_url, headers=headers, json=payload)
                if response.status_code == 200:
                    logger.info(f"Line 通知已成功發送至負責人員")
                else:
                    logger.error(f"Line 通知發送失敗: {response.text}")
        except Exception as e:
            logger.error(f"Line 通知發送發生例外錯誤: {str(e)}")
