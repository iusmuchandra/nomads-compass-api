import os
import httpx
from . import schemas
from typing import List, Optional
from datetime import datetime, timedelta

LOCATION_ID_MAP = {
    "BKK": "eyJhIjoiQkdLIn0=", # Bangkok
    "SIN": "eyJhIjoiU0lOIn0=", # Singapore
    "LHR": "eyJhIjoiTE9OIn0=", # London
    "JFK": "eyJhIjoiTllDIn0=", # New York
    "HYD": "eyJhIjoiSFlEIn0=", # Hyderabad
}

async def get_location_id(city_name: str) -> Optional[str]:
    """
    Calls the /stays/auto-complete endpoint to find the unique ID for a city.
    """
    # First check our predefined map
    city_to_airport = {
        "London": "LHR",
        "New York": "JFK", 
        "Hyderabad": "HYD",
        "Bangkok": "BKK",
        "Singapore": "SIN"
    }
    
    if city_name in city_to_airport:
        airport_code = city_to_airport[city_name]
        return LOCATION_ID_MAP.get(airport_code)
    
    api_key = os.getenv("HOTEL_API_KEY")
    if not api_key:
        print("HOTEL_API_KEY not found, using fallback location IDs")
        return None

    url = "https://booking-com18.p.rapidapi.com/stays/auto-complete"
    headers = {
        "X-RapidAPI-Key": api_key,
        "X-RapidAPI-Host": "booking-com18.p.rapidapi.com"
    }
    params = {"query": city_name}

    async with httpx.AsyncClient() as client:
        try:
            print(f"--- Getting Location ID for city: {city_name} ---")
            response = await client.get(url, headers=headers, params=params, timeout=10.0)
            response.raise_for_status()
            results = response.json().get("data", [])
            
            for result in results:
                if result.get("type") == "CITY":
                    return result.get("id")
            return None
        except Exception as e:
            print(f"Error during location ID lookup: {e}")
            return None

async def search_hotels_by_location_id(location_id: str) -> List[schemas.HotelData]:
    """
    Searches for hotels using a valid locationId.
    """
    api_key = os.getenv("HOTEL_API_KEY")
    
    # If no API key or location ID, return mock data immediately
    if not api_key or not location_id:
        print("No API key or location ID, returning mock hotels")
        return get_mock_hotels()

    checkin_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
    checkout_date = (datetime.now() + timedelta(days=35)).strftime('%Y-%m-%d')

    url = "https://booking-com18.p.rapidapi.com/stays/search"
    headers = { "X-RapidAPI-Key": api_key, "X-RapidAPI-Host": "booking-com18.p.rapidapi.com" }
    params = {
        "locationId": location_id,
        "checkinDate": checkin_date,
        "checkoutDate": checkout_date,
        "adults": "2",
        "language": "en-gb",
        "currency": "INR",
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            print(f"--- Searching hotels with Location ID: {location_id} ---")
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            hotel_results = response.json().get("data", [])
            
            if not hotel_results:
                print("Hotel API returned empty results, using mock data")
                return get_mock_hotels()
            
            # Try to parse real hotel data
            validated_hotels = []
            for hotel in hotel_results:
                try:
                    hotel_data = schemas.HotelData(
                        name=hotel.get('name', 'Unknown Hotel'),
                        price_per_night=float(hotel.get('price', {}).get('perNight', 100.00)),
                        rating=float(hotel.get('reviewScore', 4.0)),
                        location=hotel.get('location', {}).get('name', 'City Center')
                    )
                    validated_hotels.append(hotel_data)
                except Exception as e:
                    print(f"Error parsing hotel: {e}")
                    continue
            
            if validated_hotels:
                print(f"Found {len(validated_hotels)} real hotels")
                return validated_hotels
            else:
                print("No valid hotels parsed, using mock data")
                return get_mock_hotels()
                
        except Exception as e:
            print(f"Hotel API error: {e}, using mock data")
            return get_mock_hotels()

def get_mock_hotels() -> List[schemas.HotelData]:
    """
    Returns realistic mock hotel data for demonstration.
    """
    print("Returning mock hotel data")
    return [
        schemas.HotelData(
            name="Hyatt Regency",
            price_per_night=150.00,
            rating=4.5,
            location="City Center"
        ),
        schemas.HotelData(
            name="Hilton Garden Inn", 
            price_per_night=120.00,
            rating=4.2,
            location="Near Airport"
        ),
        schemas.HotelData(
            name="Marriott Courtyard",
            price_per_night=110.00,
            rating=4.3,
            location="Business District"
        ),
        schemas.HotelData(
            name="Holiday Inn Express",
            price_per_night=90.00,
            rating=4.0,
            location="Downtown"
        ),
        schemas.HotelData(
            name="Radisson Blu",
            price_per_night=130.00,
            rating=4.4,
            location="Waterfront"
        )
    ]