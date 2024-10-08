from fastapi import FastAPI
from app.routes import router as projects_router

app = FastAPI(title="Projects Service", version="0.1.0")

app.include_router(projects_router, prefix="/projects", tags=["projects"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)