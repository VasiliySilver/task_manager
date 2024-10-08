import httpx
import os

NOTIFICATION_SERVICE_URL = os.getenv("NOTIFICATION_SERVICE_URL", "http://notification-service:8000")

async def send_notification(user_id: int, message: str):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{NOTIFICATION_SERVICE_URL}/notifications/",
                json={"user_id": user_id, "message": message}
            )
            response.raise_for_status()
        except httpx.HTTPError as e:
            print(f"Error sending notification: {e}")
