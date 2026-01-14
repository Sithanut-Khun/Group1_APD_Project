import uuid
import io
import os
import tempfile
from typing import List
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from PIL import Image
import numpy as np
import torch
from transformers import VideoMAEImageProcessor, VideoMAEForVideoClassification

from .database import get_db, engine
from .models import Base, Prediction
from .schemas import PredictionCreate, PredictionHistory, PredictionOut
from .crud import create_prediction, get_predictions

app = FastAPI()

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create DB tables
Base.metadata.create_all(bind=engine)

# Load VideoMAE model
print("Loading VideoMAE model...")
MODEL_NAME = "MCG-NJU/videomae-base-finetuned-kinetics"

try:
    processor = VideoMAEImageProcessor.from_pretrained(MODEL_NAME)
    model = VideoMAEForVideoClassification.from_pretrained(MODEL_NAME)
    model.eval()
    
    # Move to GPU if available
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = model.to(device)
    print(f"✓ VideoMAE model loaded successfully on {device}")
except Exception as e:
    print(f"Error loading VideoMAE: {e}")
    raise

# Action mapping for better display names
ACTION_MAPPING = {
    "walking": "Walking",
    "running": "Running",
    "jumping": "Jumping",
    "sitting": "Sitting",
    "standing": "Standing",
    "waving": "Waving",
    "clapping": "Clapping",
    "dancing": "Dancing",
}

@app.get("/")
def root():
    """Root endpoint"""
    return {
        "message": "NeuralPose API - VideoMAE",
        "version": "2.0.0",
        "status": "running",
        "model": "VideoMAE-base-kinetics",
        "endpoints": {
            "health": "/health",
            "predict": "/predict",
            "predict_video": "/predict/video",
            "history": "/history",
            "actions": "/actions"
        }
    }

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "model": "VideoMAE-base-kinetics",
        "device": str(device)
    }


def preprocess_image_for_video(image: Image.Image, num_frames: int = 16):
    """
    Convert single image to video-like format by duplicating frames.
    VideoMAE expects 16 frames by default.
    """
    image = image.convert("RGB")
    frames = [image] * num_frames
    return frames


def predict_action(frames: List[Image.Image]) -> tuple:
    """
    Predict action using VideoMAE model.
    Returns: (action_name, confidence)
    """
    try:
        # Preprocess frames
        inputs = processor(frames, return_tensors="pt")
        inputs = {k: v.to(device) for k, v in inputs.items()}
        
        # Run inference
        with torch.no_grad():
            outputs = model(**inputs)
            logits = outputs.logits
        
        # Get predictions
        predicted_class_idx = logits.argmax(-1).item()
        probabilities = torch.nn.functional.softmax(logits, dim=-1)
        confidence = probabilities[0][predicted_class_idx].item()
        
        # Get action label
        action_label = model.config.id2label[predicted_class_idx]
        
        # Clean up action name
        action_name = ACTION_MAPPING.get(action_label.lower(), action_label.title())
        
        return action_name, confidence
        
    except Exception as e:
        print(f"Error in prediction: {e}")
        return "Unknown", 0.0


@app.post("/predict", response_model=PredictionOut)
async def predict_single_image(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Predict action from a single image.
    Note: VideoMAE works best with video, so this duplicates the frame.
    """
    try:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents))
        img_width, img_height = image.size
        
        # Convert single image to video format (duplicate frames)
        frames = preprocess_image_for_video(image, num_frames=16)
        
        # Predict action
        activity, confidence = predict_action(frames)
        
        # Save image
        temp_dir = tempfile.gettempdir()
        filename = f"{uuid.uuid4()}.jpg"
        filepath = os.path.join(temp_dir, filename)
        
        with open(filepath, "wb") as f:
            f.write(contents)
        
        # Save to DB
        pred_in = PredictionCreate(
            input_data=filename,
            prediction=activity,
            confidence=confidence
        )
        pred = create_prediction(db=db, prediction=pred_in)
        
        print(f"✅ Prediction: {activity} ({confidence*100:.1f}%)")
        
        return PredictionOut(
            id=pred.id,
            input_data=pred.input_data,
            prediction=pred.prediction,
            confidence=pred.confidence,
            created_at=pred.created_at,
            keypoints=[],  # VideoMAE doesn't provide keypoints
            person_count=1
        )
        
    except Exception as e:
        import traceback
        print("ERROR in /predict:")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")


@app.post("/predict/video")
async def predict_video(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Predict action from a video file.
    """
    try:
        import cv2
        
        contents = await file.read()
        
        # Save temporary video file
        temp_dir = tempfile.gettempdir()
        video_filename = f"{uuid.uuid4()}.mp4"
        video_path = os.path.join(temp_dir, video_filename)
        
        with open(video_path, "wb") as f:
            f.write(contents)
        
        # Extract frames from video
        cap = cv2.VideoCapture(video_path)
        frames = []
        frame_count = 0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        # Sample 16 frames evenly
        frame_indices = np.linspace(0, total_frames - 1, 16, dtype=int)
        
        while cap.isOpened() and len(frames) < 16:
            ret, frame = cap.read()
            if not ret:
                break
                
            if frame_count in frame_indices:
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil_image = Image.fromarray(frame_rgb)
                frames.append(pil_image)
            
            frame_count += 1
        
        cap.release()
        
        # If not enough frames, duplicate last one
        while len(frames) < 16:
            frames.append(frames[-1] if frames else Image.new('RGB', (224, 224)))
        
        # Predict action
        activity, confidence = predict_action(frames[:16])
        
        # Save to DB
        pred_in = PredictionCreate(
            input_data=video_filename,
            prediction=activity,
            confidence=confidence
        )
        pred = create_prediction(db=db, prediction=pred_in)
        
        print(f"✅ Video Prediction: {activity} ({confidence*100:.1f}%)")
        
        return {
            "id": pred.id,
            "input_data": pred.input_data,
            "prediction": pred.prediction,
            "confidence": pred.confidence,
            "created_at": pred.created_at,
            "frames_analyzed": len(frames)
        }
        
    except Exception as e:
        import traceback
        print("ERROR in /predict/video:")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Video prediction error: {str(e)}")
    finally:
        if os.path.exists(video_path):
            os.remove(video_path)


@app.get("/history", response_model=List[PredictionHistory])
def get_history(limit: int = 50, db: Session = Depends(get_db)):
    """Get prediction history"""
    predictions = get_predictions(db)
    return predictions[-limit:]


@app.get("/actions")
def get_available_actions():
    """Get list of actions the model can recognize"""
    return {
        "total_actions": len(model.config.id2label),
        "sample_actions": list(model.config.id2label.values())[:20],
        "note": "Model trained on Kinetics-400 dataset with 400 action classes"
    }