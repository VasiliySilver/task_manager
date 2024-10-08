from fastapi import FastAPI
from app.routes import router as tasks_router

app = FastAPI(title="Tasks Service", version="0.1.0")

app.include_router(tasks_router, prefix="/tasks", tags=["tasks"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
