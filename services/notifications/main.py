from fastapi import FastAPI
from app.routes import router as notifications_router

app = FastAPI(title="Notifications Service", version="0.1.0")

app.include_router(notifications_router, prefix="/notifications", tags=["notifications"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)