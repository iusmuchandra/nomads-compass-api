# In app/schemas.py

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

# We modify this schema to include a reference back to its parent Country
class VisaRequirement(VisaRequirementBase):
    id: int
    country_id: int  # Add the foreign key field

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