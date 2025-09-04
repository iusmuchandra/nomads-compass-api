# In app/main.py

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

# NOTICE the change in imports
from . import models, schemas, crud
from .database import engine, get_db

# This line creates the database tables if they don't exist
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Nomad's Compass API",
    description="The core engine for the world's smartest travel agent.",
    version="0.1.0"
)

# --- NEW POST ENDPOINT ---
@app.post("/visa/", response_model=schemas.Country)
def create_new_country(country: schemas.CountryCreate, db: Session = Depends(get_db)):
    """
    Creates a new country with its visa requirements.
    Prevents creation if a country with the same code already exists.
    """
    db_country = crud.get_country_by_code(db, country_code=country.code)
    if db_country:
        raise HTTPException(status_code=400, detail="Country with this code already exists")
    return crud.create_country(db=db, country=country)
# -------------------------

# --- UPDATED GET ENDPOINT ---
# It now calls the function from crud.py
@app.get("/visa/{country_code}", response_model=schemas.Country)
def get_visa_info(country_code: str, db: Session = Depends(get_db)):
    """
    Retrieves visa information for an Indian passport holder
    for a given destination country code (e.g., 'THA' for Thailand).
    """
    db_country = crud.get_country_by_code(db, country_code=country_code)
    if db_country is None:
        raise HTTPException(status_code=404, detail="Country data not found")
    return db_country

@app.put("/visa/{country_id}", response_model=schemas.Country)
def update_country_info(country_id: int, country: schemas.CountryUpdate, db: Session = Depends(get_db)):
    """
    Updates the information for a specific country by its ID.
    """
    db_country = crud.update_country(db, country_id=country_id, country_update=country)
    if db_country is None:
        raise HTTPException(status_code=404, detail="Country not found")
    return db_country

# In app/main.py, add this endpoint.

@app.delete("/visa/{country_id}", response_model=dict)
def delete_country_info(country_id: int, db: Session = Depends(get_db)):
    """
    Deletes a country and its requirements by its ID.
    """
    db_country = crud.delete_country(db, country_id=country_id)
    if db_country is None:
        raise HTTPException(status_code=404, detail="Country not found")
    return {"message": f"Country '{db_country.name}' deleted successfully"}