import asyncio
from sqlalchemy.orm import Session
from . import crud, flights, schemas, hotels, models, sponsorship
from typing import List, Optional

# This is a simple lookup. A real app would use a dedicated airport database.
AIRPORT_TO_COUNTRY_MAP = {
    "BKK": "THA",  # Bangkok -> Thailand
    "SIN": "SGP",  # Singapore
    "KUL": "MYS",  # Kuala Lumpur
    "HAN": "VNM",  # Hanoi, Vietnam
    "SGN": "VNM",  # Ho Chi Minh City, Vietnam
}

async def create_trip_plan(db: Session, origin_airport: str, dest_airport: str) -> schemas.TripPlan:
    dest_country_code = AIRPORT_TO_COUNTRY_MAP.get(dest_airport.upper())

    # Create concurrent tasks for all network and DB calls
    visa_task = asyncio.to_thread(crud.get_country_by_code, db, dest_country_code) if dest_country_code else asyncio.sleep(0, result=None)
    flight_task = flights.search_flights_on_route(origin=origin_airport, destination=dest_airport)
    hotel_task = hotels.search_hotels_by_destination(destination_airport_code=dest_airport)
    
    # Run all tasks in parallel
    results = await asyncio.gather(visa_task, flight_task, hotel_task)
    
    visa_info, flight_options, hotel_options = results

    # Combine into a single response object
    trip_plan = schemas.TripPlan(
        visa_information=visa_info,
        flight_options=flight_options,
        hotel_options=hotel_options
    )

    return trip_plan

async def create_full_itinerary_plan(db: Session, itinerary: models.Itinerary, user: models.User) -> schemas.FullItineraryPlan:
    # Create a list of tasks, one for each leg of the journey
    leg_plan_tasks = [
        create_trip_plan(db, leg.origin_airport, leg.destination_airport)
        for leg in itinerary.legs
    ]
    
    # Get sponsorship offers (this is a synchronous call, so no await needed)
    sponsorship_deals = sponsorship.get_sponsorship_offers(user=user, itinerary=itinerary)
    
    trip_plan_results = await asyncio.gather(*leg_plan_tasks)
    
    # Combine the leg details with their corresponding plans
    leg_plans = [
        schemas.LegPlan(leg_details=leg, trip_plan=plan)
        for leg, plan in zip(itinerary.legs, trip_plan_results)
    ]
    
    return schemas.FullItineraryPlan(
        itinerary_details=itinerary,
        leg_plans=leg_plans,
        sponsorship_offers=sponsorship_deals
    )
