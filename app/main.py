from fastapi import FastAPI
from pydantic import BaseModel
from typing import List

app = FastAPI(
    title="Nomad's Compass API",
    description="The core engine for the world's smartest travel agent.",
    version="0.1.0"
)

# Pydantic models (our data schemas)
class VisaRequirement(BaseModel):
    document_name: str
    description: str
    is_mandatory: bool

class VisaInfo(BaseModel):
    country_code: str
    country_name: str
    policy: str  # e.g., "Visa on Arrival", "E-Visa", "Visa Required"
    processing_time_days: int
    requirements: List[VisaRequirement]

# The first API endpoint
@app.get("/visa/{country_code}", response_model=VisaInfo)
def get_visa_info(country_code: str):
    """
    Retrieves visa information for an Indian passport holder
    for a given destination country code (e.g., 'THA' for Thailand).
    """
    # This is a stub. In the future, this data will come from our PostgreSQL DB.
    if country_code.upper() == "THA":
        return VisaInfo(
            country_code="THA",
            country_name="Thailand",
            policy="Visa on Arrival",
            processing_time_days=1,
            requirements=[
                VisaRequirement(document_name="Passport", description="Valid for at least 6 months", is_mandatory=True),
                VisaRequirement(document_name="Return Flight Ticket", description="Proof of onward travel", is_mandatory=True),
                VisaRequirement(document_name="Proof of Accommodation", description="Hotel bookings for the duration of stay", is_mandatory=True),
                VisaRequirement(document_name="Passport Size Photo", description="4x6 cm, white background", is_mandatory=True),
            ]
        )
    # Return a proper error response
    return {"error": "Country data not found"}