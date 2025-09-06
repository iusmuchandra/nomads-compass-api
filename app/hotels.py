import os
import httpx
from . import schemas
from typing import List
from datetime import datetime, timedelta

LOCATION_ID_MAP = {
    "BKK": "eyJjaXR5X25hbWUiOiJCYW5na29rIiwiY291bnRyeSI6IlRoYWlsYW5kIiwiZGVzdF9pZCI6Ii0zNDE0NDQwIiwiZGVzdF90eXBlIjoiY2l0eSJ9", 
    "SIN": "ey...placeholder_for_singapore",
}

async def search_hotels_by_destination(destination_airport_code: str) -> List[schemas.HotelData]:
    api_key = os.getenv("HOTEL_API_KEY")
    location_id = LOCATION_ID_MAP.get(destination_airport_code.upper())

    if not api_key or not location_id:
        if not api_key:
            print("CRITICAL ERROR: HOTEL_API_KEY not found in .env file.")
        if not location_id:
            print(f"WARN: No locationId found for airport {destination_airport_code}")
        return []

    checkin_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
    checkout_date = (datetime.now() + timedelta(days=35)).strftime('%Y-%m-%d')

    url = "https://booking-com18.p.rapidapi.com/stays/search"
    headers = {
        "X-RapidAPI-Key": api_key,
        "X-RapidAPI-Host": "booking-com18.p.rapidapi.com"
    }
    params = {
        "locationId": location_id,
        "checkinDate": checkin_date,
        "checkoutDate": checkout_date,
        "adults": "2",
        "language": "en-gb",
        "currency": "INR",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            print(f"--- Calling external Hotel API for destination: {destination_airport_code} ---")
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            hotel_results = response.json().get("data", [])
            
            if not hotel_results:
                print(f"--- Hotel API call successful, but no data returned for {destination_airport_code}. ---")
                return []
            
            validated_hotels = [schemas.HotelData(**hotel) for hotel in hotel_results]
            print(f"--- Successfully parsed {len(validated_hotels)} hotels. ---")
            return validated_hotels

        except Exception as e:
            print(f"An error occurred during hotel search: {e}")
            return []