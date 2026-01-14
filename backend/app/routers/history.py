from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

# Import from parent directory
from ..database import get_db
from ..schemas import PredictionHistory
from ..crud import get_predictions

router = APIRouter()

@router.get("/history", response_model=List[PredictionHistory])
def get_history(limit: int = 50, db: Session = Depends(get_db)):
    """Get prediction history"""
    predictions = get_predictions(db)
    # Return last 'limit' items
    return predictions[-limit:]