from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from app.routes import router
from app.elasticsearch import create_index

app = FastAPI(title="Task Service", version="0.1.0")

@app.on_event("startup")
async def startup_event():
    create_index()

# Добавляем инструментацию Prometheus
Instrumentator().instrument(app).expose(app)

app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
