from pydantic import BaseModel
from typing import List, Optional

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

    class Config:
        from_attributes = True

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

    class Config:
        from_attributes = True

class CountryUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    visa_policy: Optional[str] = None
    processing_time_days: Optional[int] = None

# =================================
# Schemas for External APIs
# =================================

# FINAL, CORRECTED VERSION
class FlightData(BaseModel):
    airline: str
    flight: str
    departure: str
    arrival: str
    altitude: Optional[int] = None  # <-- The fix: Mark altitude as optional
    type: str