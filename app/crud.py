from sqlalchemy.orm import Session
from . import models, schemas, security
from datetime import date
from typing import Optional

# --- (Keep existing country/itinerary functions) ---
def get_country_by_code(db: Session, country_code: str):
    return db.query(models.Country).filter(models.Country.code == country_code.upper()).first()
def create_country(db: Session, country: schemas.CountryCreate):
    db_country = models.Country(name=country.name, code=country.code, visa_policy=country.visa_policy, processing_time_days=country.processing_time_days)
    for req in country.requirements:
        db_req = models.VisaRequirement(**req.model_dump())
        db_country.requirements.append(db_req)
    db.add(db_country)
    db.commit()
    db.refresh(db_country)
    return db_country
def update_country(db: Session, country_id: int, country_update: schemas.CountryUpdate):
    db_country = db.query(models.Country).filter(models.Country.id == country_id).first()
    if not db_country: return None
    update_data = country_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_country, key, value)
    db.add(db_country)
    db.commit()
    db.refresh(db_country)
    return db_country
def delete_country(db: Session, country_id: int):
    db_country = db.query(models.Country).filter(models.Country.id == country_id).first()
    if not db_country: return None
    db.delete(db_country)
    db.commit()
    return db_country
def get_itinerary(db: Session, itinerary_id: int) -> Optional[models.Itinerary]:
    return db.query(models.Itinerary).filter(models.Itinerary.id == itinerary_id).first()
def create_itinerary_leg(db: Session, leg: schemas.LegCreate, itinerary_id: int) -> models.Leg:
    db_leg = models.Leg(**leg.model_dump(), itinerary_id=itinerary_id)
    db.add(db_leg)
    db.commit()
    db.refresh(db_leg)
    return db_leg

# --- NEW User Functions ---

def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.email == email).first()

def create_user(db: Session, user: schemas.UserCreate) -> models.User:
    hashed_password = security.get_password_hash(user.password)
    db_user = models.User(
        email=user.email,
        hashed_password=hashed_password,
        instagram_handle=user.instagram_handle
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# --- UPDATED Itinerary Function ---
# It now requires an owner_id
def create_itinerary(db: Session, itinerary: schemas.ItineraryCreate, owner_id: int) -> models.Itinerary:
    db_itinerary = models.Itinerary(**itinerary.model_dump(), owner_id=owner_id)
    db.add(db_itinerary)
    db.commit()
    db.refresh(db_itinerary)
    return db_itinerary

def update_user(db: Session, user: models.User, update_data: schemas.UserUpdate) -> models.User:
    for key, value in update_data.model_dump(exclude_unset=True).items():
        setattr(user, key, value)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user