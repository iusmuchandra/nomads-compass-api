from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from . import models, schemas, crud, flights, planner
from .database import engine, get_db

models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Nomad's Compass API",
    description="The core engine for the world's smartest travel agent.",
    version="0.2.0" # Version bump for new features
)

# === Country CRUD Endpoints ===
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
        raise HTTPException(status_code=404, detail="Country data not found")
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

# === Flight Integration Endpoint ===
@app.get("/flights/{airline_code}", response_model=List[schemas.FlightData])
async def get_flights_for_airline(airline_code: str):
    flight_results = await flights.search_flights_by_airline(airline_code=airline_code)
    if not flight_results:
        raise HTTPException(status_code=404, detail="No flights found for this airline.")
    return flight_results

# === Trip Planner Endpoint ===
@app.get("/plan-trip/", response_model=schemas.TripPlan)
async def get_trip_plan(origin: str, destination: str, db: Session = Depends(get_db)):
    """
    Generates a trip plan including visa info and flight options.
    e.g., origin=BOM, destination=BKK
    """
    if not origin or not destination:
        raise HTTPException(status_code=400, detail="Origin and destination are required.")

    trip_plan = await planner.create_trip_plan(
        db=db, 
        origin_airport=origin, 
        dest_airport=destination
    )
    
    if not trip_plan.visa_information and not trip_plan.flight_options:
        raise HTTPException(status_code=404, detail="Could not find any visa or flight information for this route.")
        
    return trip_plan