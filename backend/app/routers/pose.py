import uuid
import io
import os
import tempfile
import numpy as np
from pathlib import Path
from PIL import Image
from typing import List

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from ultralytics import YOLO

# Import from parent directory (..)
from ..database import get_db
from ..schemas import PredictionCreate, PredictionOut
from ..crud import create_prediction

router = APIRouter()

# --- MODEL LOADING LOGIC ---
print("Loading YOLOv8 model...")
MODELS_DIR = Path(__file__).parent.parent / "models"  # points to backend/app/models/
MODEL_PATH = MODELS_DIR / "yolov8n-pose.pt"

MODELS_DIR.mkdir(exist_ok=True)

if MODEL_PATH.exists():
    model = YOLO(str(MODEL_PATH))
    print("✓ Model loaded from local file")
else:
    print("Model not found locally, downloading...")
    model = YOLO('yolov8n-pose.pt')
    model.save(str(MODEL_PATH))
    print(f"✓ Model downloaded and saved to: {MODEL_PATH}")

# --- HELPER FUNCTION ---
def classify_activity(keypoints_xy, keypoints_conf, img_width, img_height):
    """
    Classifies the activity based on keypoints.
    """
    # COCO keypoint indices
    NOSE = 0
    LEFT_SHOULDER, RIGHT_SHOULDER = 5, 6
    LEFT_KNEE, RIGHT_KNEE = 13, 14
    LEFT_ANKLE, RIGHT_ANKLE = 15, 16
    LEFT_WRIST, RIGHT_WRIST = 9, 10
    LEFT_HIP, RIGHT_HIP = 11, 12

    # Helper to get point if confidence > 0.5
    def get_point(idx):
        if keypoints_conf[idx] > 0.5:
            return keypoints_xy[idx]
        return None
    
    # Extract points needed for logic
    l_knee, r_knee = get_point(LEFT_KNEE), get_point(RIGHT_KNEE)
    l_ankle, r_ankle = get_point(LEFT_ANKLE), get_point(RIGHT_ANKLE)
    l_wrist, r_wrist = get_point(LEFT_WRIST), get_point(RIGHT_WRIST)
    l_shoulder, r_shoulder = get_point(LEFT_SHOULDER), get_point(RIGHT_SHOULDER)
    l_hip, r_hip = get_point(LEFT_HIP), get_point(RIGHT_HIP)

    def avg_y(p1, p2):
        if p1 is not None and p2 is not None:
            return (p1[1] + p2[1]) / 2
        return p1[1] if p1 is not None else (p2[1] if p2 is not None else None)

    avg_hip_y = avg_y(l_hip, r_hip)
    avg_knee_y = avg_y(l_knee, r_knee)
    avg_ankle_y = avg_y(l_ankle, r_ankle)
    
    # Calculate confidence
    visible_points = [p for p in [l_hip, r_hip, l_knee, r_knee, l_ankle, r_ankle] if p is not None]
    if len(visible_points) < 3:
        return "Unknown Pose", 0.0
    confidence = np.mean([keypoints_conf[i] for i in range(17) if keypoints_conf[i] > 0.5])

    # 1. Running/Walking
    if l_knee is not None and r_knee is not None:
        knee_dist_y = abs(l_knee[1] - r_knee[1])
        knee_dist_x = abs(l_knee[0] - r_knee[0])
        if knee_dist_y > 0.08 * img_height or knee_dist_x > 0.20 * img_width:
            if knee_dist_y > 0.12 * img_height or knee_dist_x > 0.35 * img_width:
                return "Running", confidence * 0.95
            return "Walking", confidence * 0.90

    # 2. Jumping
    if avg_ankle_y is not None and avg_knee_y is not None:
        if avg_ankle_y < avg_knee_y: 
            return "Jumping", confidence * 0.9

    # 3. Sitting
    if avg_hip_y is not None and avg_knee_y is not None:
        if abs(avg_hip_y - avg_knee_y) < 0.1 * img_height:
             return "Sitting", confidence * 0.92

    # 4. Waving
    if l_wrist is not None and l_shoulder is not None:
        if l_wrist[1] < l_shoulder[1]:
            return "Waving", confidence * 0.9
    if r_wrist is not None and r_shoulder is not None:
        if r_wrist[1] < r_shoulder[1]:
            return "Waving", confidence * 0.9

    # 5. Standing
    if avg_hip_y is not None and avg_knee_y is not None and avg_ankle_y is not None:
        if avg_hip_y < avg_knee_y < avg_ankle_y:
            return "Standing", confidence * 0.90

    return "Unknown Pose", confidence * 0.5

# --- API ENDPOINT ---
@router.post("/predict", response_model=PredictionOut)
async def predict(file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents))
        img_width, img_height = image.size
        
        # Run YOLO inference
        results = model(image, conf=0.25)
        
        if len(results) == 0 or len(results[0].keypoints) == 0:
            raise ValueError("No person detected")
        
        total_persons = len(results[0].keypoints)
        keypoints = results[0].keypoints[0]
        
        # Numpy conversions
        keypoints_xy = keypoints.xy.numpy()[0] 
        keypoints_conf = keypoints.conf.numpy()[0] 

        # Classify
        activity, confidence = classify_activity(keypoints_xy, keypoints_conf, img_width, img_height)
        
        # Save temp image
        temp_dir = tempfile.gettempdir()
        filename = f"{uuid.uuid4()}.jpg"
        filepath = os.path.join(temp_dir, filename)
        with open(filepath, "wb") as f:
            f.write(contents)
        
        # Save to DB
        pred_in = PredictionCreate(input_data=filename, prediction=activity, confidence=confidence)
        pred = create_prediction(db=db, prediction=pred_in)
        
        # Normalize keypoints
        norm_keypoints = [[float(x) / img_width, float(y) / img_height] for x, y in keypoints_xy]
        
        print(f"✅ Prediction: {activity} ({confidence*100:.1f}%)")
        
        return PredictionOut(
            id=pred.id,
            input_data=pred.input_data,
            prediction=pred.prediction,
            confidence=pred.confidence,
            created_at=pred.created_at,
            keypoints=norm_keypoints,
            person_count=total_persons
        )
        
    except Exception as e:
        import traceback
        print("ERROR in /predict:")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")