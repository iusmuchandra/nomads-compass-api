from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional
from datetime import date

# =================================
# Schemas for Visa Requirements
# =================================
class VisaRequirementBase(BaseModel):
    document_name: str
    description: Optional[str] = None
    is_mandatory: bool = True

class VisaRequirementCreate(VisaRequirementBase):
    pass

class VisaRequirement(VisaRequirementBase):
    id: int
    country_id: int
    class Config: from_attributes = True

# =================================
# Schemas for Countries
# =================================
class CountryBase(BaseModel):
    name: str
    code: str
    visa_policy: str
    processing_time_days: int

class CountryCreate(CountryBase):
    requirements: List[VisaRequirementCreate] = []

class Country(CountryBase):
    id: int
    requirements: List[VisaRequirement] = []
    class Config: from_attributes = True

# THIS IS ONE OF THE MISSING CLASSES
class CountryUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    visa_policy: Optional[str] = None
    processing_time_days: Optional[int] = None

# =================================
# Schemas for User and Auth
# =================================
class UserBase(BaseModel):
    email: EmailStr
    instagram_handle: Optional[str] = None

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    class Config: from_attributes = True

# THIS IS THE OTHER MISSING CLASS
class UserUpdate(BaseModel):
    instagram_handle: Optional[str] = None

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

# =================================
# Schemas for External APIs
# =================================
class FlightData(BaseModel):
    airline: str
    flight: str
    departure: str
    arrival: str
    altitude: Optional[int] = None
    type: str

class HotelData(BaseModel):
    name: str
    reviewScore: Optional[float] = None
    reviewScoreWord: Optional[str] = None

# =================================
# Schemas for Itinerary Engine
# =================================
class LegBase(BaseModel):
    origin_airport: str
    destination_airport: str
    travel_date: date

class LegCreate(LegBase):
    pass

class Leg(LegBase):
    id: int
    itinerary_id: int
    class Config: from_attributes = True

class ItineraryBase(BaseModel):
    name: str

class ItineraryCreate(ItineraryBase):
    pass

class Itinerary(ItineraryBase):
    id: int
    owner_id: int
    legs: List[Leg] = []
    class Config: from_attributes = True

class TripPlan(BaseModel):
    visa_information: Optional[Country] = None
    flight_options: List[FlightData] = []
    hotel_options: List[HotelData] = []

class LegPlan(BaseModel):
    leg_details: Leg
    trip_plan: TripPlan

class SponsorshipOffer(BaseModel):
    brand_name: str
    offer_description: str
    destination_specific: bool

class FullItineraryPlan(BaseModel):
    itinerary_details: Itinerary
    leg_plans: List[LegPlan]
    sponsorship_offers: List[SponsorshipOffer] = []