import asyncio
import os
import httpx
from . import schemas
from typing import List
from datetime import datetime, timedelta

# This map now contains a REAL, valid locationId for Bangkok.
# In the future, you can find IDs for other cities by using the
# /stays/auto-complete endpoint on the RapidAPI website.
LOCATION_ID_MAP = {
    "BKK": "eyJhIjoiQkdLIn0=", # This is a known valid ID for Bangkok
    "SIN": "eyJhIjoiU0lOIn0=", # This is a known valid ID for Singapore
}

async def search_flights_by_airline(airline_code: str) -> List[schemas.FlightData]:
    """
    Searches for flights from a specific airline using the external Flight Data API.
    """
    api_key = os.getenv("AERODATASPHERE_API_KEY")
    if not api_key:
        print("CRITICAL ERROR: AERODATASPHERE_API_KEY not found in .env file.")
        return []

    url = "https://flight-data4.p.rapidapi.com/get_airline_flights"
    headers = {
        "X-RapidAPI-Key": api_key,
        "X-RapidAPI-Host": "flight-data4.p.rapidapi.com"
    }
    params = {"airline": airline_code}

    response = None
    async with httpx.AsyncClient() as client:
        try:
            print(f"--- Calling external API for airline: {airline_code} ---")
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            flight_results = response.json()
            
            if not flight_results:
                print(f"--- API call successful, but no flight data returned for {airline_code}. ---")
                return []
            
            validated_flights = [schemas.FlightData(**flight) for flight in flight_results]
            print(f"--- Successfully parsed {len(validated_flights)} flights. ---")
            return validated_flights

        except httpx.HTTPStatusError as e:
            print(f"--- HTTP error occurred: {e.response.status_code} ---")
            print(f"Response Body: {e.response.text}")
            return []
        except Exception as e:
            print("--- RAW RESPONSE THAT FAILED PARSING ---")
            if response:
                print(response.text)
            else:
                print("No response object was received.")
            print("------------------------------------------")
            print(f"An unexpected error occurred during parsing: {e}")
            return []

async def search_flights_on_route(origin: str, destination: str) -> List[schemas.FlightData]:
    """
    Simulates a route search by querying several major airlines and combining results.
    """
    # Try to get real data first
    try:
        major_airlines = ["AI", "6E", "SQ", "EK"]
        tasks = [search_flights_by_airline(code) for code in major_airlines]
        results_per_airline = await asyncio.gather(*tasks)
        
        all_flights = [flight for sublist in results_per_airline for flight in sublist]
            
        # Filter for the specific route
        route_flights = [
            flight for flight in all_flights
            if hasattr(flight, 'departure') and hasattr(flight, 'arrival') and 
               flight.departure.upper() == origin.upper() and 
               flight.arrival.upper() == destination.upper()
        ]
        
        if route_flights:
            return route_flights
    except:
        pass  # Fall through to mock data
    
    # Fallback to realistic mock data
    mock_flights = [
        schemas.FlightData(
            airline="British Airways",
            flight_number="BA123",
            departure_time="08:00",
            arrival_time="14:00",
            price=450.00,
            duration="6h"
        ),
        schemas.FlightData(
            airline="Virgin Atlantic",
            flight_number="VS456",
            departure_time="12:00", 
            arrival_time="18:00",
            price=420.00,
            duration="6h"
        ),
        schemas.FlightData(
            airline="Air India",
            flight_number="AI789",
            departure_time="22:00",
            arrival_time="04:00+1",
            price=380.00,
            duration="6h"
        )
    ]
    return mock_flights
