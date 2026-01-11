from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Relative imports
from .database import engine
from .models import Base
from .routers import pose, history 

app = FastAPI()

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create DB tables (if they don't exist)
Base.metadata.create_all(bind=engine)

# Include the routers
app.include_router(pose.router)
app.include_router(history.router)

@app.get("/")
def root():
    """Root endpoint"""
    return {
        "message": "NeuralPose API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "predict": "/predict",
            "history": "/history"
        }
    }

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

