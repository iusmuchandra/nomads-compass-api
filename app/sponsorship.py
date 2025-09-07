from . import schemas, models
from typing import List
from pydantic import BaseModel

class SponsorshipOffer(BaseModel):
    brand_name: str
    offer_description: str
    destination_specific: bool = False

AVAILABLE_OFFERS = [
    SponsorshipOffer(brand_name="SkyBags", offer_description="15% discount on all travel luggage.", destination_specific=False),
    SponsorshipOffer(brand_name="Nomad Apparel", offer_description="Get a free travel shirt with any purchase over ₹2000.", destination_specific=False),
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
    
    if user.instagram_handle:
        for offer in AVAILABLE_OFFERS:
            if not offer.destination_specific:
                offers.append(offer)
        
        for leg in itinerary.legs:
            if leg.destination_airport == "BKK":
                if not any(o.brand_name == "GoPro India" for o in offers):
                     offers.append(next(o for o in AVAILABLE_OFFERS if o.brand_name == "GoPro India"))

    return offers

