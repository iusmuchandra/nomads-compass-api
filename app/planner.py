import asyncio
import json
from datetime import datetime, timedelta
from typing import List, Optional
# FIX 1: Import the correct async components
from sqlalchemy.ext.asyncio import AsyncSession
from . import async_crud, flights, schemas, hotels, models, sponsorship

# Enhanced API Quota and Error Handler
class APIQuotaHandler:
    def __init__(self):
        self.quota_exceeded = {}  # Track quota by service
        self.last_check = {}
        self.error_count = {}
        
    def is_quota_exceeded(self, service: str) -> bool:
        return self.quota_exceeded.get(service, False)
        
    def set_quota_exceeded(self, service: str):
        self.quota_exceeded[service] = True
        self.last_check[service] = datetime.now()
        print(f"⚠️  API quota exceeded for {service}, switching to mock data")
        
    def increment_error(self, service: str):
        self.error_count[service] = self.error_count.get(service, 0) + 1
        if self.error_count[service] >= 3:  # After 3 errors, assume quota exceeded
            self.set_quota_exceeded(service)
    
    def reset_quota_status(self, service: str):
        """Reset quota status (could be called daily/monthly)"""
        self.quota_exceeded[service] = False
        self.error_count[service] = 0
        self.last_check[service] = None
        
    def get_mock_flight_data(self, origin: str, destination: str, departure_date: str = None) -> List[schemas.FlightData]:
        """Return realistic mock flight data when API quota is exceeded"""
        city_info = AIRPORT_TO_CITY_INFO.get(destination.upper(), {"city": "Unknown City"})
        
        return [
            schemas.FlightData(
                airline="Air India",
                flight_number="AI101",
                departure_time="08:30",
                arrival_time="14:45",
                price=18500.0,
                duration="6h 15m",
                stops=0,
                booking_link="https://airindia.com",
                note="⚠️ Mock data - API quota exceeded"
            ),
            schemas.FlightData(
                airline="IndiGo",
                flight_number="6E205",
                departure_time="11:20",
                arrival_time="17:55",
                price=15750.0,
                duration="6h 35m",
                stops=1,
                booking_link="https://goindigo.in",
                note="⚠️ Mock data - API quota exceeded"
            ),
            schemas.FlightData(
                airline="Singapore Airlines",
                flight_number="SQ407",
                departure_time="15:45",
                arrival_time="22:10",
                price=22300.0,
                duration="6h 25m",
                stops=0,
                booking_link="https://singaporeair.com",
                note="⚠️ Mock data - API quota exceeded"
            )
        ]
        
    def get_mock_hotel_data(self, location: str, checkin_date: str = None, checkout_date: str = None) -> List[schemas.HotelData]:
        """Return realistic mock hotel data when API quota is exceeded"""
        return [
            schemas.HotelData(
                name=f"Grand {location} Hotel",
                price_per_night=4500.0,
                rating=4.5,
                location="City Center",
                amenities=["WiFi", "Pool", "Spa", "Restaurant", "Gym"],
                image_url="https://via.placeholder.com/400x300",
                booking_link="https://booking.com",
                note="⚠️ Mock data - API quota exceeded"
            ),
            schemas.HotelData(
                name=f"Luxury Suites {location}",
                price_per_night=6800.0,
                rating=4.8,
                location="Business District",
                amenities=["WiFi", "Pool", "Concierge", "Restaurant", "Bar"],
                image_url="https://via.placeholder.com/400x300",
                booking_link="https://hotels.com",
                note="⚠️ Mock data - API quota exceeded"
            ),
            schemas.HotelData(
                name=f"Budget Inn {location}",
                price_per_night=2200.0,
                rating=3.8,
                location="Downtown",
                amenities=["WiFi", "24/7 Reception"],
                image_url="https://via.placeholder.com/400x300",
                booking_link="https://hostelworld.com",
                note="⚠️ Mock data - API quota exceeded"
            )
        ]

# Global quota handler instance
quota_handler = APIQuotaHandler()

# Enhanced airport to city mapping
AIRPORT_TO_CITY_INFO = {
    "BKK": {"city": "Bangkok", "country_code": "THA"},
    "SIN": {"city": "Singapore", "country_code": "SGP"},
    "KUL": {"city": "Kuala Lumpur", "country_code": "MYS"},
    "HAN": {"city": "Hanoi", "country_code": "VNM"},
    "SGN": {"city": "Ho Chi Minh City", "country_code": "VNM"},
    "LHR": {"city": "London", "country_code": "GBR"},
    "JFK": {"city": "New York", "country_code": "USA"},
    "LAX": {"city": "Los Angeles", "country_code": "USA"},
    "CDG": {"city": "Paris", "country_code": "FRA"},
    "NRT": {"city": "Tokyo", "country_code": "JPN"},
    "ICN": {"city": "Seoul", "country_code": "KOR"},
    "HYD": {"city": "Hyderabad", "country_code": "IND"},
    "DEL": {"city": "Delhi", "country_code": "IND"},
    "BOM": {"city": "Mumbai", "country_code": "IND"},
    "BLR": {"city": "Bangalore", "country_code": "IND"},
    "MAA": {"city": "Chennai", "country_code": "IND"},
    "CCU": {"city": "Kolkata", "country_code": "IND"},
    "GOI": {"city": "Goa", "country_code": "IND"},
    "DXB": {"city": "Dubai", "country_code": "ARE"},
    "DOH": {"city": "Doha", "country_code": "QAT"},
    "SYD": {"city": "Sydney", "country_code": "AUS"},
    "MEL": {"city": "Melbourne", "country_code": "AUS"},
}

async def fetch_flights_with_fallback(origin: str, destination: str, departure_date: str = None) -> List[schemas.FlightData]:
    """Fetch flights with graceful fallback to mock data on API failures"""
    service = "flights"
    
    # Check if we already know quota is exceeded
    if quota_handler.is_quota_exceeded(service):
        print(f"🔄 Using mock flight data for {origin} → {destination} (quota exceeded)")
        return quota_handler.get_mock_flight_data(origin, destination, departure_date)
    
    try:
        print(f"🛫 Fetching real flight data for {origin} → {destination}")
        flight_options = await flights.search_flights_on_route(origin=origin, destination=destination)
        
        # Reset error count on successful call
        quota_handler.error_count[service] = 0
        return flight_options
        
    except Exception as e:
        error_str = str(e).lower()
        
        # Check for quota/rate limit errors
        if any(keyword in error_str for keyword in ["429", "quota", "rate limit", "exceeded", "limit"]):
            quota_handler.set_quota_exceeded(service)
        else:
            quota_handler.increment_error(service)
            print(f"⚠️  Flight API error ({quota_handler.error_count.get(service, 0)}/3): {e}")
        
        # Always return mock data on any error
        print(f"🔄 Falling back to mock flight data for {origin} → {destination}")
        return quota_handler.get_mock_flight_data(origin, destination, departure_date)

async def fetch_hotels_with_fallback(city_name: str, checkin_date: str = None, checkout_date: str = None) -> List[schemas.HotelData]:
    """Fetch hotels with graceful fallback to mock data on API failures"""
    service = "hotels"
    
    # Check if we already know quota is exceeded
    if quota_handler.is_quota_exceeded(service):
        print(f"🔄 Using mock hotel data for {city_name} (quota exceeded)")
        return quota_handler.get_mock_hotel_data(city_name, checkin_date, checkout_date)
    
    try:
        print(f"🏨 Fetching real hotel data for {city_name}")
        location_id = await hotels.get_location_id(city_name=city_name)
        if location_id:
            # FIX 2: Call the hotel search function with the correct arguments
            hotel_options = await hotels.search_hotels_by_location_id(location_id)
            
            # Reset error count on successful call
            quota_handler.error_count[service] = 0
            return hotel_options
        else:
            print(f"⚠️  No location ID found for {city_name}")
            return quota_handler.get_mock_hotel_data(city_name, checkin_date, checkout_date)
            
    except Exception as e:
        error_str = str(e).lower()
        
        # Check for quota/rate limit errors
        if any(keyword in error_str for keyword in ["429", "quota", "rate limit", "exceeded", "limit", "400"]):
            quota_handler.set_quota_exceeded(service)
        else:
            quota_handler.increment_error(service)
            print(f"⚠️  Hotel API error ({quota_handler.error_count.get(service, 0)}/3): {e}")
        
        # Always return mock data on any error
        print(f"🔄 Falling back to mock hotel data for {city_name}")
        return quota_handler.get_mock_hotel_data(city_name, checkin_date, checkout_date)

# FIX 1: Update function signature to use AsyncSession
async def create_trip_plan(db: AsyncSession, origin_airport: str, dest_airport: str, travel_date: str = None) -> schemas.TripPlan:
    """Create a trip plan with enhanced error handling and fallbacks"""
    print(f"📋 Creating trip plan: {origin_airport} → {dest_airport}")
    
    city_info = AIRPORT_TO_CITY_INFO.get(dest_airport.upper())
    
    if not city_info:
        print(f"⚠️  Unknown destination airport: {dest_airport}")
        # Return a plan with limited information for unknown destinations
        return schemas.TripPlan(
            visa_information=None,
            flight_options=[schemas.FlightData(
                airline="Unknown Route",
                flight_number="N/A",
                departure_time="N/A",
                arrival_time="N/A",
                price=0.0,
                duration="N/A",
                note="⚠️ Route information not available"
            )],
            hotel_options=[schemas.HotelData(
                name="Hotel information not available",
                price_per_night=0.0,
                rating=0.0,
                location="Unknown",
                note="⚠️ Destination information not available"
            )]
        )

    dest_country_code = city_info["country_code"]
    dest_city_name = city_info["city"]

    # Get visa information
    visa_info = None
    try:
        if dest_country_code:
            # FIX 1: Use await and async_crud
            visa_info = await async_crud.get_country_by_code(db, dest_country_code)
    except Exception as e:
        print(f"⚠️  Error fetching visa info: {e}")

    # Get flight options with fallback
    flight_options = await fetch_flights_with_fallback(
        origin=origin_airport, 
        destination=dest_airport, 
        departure_date=travel_date
    )

    # Get hotel options with fallback
    hotel_options = await fetch_hotels_with_fallback(
        city_name=dest_city_name,
        checkin_date=travel_date,
        checkout_date=travel_date  # You might want to calculate checkout date
    )

    return schemas.TripPlan(
        visa_information=visa_info,
        flight_options=flight_options,
        hotel_options=hotel_options
    )

# FIX 1: Update function signature to use AsyncSession
async def create_full_itinerary_plan(db: AsyncSession, itinerary: models.Itinerary, user: models.User) -> schemas.FullItineraryPlan:
    """Create a comprehensive itinerary plan with enhanced error handling"""
    print(f"🗺️  Generating full itinerary plan for: {itinerary.name}")
    
    # Make sure legs are loaded
    if not hasattr(itinerary, 'legs') or not itinerary.legs:
        print("⚠️  No travel legs found in itinerary")
        return schemas.FullItineraryPlan(
            itinerary_details=itinerary,
            leg_plans=[],
            sponsorship_offers=[],
            plan_content="❌ No travel legs found in this itinerary. Please add legs to generate a plan."
        )
    
    print(f"📍 Processing {len(itinerary.legs)} travel legs")
    
    # Create a list of tasks, one for each leg of the journey
    leg_plan_tasks = []
    for leg in itinerary.legs:
        travel_date = leg.travel_date.strftime("%Y-%m-%d") if hasattr(leg.travel_date, 'strftime') else str(leg.travel_date)
        task = create_trip_plan(db, leg.origin_airport, leg.destination_airport, travel_date)
        leg_plan_tasks.append(task)
    
    # Get sponsorship offers
    sponsorship_deals = []
    try:
        print("🎁 Fetching sponsorship offers...")
        sponsorship_deals = sponsorship.get_sponsorship_offers(user=user, itinerary=itinerary)
        # Convert SponsorshipOffer objects to dictionaries if needed
        sponsorship_deals = [deal.dict() if hasattr(deal, 'dict') else deal for deal in sponsorship_deals]
        print(f"✅ Found {len(sponsorship_deals)} sponsorship offers")
    except Exception as e:
        print(f"⚠️  Sponsorship error: {e}")
        sponsorship_deals = []

    # Execute all trip plan tasks concurrently
    print("⚡ Executing all API calls concurrently...")
    trip_plan_results = await asyncio.gather(*leg_plan_tasks, return_exceptions=True)
    
    # Handle any exceptions in the results
    valid_trip_plans = []
    for i, result in enumerate(trip_plan_results):
        if isinstance(result, Exception):
            print(f"⚠️  Error in leg {i+1}: {result}")
            # Create a fallback trip plan
            leg = itinerary.legs[i]
            fallback_plan = schemas.TripPlan(
                visa_information=None,
                flight_options=[schemas.FlightData(
                    airline="Error",
                    flight_number="N/A",
                    departure_time="N/A",
                    arrival_time="N/A",
                    price=0.0,
                    duration="N/A",
                    note="❌ Error generating plan for this leg"
                )],
                hotel_options=[schemas.HotelData(
                    name="Error fetching hotels",
                    price_per_night=0.0,
                    rating=0.0,
                    location="Unknown",
                    note="❌ Error fetching hotel information"
                )]
            )
            valid_trip_plans.append(fallback_plan)
        else:
            valid_trip_plans.append(result)
    
    # Combine the leg details with their corresponding plans
    leg_plans = []
    for i, (leg, plan) in enumerate(zip(itinerary.legs, valid_trip_plans)):
        leg_plans.append(schemas.LegPlan(
            leg_number=i + 1,
            leg_details=leg,
            trip_plan=plan
        ))
    
    # Generate enhanced plan content
    plan_content = generate_enhanced_plan_content(itinerary, leg_plans, sponsorship_deals)

    print("✅ Full itinerary plan generated successfully")
    return schemas.FullItineraryPlan(
        itinerary_details=itinerary,
        leg_plans=leg_plans,
        sponsorship_offers=sponsorship_deals,
        plan_content=plan_content
    )

def generate_enhanced_plan_content(itinerary: models.Itinerary, leg_plans: List[schemas.LegPlan], sponsorship_deals: List) -> str:
    """Generate enhanced, formatted plan content"""
    plan_content = f"🌍 NOMAD'S COMPASS: {itinerary.name}\n"
    plan_content += f"Generated on: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}\n"
    plan_content += "=" * 60 + "\n\n"
    
    # Add quota status warning if applicable
    services_on_mock = []
    if quota_handler.is_quota_exceeded("flights"):
        services_on_mock.append("flights")
    if quota_handler.is_quota_exceeded("hotels"):
        services_on_mock.append("hotels")
    
    if services_on_mock:
        plan_content += "⚠️  NOTICE: Some data is from mock sources due to API limitations.\n"
        plan_content += f"   Mock data services: {', '.join(services_on_mock)}\n"
        plan_content += "   Real-time data will be restored when API access is available.\n\n"
    
    for i, leg_plan in enumerate(leg_plans):
        leg = leg_plan.leg_details
        plan = leg_plan.trip_plan
        
        # Format travel date
        travel_date = leg.travel_date.strftime("%A, %B %d, %Y") if hasattr(leg.travel_date, 'strftime') else str(leg.travel_date)
        
        plan_content += f"✈️  LEG {i + 1}: {leg.origin_airport} → {leg.destination_airport}\n"
        plan_content += f"   📅 Date: {travel_date}\n"
        
        city_name = AIRPORT_TO_CITY_INFO.get(leg.destination_airport.upper(), {}).get('city', 'Unknown City')
        country_name = AIRPORT_TO_CITY_INFO.get(leg.destination_airport.upper(), {}).get('country_code', 'Unknown')
        plan_content += f"   🏙️  Destination: {city_name}, {country_name}\n\n"
        
        # Visa Information
        if plan.visa_information:
            plan_content += f"   📋 VISA REQUIREMENTS:\n"
            plan_content += f"      • Policy: {plan.visa_information.visa_policy}\n"
            plan_content += f"      • Processing Time: {plan.visa_information.processing_time_days} days\n"
            if hasattr(plan.visa_information, 'requirements') and plan.visa_information.requirements:
                plan_content += f"      • Documents Required:\n"
                for req in plan.visa_information.requirements:
                    status = "✅ Mandatory" if req.is_mandatory else "⚪ Optional"
                    plan_content += f"        - {req.document_name} ({status})\n"
        else:
            plan_content += f"   📋 VISA: Information not available for this destination\n"
        
        plan_content += "\n"
        
        # Flight Options
        if plan.flight_options and plan.flight_options[0].airline != "Error":
            plan_content += f"   ✈️  FLIGHT OPTIONS ({len(plan.flight_options)} found):\n"
            for j, flight in enumerate(plan.flight_options[:3]):  # Show top 3 flights
                # FIX 3: Safely access the .note attribute
                note = getattr(flight, 'note', None)
                mock_indicator = " 🔄" if note and "mock" in note.lower() else ""
                plan_content += f"      {j+1}. {flight.airline} {flight.flight_number}{mock_indicator}\n"
                plan_content += f"         🕐 {flight.departure_time} → {flight.arrival_time} ({flight.duration})\n"
                plan_content += f"         💰 ₹{flight.price:,.0f} | Stops: {getattr(flight, 'stops', 'N/A')}\n"
                if hasattr(flight, 'booking_link') and flight.booking_link:
                    plan_content += f"         🔗 Book: {flight.booking_link}\n"
                plan_content += "\n"
        else:
            plan_content += f"   ✈️  FLIGHTS: ❌ No flight data available\n\n"
        
        # Hotel Options
        if plan.hotel_options and plan.hotel_options[0].name != "Error fetching hotels":
            plan_content += f"   🏨 HOTEL OPTIONS ({len(plan.hotel_options)} found):\n"
            for j, hotel in enumerate(plan.hotel_options[:3]):  # Show top 3 hotels
                # FIX 3: Safely access the .note attribute
                note = getattr(hotel, 'note', None)
                mock_indicator = " 🔄" if note and "mock" in note.lower() else ""
                plan_content += f"      {j+1}. {hotel.name}{mock_indicator}\n"
                plan_content += f"         📍 {hotel.location} | ⭐ {hotel.rating}/5.0\n"
                plan_content += f"         💰 ₹{hotel.price_per_night:,.0f}/night\n"
                if hasattr(hotel, 'amenities') and hotel.amenities:
                    plan_content += f"         🎯 Amenities: {', '.join(hotel.amenities[:4])}\n"
                if hasattr(hotel, 'booking_link') and hotel.booking_link:
                    plan_content += f"         🔗 Book: {hotel.booking_link}\n"
                plan_content += "\n"
        else:
            plan_content += f"   🏨 HOTELS: ❌ No hotel data available\n\n"
        
        plan_content += "─" * 50 + "\n\n"
    
    # Sponsorship Offers
    if sponsorship_deals:
        plan_content += "🎁 EXCLUSIVE SPONSORSHIP OPPORTUNITIES:\n\n"
        for i, deal in enumerate(sponsorship_deals):
            plan_content += f"   {i+1}. 🏷️  {deal.get('brand_name', 'Unknown Brand')}\n"
            plan_content += f"      💡 {deal.get('offer_description', 'No description available')}\n"
            if deal.get('destination_specific'):
                plan_content += f"      🎯 Destination-Specific Offer\n"
            if deal.get('value'):
                plan_content += f"      💰 Value: {deal.get('value')}\n"
            plan_content += "\n"
    else:
        plan_content += "💡 No sponsorship offers available at this time.\n"
        plan_content += "   Check back later for exclusive deals from our partners!\n\n"
    
    # Footer
    plan_content += "=" * 60 + "\n"
    plan_content += "✨ TRAVEL SMART WITH NOMAD'S COMPASS ✨\n"
    plan_content += "💡 Tips:\n"
    plan_content += "   • Book flights 2-3 months in advance for better prices\n"
    plan_content += "   • Check visa requirements well in advance\n"
    plan_content += "   • Consider travel insurance for international trips\n"
    plan_content += "   • Keep digital copies of important documents\n\n"
    plan_content += "🌟 Happy travels! Safe journey ahead! 🌟\n"

    return plan_content

# Utility function to reset quota status (could be called by a scheduled task)
def reset_all_quota_status():
    """Reset all quota statuses - useful for scheduled maintenance"""
    global quota_handler
    for service in ["flights", "hotels"]:
        quota_handler.reset_quota_status(service)
    print("✅ All API quota statuses have been reset")

# Function to get current API status
def get_api_status():
    """Get current status of all APIs"""
    status = {
        "flights": {
            "quota_exceeded": quota_handler.is_quota_exceeded("flights"),
            "error_count": quota_handler.error_count.get("flights", 0),
            "last_check": quota_handler.last_check.get("flights")
        },
        "hotels": {
            "quota_exceeded": quota_handler.is_quota_exceeded("hotels"),
            "error_count": quota_handler.error_count.get("hotels", 0),
            "last_check": quota_handler.last_check.get("hotels")
        }
    }
    return status