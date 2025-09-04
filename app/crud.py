# In app/crud.py

from sqlalchemy.orm import Session
from . import models, schemas

def get_country_by_code(db: Session, country_code: str):
    return db.query(models.Country).filter(models.Country.code == country_code.upper()).first()

def create_country(db: Session, country: schemas.CountryCreate):
    # Create the main Country object
    db_country = models.Country(
        name=country.name,
        code=country.code,
        visa_policy=country.visa_policy,
        processing_time_days=country.processing_time_days
    )
    db.add(db_country)
    db.commit()
    db.refresh(db_country)

    # Now create and associate the VisaRequirement objects
    for req in country.requirements:
        db_req = models.VisaRequirement(
            **req.model_dump(), country_id=db_country.id
        )
        db.add(db_req)
    
    db.commit()
    db.refresh(db_country)
    return db_country

def update_country(db: Session, country_id: int, country_update: schemas.CountryUpdate):
    db_country = db.query(models.Country).filter(models.Country.id == country_id).first()
    if not db_country:
        return None

    # Get the update data, excluding any fields that were not set (i.e., are None)
    update_data = country_update.model_dump(exclude_unset=True)
    
    for key, value in update_data.items():
        setattr(db_country, key, value)

    db.add(db_country)
    db.commit()
    db.refresh(db_country)
    return db_country

# In app/crud.py, add this function.

def delete_country(db: Session, country_id: int):
    db_country = db.query(models.Country).filter(models.Country.id == country_id).first()
    if not db_country:
        return None
    
    db.delete(db_country)
    db.commit()
    return db_country 
