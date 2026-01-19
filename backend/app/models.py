from sqlalchemy import Column, Integer, String, Float, DateTime
from datetime import datetime
from .database import Base

class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True)
    input_data = Column(String)
    original_filename = Column(String)
    prediction = Column(String)
    confidence = Column(Float)
    person_count = Column(Integer, default=0)
    fps = Column(Float, default=0.0)
    latency = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)