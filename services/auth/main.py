from fastapi import FastAPI
from app.routes import router as auth_router

app = FastAPI(title="Auth Service", version="0.1.0")

app.include_router(auth_router, prefix="/auth", tags=["auth"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)