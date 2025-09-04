from sqlalchemy.orm import Session
from . import crud, flights, schemas
from typing import Optional, List

# This is a simple lookup. A real app would use a dedicated airport database.
AIRPORT_TO_COUNTRY_MAP = {
    "BKK": "THA",  # Bangkok -> Thailand
    "SIN": "SGP",  # Singapore
    "KUL": "MYS",  # Kuala Lumpur
    "HAN": "VNM",  # Hanoi, Vietnam
    "SGN": "VNM",  # Ho Chi Minh City, Vietnam
    # Add more mappings as you add countries to your DB
}

async def create_trip_plan(db: Session, origin_airport: str, dest_airport: str) -> schemas.TripPlan:
    # 1. Map destination airport to country code
    dest_country_code = AIRPORT_TO_COUNTRY_MAP.get(dest_airport.upper())

    # 2. Get visa information from our internal database
    visa_info = None
    if dest_country_code:
        visa_info = crud.get_country_by_code(db, country_code=dest_country_code)

    # 3. Get flight options from the external API
    flight_options = await flights.search_flights_on_route(
        origin=origin_airport, 
        destination=dest_airport
    )

    # 4. Combine into a single response object
    trip_plan = schemas.TripPlan(
        visa_information=visa_info,
        flight_options=flight_options
    )

    return trip_plan

