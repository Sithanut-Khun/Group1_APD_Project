import uuid
import io
import os
import tempfile
import numpy as np
import json
import time
from pathlib import Path
from PIL import Image
from typing import List
import cv2
import mediapipe as mp

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import PredictionCreate, PredictionOut
from ..crud import create_prediction

router = APIRouter()

# --- MediaPipe MODEL LOADING ---
print("Loading MediaPipe Pose model...")
mp_pose = mp.solutions.pose
pose = mp_pose.Pose(
    static_image_mode=True,
    model_complexity=1,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)
print("✓ MediaPipe Pose model loaded successfully")

# --- ACTIVITY CLASSIFICATION FUNCTION ---
def classify_activity(landmarks, img_width, img_height):
    """
    Classifies the activity based on MediaPipe landmarks.
    MediaPipe provides 33 pose landmarks.
    """
    if not landmarks:
        return "Unknown Pose", 0.0
    
    def get_landmark(idx):
        if idx < len(landmarks):
            return landmarks[idx]
        return None
    
    # MediaPipe Landmark Indices
    NOSE = 0
    LEFT_SHOULDER = 11
    RIGHT_SHOULDER = 12
    LEFT_ELBOW = 13
    RIGHT_ELBOW = 14
    LEFT_WRIST = 15
    RIGHT_WRIST = 16
    LEFT_HIP = 23
    RIGHT_HIP = 24
    LEFT_KNEE = 25
    RIGHT_KNEE = 26
    LEFT_ANKLE = 27
    RIGHT_ANKLE = 28
    
    nose = get_landmark(NOSE)
    left_shoulder = get_landmark(LEFT_SHOULDER)
    right_shoulder = get_landmark(RIGHT_SHOULDER)
    left_hip = get_landmark(LEFT_HIP)
    right_hip = get_landmark(RIGHT_HIP)
    left_knee = get_landmark(LEFT_KNEE)
    right_knee = get_landmark(RIGHT_KNEE)
    left_ankle = get_landmark(LEFT_ANKLE)
    right_ankle = get_landmark(RIGHT_ANKLE)
    left_wrist = get_landmark(LEFT_WRIST)
    right_wrist = get_landmark(RIGHT_WRIST)
    left_elbow = get_landmark(LEFT_ELBOW)
    right_elbow = get_landmark(RIGHT_ELBOW)
    
    avg_confidence = np.mean([lm.visibility for lm in landmarks if lm.visibility > 0.5])
    
    def avg_y(lm1, lm2):
        if lm1 and lm2:
            return (lm1.y + lm2.y) / 2
        return lm1.y if lm1 else (lm2.y if lm2 else None)
    
    avg_hip_y = avg_y(left_hip, right_hip)
    avg_knee_y = avg_y(left_knee, right_knee)
    avg_ankle_y = avg_y(left_ankle, right_ankle)
    avg_shoulder_y = avg_y(left_shoulder, right_shoulder)
    avg_wrist_y = avg_y(left_wrist, right_wrist)
    
    # Activity classification logic
    if left_knee and right_knee:
        knee_dist_y = abs(left_knee.y - right_knee.y)
        knee_dist_x = abs(left_knee.x - right_knee.x)
        
        if knee_dist_y > 0.08 or knee_dist_x > 0.20:
            if knee_dist_y > 0.12 or knee_dist_x > 0.35:
                return "Running", avg_confidence * 0.95
            return "Walking", avg_confidence * 0.90
    
    if avg_ankle_y and avg_knee_y and avg_ankle_y < avg_knee_y - 0.05:
        return "Jumping", avg_confidence * 0.92
    
    if avg_hip_y and avg_knee_y and abs(avg_hip_y - avg_knee_y) < 0.12:
        return "Sitting", avg_confidence * 0.93
    
    if left_wrist and left_shoulder and left_wrist.y < left_shoulder.y - 0.1:
        return "Waving", avg_confidence * 0.91
    if right_wrist and right_shoulder and right_wrist.y < right_shoulder.y - 0.1:
        return "Waving", avg_confidence * 0.91
    
    if (left_wrist and left_shoulder and left_wrist.y < left_shoulder.y and
        right_wrist and right_shoulder and right_wrist.y < right_shoulder.y):
        return "Raising Arms", avg_confidence * 0.89
    
    if avg_hip_y and avg_knee_y and avg_ankle_y:
        hip_knee_dist = abs(avg_hip_y - avg_knee_y)
        knee_ankle_dist = abs(avg_knee_y - avg_ankle_y)
        if hip_knee_dist < 0.18 and knee_ankle_dist < 0.18:
            return "Squatting", avg_confidence * 0.88
    
    if avg_shoulder_y and avg_hip_y and avg_shoulder_y > avg_hip_y + 0.15:
        return "Bending Over", avg_confidence * 0.87
    
    if avg_hip_y and avg_knee_y and avg_ankle_y:
        if avg_hip_y < avg_knee_y < avg_ankle_y:
            if avg_shoulder_y and avg_shoulder_y < avg_hip_y:
                return "Standing", avg_confidence * 0.90
    
    return "Unknown Pose", avg_confidence * 0.5

# --- API ENDPOINT ---
@router.post("/predict", response_model=PredictionOut)
async def predict(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Predict human activity from uploaded image using MediaPipe.
    Now includes FPS and latency tracking.
    """
    start_time = time.time()
    
    try:
        # --- NEW: Capture original filename ---
        original_filename = file.filename 
        
        # Read uploaded image
        contents = await file.read()
        image = Image.open(io.BytesIO(contents))
        img_width, img_height = image.size
        
        # Convert PIL Image to OpenCV format
        image_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        
        # Process image with MediaPipe
        inference_start = time.time()
        results = pose.process(cv2.cvtColor(image_cv, cv2.COLOR_BGR2RGB))
        inference_time = (time.time() - inference_start) * 1000  # Convert to ms
        
        # Check if person detected
        if not results.pose_landmarks:
            raise ValueError("No person detected in image")
        
        landmarks = results.pose_landmarks.landmark
        
        # Classify the activity
        activity, confidence = classify_activity(landmarks, img_width, img_height)
        
        # Save temporary image file
        temp_dir = tempfile.gettempdir()
        filename = f"{uuid.uuid4()}.jpg" # This is our internal hashed name
        filepath = os.path.join(temp_dir, filename)
        with open(filepath, "wb") as f:
            f.write(contents)
        
        # Calculate metrics
        total_latency = (time.time() - start_time) * 1000  # ms
        fps = 1000 / total_latency if total_latency > 0 else 0
        
        # Prepare keypoints as JSON string
        norm_keypoints = [[float(lm.x), float(lm.y)] for lm in landmarks]
        keypoints_json = json.dumps(norm_keypoints)
        
        # Save prediction to database with extended fields
        pred_in = PredictionCreate(
            input_data=filename,          
            original_filename=original_filename, 
            prediction=activity,
            confidence=confidence,
            person_count=1,
            fps=round(fps, 2),
            latency=round(total_latency, 2),
            keypoints=keypoints_json
        )
        pred = create_prediction(db=db, prediction=pred_in)
        
        print(f"✅ Prediction: {activity} | Original: {original_filename} | FPS: {fps:.1f}")
        
        # Return prediction result
        return PredictionOut(
            id=pred.id,
            input_data=pred.input_data,
            original_filename=pred.original_filename, # NEW
            prediction=pred.prediction,
            confidence=pred.confidence,
            person_count=pred.person_count,
            fps=pred.fps,
            latency=pred.latency,
            created_at=pred.created_at,
            keypoints=norm_keypoints
        )
        
    except Exception as e:
        import traceback
        print("❌ ERROR in /predict endpoint:")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=500, 
            detail=f"Prediction error: {str(e)}"
        )