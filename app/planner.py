import asyncio
from sqlalchemy.orm import Session
from . import crud, flights, schemas, hotels, models, sponsorship
from typing import List, Optional
from datetime import datetime

# A more useful mapping for our new dynamic planner
AIRPORT_TO_CITY_INFO = {
    "BKK": {"city": "Bangkok", "country_code": "THA"},
    "SIN": {"city": "Singapore", "country_code": "SGP"},
    "KUL": {"city": "Kuala Lumpur", "country_code": "MYS"},
    "HAN": {"city": "Hanoi", "country_code": "VNM"},
    "SGN": {"city": "Ho Chi Minh City", "country_code": "VNM"},
    "LHR": {"city": "London", "country_code": "GBR"},
    "JFK": {"city": "New York", "country_code": "USA"},
    "HYD": {"city": "Hyderabad", "country_code": "IND"},
    "DEL": {"city": "Delhi", "country_code": "IND"},
    "BOM": {"city": "Mumbai", "country_code": "IND"},
}

async def create_trip_plan(db: Session, origin_airport: str, dest_airport: str) -> schemas.TripPlan:
    city_info = AIRPORT_TO_CITY_INFO.get(dest_airport.upper())
    
    if not city_info:
        # If the destination is unknown, return an empty plan
        return schemas.TripPlan(
            visa_information=None,
            flight_options=[],
            hotel_options=[]
        )

    dest_country_code = city_info["country_code"]
    dest_city_name = city_info["city"]

    # Get visa information
    visa_info = None
    if dest_country_code:
        visa_info = crud.get_country_by_code(db, dest_country_code)

    # Get flight options (mock data for now)
    flight_options = []
    try:
        flight_options = await flights.search_flights_on_route(origin=origin_airport, destination=dest_airport)
    except:
        # Fallback to mock data if real API fails
        flight_options = [
            schemas.FlightData(
                airline="Example Airlines",
                flight_number="EX123",
                departure_time="08:00",
                arrival_time="14:00",
                price=299.99,
                duration="6h"
            )
        ]

    # Get hotel options (mock data for now)
    hotel_options = []
    try:
        location_id = await hotels.get_location_id(city_name=dest_city_name)
        if location_id:
            hotel_options = await hotels.search_hotels_by_location_id(location_id)
    except:
        # Fallback to mock data if real API fails
        hotel_options = [
            schemas.HotelData(
                name="Luxury Hotel",
                price_per_night=120.00,
                rating=4.5,
                location="City Center"
            )
        ]

    return schemas.TripPlan(
        visa_information=visa_info,
        flight_options=flight_options,
        hotel_options=hotel_options
    )

async def create_full_itinerary_plan(db: Session, itinerary: models.Itinerary, user: models.User) -> schemas.FullItineraryPlan:
    # Make sure legs are loaded
    if not hasattr(itinerary, 'legs') or not itinerary.legs:
        # Create empty plan if no legs
        return schemas.FullItineraryPlan(
            itinerary_details=itinerary,
            leg_plans=[],
            sponsorship_offers=[],
            plan_content="No travel legs found in this itinerary. Please add legs to generate a plan."
        )
    
    # Create a list of tasks, one for each leg of the journey
    leg_plan_tasks = [
        create_trip_plan(db, leg.origin_airport, leg.destination_airport)
        for leg in itinerary.legs
    ]
    
    # Get sponsorship offers
    sponsorship_deals = []
    try:
        sponsorship_deals = sponsorship.get_sponsorship_offers(user=user, itinerary=itinerary)
    except:
        sponsorship_deals = []

    # Execute all trip plan tasks concurrently
    trip_plan_results = await asyncio.gather(*leg_plan_tasks)
    
    # Combine the leg details with their corresponding plans
    leg_plans = []
    for i, (leg, plan) in enumerate(zip(itinerary.legs, trip_plan_results)):
        leg_plans.append(schemas.LegPlan(
            leg_number=i + 1,
            leg_details=leg,
            trip_plan=plan
        ))
    
    # Create detailed plan content
    plan_content = f"🌍 TRAVEL PLAN: {itinerary.name}\n\n"
    plan_content += "=" * 50 + "\n\n"
    
    for i, leg_plan in enumerate(leg_plans):
        leg = leg_plan.leg_details
        plan = leg_plan.trip_plan
        
        # Format travel date
        travel_date = leg.travel_date.strftime("%d %b %Y") if hasattr(leg.travel_date, 'strftime') else str(leg.travel_date)
        
        plan_content += f"✈️ LEG {i + 1}: {leg.origin_airport} → {leg.destination_airport}\n"
        plan_content += f"   📅 Date: {travel_date}\n"
        plan_content += f"   🏙️  Destination: {AIRPORT_TO_CITY_INFO.get(leg.destination_airport.upper(), {}).get('city', 'Unknown City')}\n\n"
        
        # Visa Information
        if plan.visa_information:
            plan_content += f"   📋 VISA REQUIREMENTS:\n"
            plan_content += f"      • Policy: {plan.visa_information.visa_policy}\n"
            plan_content += f"      • Processing Time: {plan.visa_information.processing_time_days} days\n"
            if hasattr(plan.visa_information, 'requirements') and plan.visa_information.requirements:
                plan_content += f"      • Documents Required:\n"
                for req in plan.visa_information.requirements:
                    plan_content += f"        - {req.document_name} {'(Mandatory)' if req.is_mandatory else '(Optional)'}\n"
        else:
            plan_content += f"   📋 VISA: Information not available\n"
        
        plan_content += "\n"
        
        # Flight Options
        if plan.flight_options:
            plan_content += f"   ✈️ FLIGHT OPTIONS ({len(plan.flight_options)} available):\n"
            for flight in plan.flight_options[:3]:  # Show top 3 flights
                plan_content += f"      • {flight.airline} {flight.flight_number}: {flight.departure_time} → {flight.arrival_time} (${flight.price})\n"
        else:
            plan_content += f"   ✈️ FLIGHTS: No flight data available\n"
        
        plan_content += "\n"
        
        # Hotel Options
        if plan.hotel_options:
            plan_content += f"   🏨 HOTEL OPTIONS ({len(plan.hotel_options)} available):\n"
            for hotel in plan.hotel_options[:3]:  # Show top 3 hotels
                plan_content += f"      • {hotel.name}: ${hotel.price_per_night}/night ⭐{hotel.rating}\n"
        else:
            plan_content += f"   🏨 HOTELS: No hotel data available\n"
        
        plan_content += "\n" + "-" * 40 + "\n\n"
    
    # Sponsorship Offers
    if sponsorship_deals:
        plan_content += "🎁 EXCLUSIVE SPONSORSHIP OFFERS:\n\n"
        for deal in sponsorship_deals:
            plan_content += f"   🏷️  {deal.brand_name}\n"
            plan_content += f"      • Discount: {deal.discount_percentage}% off\n"
            plan_content += f"      • Terms: {deal.terms_and_conditions}\n"
            plan_content += f"      • Contact: {deal.contact_email}\n\n"
    else:
        plan_content += "💡 No sponsorship offers available at this time.\n\n"
    
    plan_content += "=" * 50 + "\n"
    plan_content += "✨ Happy travels! Remember to check all visa requirements and book in advance. ✨\n"

    return schemas.FullItineraryPlan(
        itinerary_details=itinerary,
        leg_plans=leg_plans,
        sponsorship_offers=sponsorship_deals,
        plan_content=plan_content
    )