# In app/schemas.py

from pydantic import BaseModel
from typing import List, Optional  # <--- 1. IMPORT OPTIONAL HERE

# Schema for creating/reading a single requirement
class VisaRequirementBase(BaseModel):
    document_name: str
    description: Optional[str] = None # <--- 2. CHANGE THIS LINE
    is_mandatory: bool = True

class VisaRequirement(VisaRequirementBase):
    id: int

    class Config:
        from_attributes = True

# Schema for reading a country with its requirements
class CountryBase(BaseModel):
    name: str
    code: str
    visa_policy: str
    processing_time_days: int

class Country(CountryBase):
    id: int
    requirements: List[VisaRequirement] = []

    class Config:
        from_attributes = True