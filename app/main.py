# In app/main.py
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from . import models, schemas
from .database import engine, get_db

# This line creates the database tables if they don't exist
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Nomad's Compass API",
    description="The core engine for the world's smartest travel agent.",
    version="0.1.0"
)

# A simple function to get data from the DB
def get_country_by_code(db: Session, country_code: str):
    return db.query(models.Country).filter(models.Country.code == country_code.upper()).first()

# Updated API endpoint
@app.get("/visa/{country_code}", response_model=schemas.Country)
def get_visa_info(country_code: str, db: Session = Depends(get_db)):
    """
    Retrieves visa information for an Indian passport holder
    for a given destination country code (e.g., 'THA' for Thailand).
    """
    db_country = get_country_by_code(db, country_code=country_code)
    if db_country is None:
        raise HTTPException(status_code=404, detail="Country data not found")
    return db_country