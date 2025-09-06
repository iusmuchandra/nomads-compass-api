from . import schemas, models
from typing import List
from pydantic import BaseModel # <--- THIS IS THE FIX. ADD THIS IMPORT.

class SponsorshipOffer(BaseModel):
    brand_name: str
    offer_description: str
    destination_specific: bool = False

# This is our mock database of available sponsorships.
# In a real app, this would come from a database.
AVAILABLE_OFFERS = [
    SponsorshipOffer(brand_name="SkyBags", offer_description="15% discount on all travel luggage."),
    SponsorshipOffer(brand_name="Nomad Apparel", offer_description="Get a free travel shirt with any purchase over ₹2000."),
    SponsorshipOffer(
        brand_name="GoPro India", 
        offer_description="Content Creator Program: Pitch a travel video concept for a chance to get a free camera.",
        destination_specific=True
    ),
]

def get_sponsorship_offers(user: models.User, itinerary: models.Itinerary) -> List[SponsorshipOffer]:
    """
    Generates a list of potential sponsorship offers for a user based on their profile.
    """
    offers = []
    
    # Simple MVP logic: if the user has an Instagram handle, they are eligible.
    if user.instagram_handle:
        # Offer all generic deals
        for offer in AVAILABLE_OFFERS:
            if not offer.destination_specific:
                offers.append(offer)
        
        # Simple context-aware logic: if the trip is to Thailand, offer a specific deal
        for leg in itinerary.legs:
            if leg.destination_airport == "BKK":
                # Check if the GoPro offer is not already added
                if not any(o.brand_name == "GoPro India" for o in offers):
                     offers.append(next(o for o in AVAILABLE_OFFERS if o.brand_name == "GoPro India"))

    return offers