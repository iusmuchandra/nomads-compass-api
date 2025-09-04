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

    # We initialize response outside the try block to use it in the except block
    response = None 
    async with httpx.AsyncClient() as client:
        try:
            print(f"--- Calling external API for airline: {airline_code} ---")
            response = await client.get(url, headers=headers, params=params)
            
            # This will raise an exception if the status is 4xx or 5xx
            response.raise_for_status()
            
            flight_results = response.json()
            
            if not flight_results:
                print(f"--- API call successful, but no flight data returned for {airline_code}. ---")
                return []
            
            # The core validation step: does the response match our schema?
            validated_flights = [schemas.FlightData(**flight) for flight in flight_results]
            print(f"--- Successfully parsed {len(validated_flights)} flights. ---")
            return validated_flights

        except httpx.HTTPStatusError as e:
            # This catches errors like 401 Unauthorized, 403 Forbidden, etc.
            print(f"--- HTTP error occurred: {e.response.status_code} ---")
            print(f"Response Body: {e.response.text}")
            return []
        except Exception as e:
            # This catches Pydantic ValidationErrors and other unexpected issues
            print("--- RAW RESPONSE THAT FAILED PARSING ---")
            # We check if response is not None before trying to access its attributes
            if response:
                print(response.text)
            else:
                print("No response object was received.")
            print("------------------------------------------")
            print(f"An unexpected error occurred during parsing: {e}")
            return []
