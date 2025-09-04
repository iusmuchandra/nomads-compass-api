import asyncio
import os
import httpx
from . import schemas
from typing import List

async def search_flights_by_airline(airline_code: str) -> List[schemas.FlightData]:
    """
    Searches for flights from a specific airline using the external Flight Data API.
    """
    api_key = os.getenv("AERODATASPHERE_API_KEY")
    if not api_key:
        print("CRITICAL ERROR: AERODATASPHERE_API_KEY not found in .env file.")
        return []

    # These values are taken directly from the RapidAPI documentation for the "Flight Data" API
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
    # In a real-world app, this list would be dynamic or more extensive.
    major_airlines = ["AI", "6E", "SQ", "EK"] # Air India, IndiGo, Singapore, Emirates
    
    # Create a list of concurrent tasks
    tasks = [search_flights_by_airline(code) for code in major_airlines]
    
    # Run all API calls concurrently for speed
    results_per_airline = await asyncio.gather(*tasks)
    
    all_flights = []
    # Flatten the list of lists into a single list
    for airline_flights in results_per_airline:
        all_flights.extend(airline_flights)
        
    # Filter the combined list to match the user's requested route
    route_flights = [
        flight for flight in all_flights
        if flight.departure and flight.arrival and 
           flight.departure.upper() == origin.upper() and 
           flight.arrival.upper() == destination.upper()
    ]
    
    return route_flights