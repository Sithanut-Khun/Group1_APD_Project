# import uuid
# from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
# from fastapi.middleware.cors import CORSMiddleware
# from fastapi.responses import JSONResponse
# from sqlalchemy.orm import Session
# from ultralytics import YOLO
# from PIL import Image
# import io
# from typing import List
# import os
# import numpy as np
# from datetime import datetime
# import tempfile  #
# from pathlib import Path

# from .database import get_db, engine
# from .models import Base, Prediction
# from .schemas import PredictionCreate, PredictionHistory, PredictionOut
# from .crud import create_prediction, get_predictions

# app = FastAPI()

# # CORS for frontend
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # Create DB tables
# Base.metadata.create_all(bind=engine)

# # Load YOLO model
# # print("Loading YOLOv8 model...")
# # model = YOLO('yolov8n-pose.pt')
# # print("Model loaded successfully!")
# print("Loading YOLOv8 model...")

# # Define the path where you want the model
# MODELS_DIR = Path(__file__).parent / "models"  # backend/app/models/
# MODEL_PATH = MODELS_DIR / "yolov8n-pose.pt"

# # Create models directory if it doesn't exist
# MODELS_DIR.mkdir(exist_ok=True)

# print(f"Looking for model at: {MODEL_PATH}")

# if MODEL_PATH.exists():
#     # Load from local file
#     model = YOLO(str(MODEL_PATH))
#     print("✓ Model loaded from local file")
# else:
#     # Download and save to our models directory
#     print("Model not found locally, downloading...")
    
#     # Download the model (this will temporarily save to current dir)
#     model = YOLO('yolov8n-pose.pt')
    
#     # Save it to our desired location
#     model.save(str(MODEL_PATH))
#     print(f"✓ Model downloaded and saved to: {MODEL_PATH}")

# print("Model loaded successfully!")

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
#     return {"status": "healthy", "model": "yolov8n-pose"}


# def classify_activity(keypoints_xy, keypoints_conf, img_width, img_height):
#     """
#     Improved activity classification with corrected priority order.
#     """
#     # COCO keypoint indices
#     NOSE = 0
#     LEFT_SHOULDER, RIGHT_SHOULDER = 5, 6
#     LEFT_ELBOW, RIGHT_ELBOW = 7, 8
#     LEFT_WRIST, RIGHT_WRIST = 9, 10
#     LEFT_HIP, RIGHT_HIP = 11, 12
#     LEFT_KNEE, RIGHT_KNEE = 13, 14
#     LEFT_ANKLE, RIGHT_ANKLE = 15, 16
    
#     # Helper to get point if confidence > 0.5
#     def get_point(idx):
#         if keypoints_conf[idx] > 0.5:
#             return keypoints_xy[idx]
#         return None
    
#     # Extract points
#     l_hip, r_hip = get_point(LEFT_HIP), get_point(RIGHT_HIP)
#     l_knee, r_knee = get_point(LEFT_KNEE), get_point(RIGHT_KNEE)
#     l_ankle, r_ankle = get_point(LEFT_ANKLE), get_point(RIGHT_ANKLE)
#     l_wrist, r_wrist = get_point(LEFT_WRIST), get_point(RIGHT_WRIST)
#     l_shoulder, r_shoulder = get_point(LEFT_SHOULDER), get_point(RIGHT_SHOULDER)
#     nose = get_point(NOSE)

#     # Calculate averages (safe calculation)
#     def avg_y(p1, p2):
#         if p1 is not None and p2 is not None:
#             return (p1[1] + p2[1]) / 2
#         return p1[1] if p1 is not None else (p2[1] if p2 is not None else None)

#     avg_hip_y = avg_y(l_hip, r_hip)
#     avg_knee_y = avg_y(l_knee, r_knee)
#     avg_ankle_y = avg_y(l_ankle, r_ankle)
    
#     # Base Confidence
#     visible_points = [p for p in [l_hip, r_hip, l_knee, r_knee, l_ankle, r_ankle] if p is not None]
#     if len(visible_points) < 3:
#         return "Unknown Pose", 0.0
#     confidence = np.mean([keypoints_conf[i] for i in range(17) if keypoints_conf[i] > 0.5])

#     # --- PRIORITY 1: Dynamic Actions (Running/Walking) ---
#     # Check this BEFORE standing. 
#     # Logic: Large vertical separation between knees (lifting leg) OR large horizontal separation (stride)
#     if l_knee is not None and r_knee is not None:
#         knee_dist_y = abs(l_knee[1] - r_knee[1])
#         knee_dist_x = abs(l_knee[0] - r_knee[0])
        
#         # If knees are far apart vertically (high stepping) or horizontally (wide stride)
#         if knee_dist_y > 0.08 * img_height or knee_dist_x > 0.20 * img_width:
#             # Distinguish Run vs Walk based on severity of split
#             if knee_dist_y > 0.12 * img_height or knee_dist_x > 0.35 * img_width:
#                 return "Running", confidence * 0.95
#             return "Walking", confidence * 0.90


#     # --- PRIORITY 3: Jumping ---
#     # Logic: Ankles are significantly higher than bottom of image (or relative to body size)
#     # This is tricky without a ground reference, but we can check if legs are tucked up
#     if avg_ankle_y is not None and avg_knee_y is not None:
#         if avg_ankle_y < avg_knee_y: # Feet above knees (tucked jump)
#             return "Jumping", confidence * 0.9

#     # --- PRIORITY 4: Sitting ---
#     if avg_hip_y is not None and avg_knee_y is not None:
#         # Thighs are roughly horizontal (knees and hips at similar Y)
#         if abs(avg_hip_y - avg_knee_y) < 0.1 * img_height:
#              return "Sitting", confidence * 0.92

#     # --- PRIORITY 5: Waving (Upper Body) ---
#     if l_wrist is not None and l_shoulder is not None:
#         if l_wrist[1] < l_shoulder[1]: # Wrist above shoulder
#             return "Waving", confidence * 0.9
#     if r_wrist is not None and r_shoulder is not None:
#         if r_wrist[1] < r_shoulder[1]:
#             return "Waving", confidence * 0.9

#     # --- PRIORITY 7: Standing (Default Upright) ---
#     # Only if none of the above matched
#     if avg_hip_y is not None and avg_knee_y is not None and avg_ankle_y is not None:
#         if avg_hip_y < avg_knee_y < avg_ankle_y:
#             return "Standing", confidence * 0.90

#     return "Unknown Pose", confidence * 0.5

# @app.post("/predict", response_model=PredictionOut)
# async def predict(file: UploadFile = File(...), db: Session = Depends(get_db)):
#     try:
#         contents = await file.read()
#         image = Image.open(io.BytesIO(contents))
#         img_width, img_height = image.size
        
#         # Run YOLO inference
#         results = model(image, conf=0.25)
        
#         # Extract keypoints (first person only)
#         if len(results) == 0 or len(results[0].keypoints) == 0:
#             raise ValueError("No person detected")
        
#         # --- NEW CODE START ---
#         # 1. Get the total number of people detected
#         total_persons = len(results[0].keypoints)
        
#         keypoints = results[0].keypoints[0]
#         # --- NEW CODE END ---
        
#         keypoints = results[0].keypoints[0]
        
#         # --- FIXED SECTION START ---
#         # accessing .xy usually returns shape (1, 17, 2), so we need [0] to get (17, 2)
#         keypoints_xy = keypoints.xy.numpy()[0] 
        
#         # conf is usually (1, 17), flattening it works, but [0] is cleaner
#         keypoints_conf = keypoints.conf.numpy()[0] 
#         # --- FIXED SECTION END ---

#         # Classify activity
#         activity, confidence = classify_activity(keypoints_xy, keypoints_conf, img_width, img_height)
#         # Save image
#         temp_dir = tempfile.gettempdir()
#         filename = f"{uuid.uuid4()}.jpg"
#         filepath = os.path.join(temp_dir, filename)
        
#         with open(filepath, "wb") as f:
#             f.write(contents)
        
#         # Save to DB
#         pred_in = PredictionCreate(input_data=filename, prediction=activity, confidence=confidence)
#         pred = create_prediction(db=db, prediction=pred_in)
        
#         # Normalize keypoints for frontend (0-1)
#         norm_keypoints = [[float(x) / img_width, float(y) / img_height] for x, y in keypoints_xy]
        
#         print(f"✅ Prediction: {activity} ({confidence*100:.1f}%)")
        
#         return PredictionOut(
#             id=pred.id,
#             input_data=pred.input_data,
#             prediction=pred.prediction,
#             confidence=pred.confidence,
#             created_at=pred.created_at,
#             keypoints=norm_keypoints,
#             person_count=total_persons
#         )
        
#     except Exception as e:
#         import traceback
#         print("ERROR in /predict:")
#         print(traceback.format_exc())
#         raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")

# @app.get("/history", response_model=List[PredictionHistory])
# def get_history(limit: int = 50, db: Session = Depends(get_db)):
#     """Get prediction history"""
#     predictions = get_predictions(db)
#     return predictions[-limit:]

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Relative imports
from .database import engine
from .models import Base
from .routers import pose, history # Import your new routers

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

