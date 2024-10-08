from fastapi import FastAPI, HTTPException, Request
from httpx import AsyncClient
import os

app = FastAPI(title="API Gateway")

AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://auth-service:8000")
TASK_SERVICE_URL = os.getenv("TASK_SERVICE_URL", "http://task-service:8000")
PROJECT_SERVICE_URL = os.getenv("PROJECT_SERVICE_URL", "http://project-service:8000")
NOTIFICATION_SERVICE_URL = os.getenv("NOTIFICATION_SERVICE_URL", "http://notification-service:8000")

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def gateway(path: str, request: Request):
    client = AsyncClient()

    if path.startswith("auth"):
        url = f"{AUTH_SERVICE_URL}/{path}"
    elif path.startswith("tasks"):
        url = f"{TASK_SERVICE_URL}/{path}"
    elif path.startswith("projects"):
        url = f"{PROJECT_SERVICE_URL}/{path}"
    elif path.startswith("notifications"):
        url = f"{NOTIFICATION_SERVICE_URL}/{path}"
    else:
        raise HTTPException(status_code=404, detail="Not Found")

    headers = {key: value for key, value in request.headers.items() if key != "host"}
    
    response = await client.request(
        method=request.method,
        url=url,
        headers=headers,
        params=request.query_params,
        data=await request.body()
    )

    return response.json()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
