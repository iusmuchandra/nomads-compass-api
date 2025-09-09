from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.orm import selectinload
from . import models, schemas, security
from datetime import date
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)

# --- Country Functions (Async) ---
async def get_country_by_code(db: AsyncSession, country_code: str) -> Optional[models.Country]:
    """Get country by code with async support"""
    try:
        result = await db.execute(
            select(models.Country)
            .options(selectinload(models.Country.requirements))
            .where(models.Country.code == country_code.upper())
        )
        return result.scalar_one_or_none()
    except Exception as e:
        logger.error(f"Error getting user {user_id}: {e}")
        return None

async def delete_itinerary(db: AsyncSession, itinerary_id: int, owner_id: int) -> Optional[models.Itinerary]:
    """Delete itinerary with async support (with owner verification)"""
    try:
        result = await db.execute(
            select(models.Itinerary)
            .where(models.Itinerary.id == itinerary_id, models.Itinerary.owner_id == owner_id)
        )
        db_itinerary = result.scalar_one_or_none()
        
        if not db_itinerary:
            return None
        
        await db.delete(db_itinerary)
        await db.commit()
        return db_itinerary
    except Exception as e:
        await db.rollback()
        logger.error(f"Error deleting itinerary {itinerary_id}: {e}")
        raise

async def get_legs_for_itinerary(db: AsyncSession, itinerary_id: int) -> List[models.Leg]:
    """Get all legs for a specific itinerary"""
    try:
        result = await db.execute(
            select(models.Leg)
            .where(models.Leg.itinerary_id == itinerary_id)
            .order_by(models.Leg.id)
        )
        return result.scalars().all()
    except Exception as e:
        logger.error(f"Error getting legs for itinerary {itinerary_id}: {e}")
        return []

async def delete_leg(db: AsyncSession, leg_id: int, owner_id: int) -> Optional[models.Leg]:
    """Delete a leg with owner verification"""
    try:
        # First verify the leg belongs to the user's itinerary
        result = await db.execute(
            select(models.Leg)
            .join(models.Itinerary)
            .where(
                models.Leg.id == leg_id,
                models.Itinerary.owner_id == owner_id
            )
        )
        db_leg = result.scalar_one_or_none()
        
        if not db_leg:
            return None
        
        await db.delete(db_leg)
        await db.commit()
        return db_leg
    except Exception as e:
        await db.rollback()
        logger.error(f"Error deleting leg {leg_id}: {e}")
        raise

# --- Bulk Operations ---
async def get_user_stats(db: AsyncSession, user_id: int) -> dict:
    """Get user statistics with async support"""
    try:
        # Get itinerary count
        itinerary_result = await db.execute(
            select(models.Itinerary).where(models.Itinerary.owner_id == user_id)
        )
        itinerary_count = len(itinerary_result.scalars().all())
        
        # Get total legs count
        leg_result = await db.execute(
            select(models.Leg)
            .join(models.Itinerary)
            .where(models.Itinerary.owner_id == user_id)
        )
        leg_count = len(leg_result.scalars().all())
        
        return {
            "total_itineraries": itinerary_count,
            "total_legs": leg_count
        }
    except Exception as e:
        logger.error(f"Error getting user stats for {user_id}: {e}")
        return {"total_itineraries": 0, "total_legs": 0}

# --- Search Functions ---
async def search_itineraries_by_name(db: AsyncSession, owner_id: int, search_term: str) -> List[models.Itinerary]:
    """Search itineraries by name with async support"""
    try:
        result = await db.execute(
            select(models.Itinerary)
            .options(selectinload(models.Itinerary.legs))
            .where(
                models.Itinerary.owner_id == owner_id,
                models.Itinerary.name.ilike(f"%{search_term}%")
            )
            .order_by(models.Itinerary.id.desc())
        )
        return result.scalars().all()
    except Exception as e:
        logger.error(f"Error searching itineraries for user {owner_id}: {e}")

async def create_country(db: AsyncSession, country: schemas.CountryCreate) -> models.Country:
    """Create country with async support"""
    try:
        db_country = models.Country(
            name=country.name,
            code=country.code,
            visa_policy=country.visa_policy,
            processing_time_days=country.processing_time_days
        )
        
        # Add requirements
        for req in country.requirements:
            db_req = models.VisaRequirement(**req.model_dump())
            db_country.requirements.append(db_req)
        
        db.add(db_country)
        await db.commit()
        await db.refresh(db_country)
        
        # Load requirements for the response
        await db.refresh(db_country, ["requirements"])
        return db_country
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating country: {e}")
        raise

async def update_country(db: AsyncSession, country_id: int, country_update: schemas.CountryUpdate) -> Optional[models.Country]:
    """Update country with async support"""
    try:
        result = await db.execute(select(models.Country).where(models.Country.id == country_id))
        db_country = result.scalar_one_or_none()
        
        if not db_country:
            return None
        
        update_data = country_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_country, key, value)
        
        await db.commit()
        await db.refresh(db_country)
        return db_country
    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating country {country_id}: {e}")
        raise

async def delete_country(db: AsyncSession, country_id: int) -> Optional[models.Country]:
    """Delete country with async support"""
    try:
        result = await db.execute(select(models.Country).where(models.Country.id == country_id))
        db_country = result.scalar_one_or_none()
        
        if not db_country:
            return None
        
        await db.delete(db_country)
        await db.commit()
        return db_country
    except Exception as e:
        await db.rollback()
        logger.error(f"Error deleting country {country_id}: {e}")
        raise

# --- User Functions (Async) ---
async def get_user_by_email(db: AsyncSession, email: str) -> Optional[models.User]:
    """Get user by email with async support"""
    try:
        result = await db.execute(select(models.User).where(models.User.email == email))
        return result.scalar_one_or_none()
    except Exception as e:
        logger.error(f"Error getting user by email {email}: {e}")
        return None

async def create_user(db: AsyncSession, user: schemas.UserCreate) -> models.User:
    """Create user with async support"""
    try:
        hashed_password = security.get_password_hash(user.password)
        db_user = models.User(
            email=user.email,
            hashed_password=hashed_password,
            instagram_handle=user.instagram_handle
        )
        db.add(db_user)
        await db.commit()
        await db.refresh(db_user)
        return db_user
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating user: {e}")
        raise

async def update_user(db: AsyncSession, user: models.User, update_data: schemas.UserUpdate) -> models.User:
    """Update user with async support"""
    try:
        for key, value in update_data.model_dump(exclude_unset=True).items():
            setattr(user, key, value)
        
        await db.commit()
        await db.refresh(user)
        return user
    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating user {user.id}: {e}")
        raise

# --- Itinerary Functions (Async) ---
async def create_itinerary(db: AsyncSession, itinerary: schemas.ItineraryCreate, owner_id: int) -> models.Itinerary:
    """Create itinerary with async support"""
    try:
        db_itinerary = models.Itinerary(
            name=itinerary.name,
            owner_id=owner_id
        )
        db.add(db_itinerary)
        await db.commit()
        await db.refresh(db_itinerary)
        
        # Ensure legs are loaded (even if empty)
        await db.refresh(db_itinerary, ["legs"])
        return db_itinerary
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating itinerary: {e}")
        raise

async def get_itinerary(db: AsyncSession, itinerary_id: int) -> Optional[models.Itinerary]:
    """Get itinerary by ID with async support, including legs"""
    try:
        result = await db.execute(
            select(models.Itinerary)
            .options(selectinload(models.Itinerary.legs))
            .where(models.Itinerary.id == itinerary_id)
        )
        return result.scalar_one_or_none()
    except Exception as e:
        logger.error(f"Error getting itinerary {itinerary_id}: {e}")
        return None

async def get_itineraries_by_owner(db: AsyncSession, owner_id: int) -> List[models.Itinerary]:
    """Get all itineraries for a user with async support"""
    try:
        result = await db.execute(
            select(models.Itinerary)
            .options(selectinload(models.Itinerary.legs))
            .where(models.Itinerary.owner_id == owner_id)
            .order_by(models.Itinerary.id.desc())
        )
        return result.scalars().all()
    except Exception as e:
        logger.error(f"Error getting itineraries for user {owner_id}: {e}")
        return []

async def create_itinerary_leg(db: AsyncSession, leg: schemas.LegCreate, itinerary_id: int) -> models.Leg:
    """Create itinerary leg with async support"""
    try:
        db_leg = models.Leg(
            origin_airport=leg.origin_airport,
            destination_airport=leg.destination_airport,
            travel_date=leg.travel_date,
            itinerary_id=itinerary_id
        )
        db.add(db_leg)
        await db.commit()
        await db.refresh(db_leg)
        return db_leg
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating leg for itinerary {itinerary_id}: {e}")
        raise

async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[models.User]:
    """Get user by ID with async support"""
    try:
        result = await db.execute(select(models.User).where(models.User.id == user_id))
        return result.scalar_one_or_none()
    except Exception as e:
        logger.error(f"Error getting user by ID {user_id}: {e}")
        return None