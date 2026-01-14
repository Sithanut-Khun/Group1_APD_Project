from sqlalchemy.orm import Session
from .models import Prediction
from .schemas import PredictionCreate

def create_prediction(db: Session, prediction: PredictionCreate):
    db_pred = Prediction(**prediction.dict())
    db.add(db_pred)
    db.commit()
    db.refresh(db_pred)
    return db_pred

def get_predictions(db: Session):
    return db.query(Prediction).all()