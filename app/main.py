# In app/main.py

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

# --- ENSURE THIS IMPORT LINE IS CORRECT ---
from . import models, schemas, crud, flights
# ----------------------------------------

from .database import engine, get_db

models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Nomad's Compass API",
    description="The core engine for the world's smartest travel agent.",
    version="0.1.0"
)

@app.post("/visa/", response_model=schemas.Country)
def create_new_country(country: schemas.CountryCreate, db: Session = Depends(get_db)):
    db_country = crud.get_country_by_code(db, country_code=country.code)
    if db_country:
        raise HTTPException(status_code=400, detail="Country with this code already exists")
    return crud.create_country(db=db, country=country)

@app.get("/visa/{country_code}", response_model=schemas.Country)
def get_visa_info(country_code: str, db: Session = Depends(get_db)):
    db_country = crud.get_country_by_code(db, country_code=country_code)
    if db_country is None:
        raise HTTPException(status_code=404, detail="Country not found")
    return db_country

@app.put("/visa/{country_id}", response_model=schemas.Country)
def update_country_info(country_id: int, country: schemas.CountryUpdate, db: Session = Depends(get_db)):
    db_country = crud.update_country(db, country_id=country_id, country_update=country)
    if db_country is None:
        raise HTTPException(status_code=404, detail="Country not found")
    return db_country

@app.delete("/visa/{country_id}", response_model=dict)
def delete_country_info(country_id: int, db: Session = Depends(get_db)):
    db_country = crud.delete_country(db, country_id=country_id)
    if db_country is None:
        raise HTTPException(status_code=404, detail="Country not found")
    return {"message": f"Country '{db_country.name}' deleted successfully"}

@app.get("/flights/{airline_code}", response_model=List[schemas.FlightData])
async def get_flights_for_airline(airline_code: str):
    flight_results = await flights.search_flights_by_airline(airline_code=airline_code)
    if not flight_results:
        raise HTTPException(status_code=404, detail="No flights found for this airline.")
    return flight_results