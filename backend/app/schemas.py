from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional

class PredictionBase(BaseModel):
    input_data: str
    prediction: str
    confidence: float

class PredictionCreate(PredictionBase):
    person_count: int = 0
    fps: float = 0.0
    latency: float = 0.0
    original_filename: str 
    
class PredictionOut(PredictionBase):
    id: int
    created_at: datetime
    person_count: int
    keypoints: List[List[float]]

    class Config:
        from_attributes = True

class PredictionHistory(BaseModel):
    id: int
    input_data: str
    original_filename: str
    prediction: str
    confidence: float
    person_count: int = 0
    fps: float = 0.0
    latency: float = 0.0
    created_at: datetime

    class Config:
        from_attributes = True