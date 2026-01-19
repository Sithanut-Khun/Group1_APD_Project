# from fastapi import FastAPI
# from fastapi.middleware.cors import CORSMiddleware

# # Relative imports
# from .database import engine
# from .models import Base
# from .routers import pose, history 

# app = FastAPI()

# # CORS for frontend
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # Create DB tables (if they don't exist)
# Base.metadata.create_all(bind=engine)

# # Include the routers
# app.include_router(pose.router)
# app.include_router(history.router)

# @app.get("/")
# def root():
#     """Root endpoint"""
#     return {
#         "message": "NeuralPose API",
#         "version": "1.0.0",
#         "status": "running",
#         "endpoints": {
#             "health": "/health",
#             "predict": "/predict",
#             "history": "/history"
#         }
#     }

# @app.get("/health")
# def health_check():
#     """Health check endpoint"""
#     return {"status": "healthy"}

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles #

# Relative imports
from .database import engine
from .models import Base
from .routers import pose, history 

app = FastAPI(root_path="/api")

# 1. Mount the static directory
UPLOAD_DIR = "uploads" 

if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

# This line links the URL path /outputs to the physical folder /uploads
app.mount("/outputs", StaticFiles(directory=UPLOAD_DIR), name="outputs") #

# 2. CORS configuration (keep your existing setup)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://api.pose.ams.cards", "https://api.pose.ams.cards"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. Create DB tables
Base.metadata.create_all(bind=engine) #

# 4. Include routers
app.include_router(pose.router) #
app.include_router(history.router) #

@app.get("/")
def root():
    return {"message": "NeuralPose API", "status": "running"}

@app.get("/health")
def health_check():
    return {"status": "healthy"} #