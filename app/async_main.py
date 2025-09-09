import time
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from jose import JWTError, jwt
from datetime import datetime

from . import models, schemas, flights, planner, security, sponsorship
from .async_crud import (
    get_user_by_email, create_user, update_user, create_itinerary,
    get_itinerary, get_itineraries_by_owner, create_itinerary_leg,
    get_country_by_code, create_country, update_country, delete_country,
    get_user_stats
)
from .async_database import get_async_db, init_database, test_database_connection, close_database

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Application lifecycle management
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown"""
    logger.info("Starting Nomad's Compass API...")
    
    # Startup
    database_ready = await init_database()
    if database_ready:
        connection_test = await test_database_connection()
        if connection_test:
            logger.info("Database initialization completed successfully")
        else:
            logger.warning("Database connection test failed")
    else:
        logger.warning("Database initialization failed")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Nomad's Compass API...")
    await close_database()
    logger.info("Shutdown completed")

app = FastAPI(
    title="Nomad's Compass API",
    description="The core engine for the world's smartest travel agent with AI-powered itinerary planning.",
    version="3.2.0",  # Version bump for async support
    contact={
        "name": "Nomad's Compass Support", 
        "email": "support@nomadscompass.com",
    },
    license_info={
        "name": "MIT",
    },
    lifespan=lifespan
)

# CORS MIDDLEWARE
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:8080", 
        "http://127.0.0.1:8000",
        "http://localhost:8000",
        "*"  # Remove this in production
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Security Setup
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_async_db)):
    """Get current user from JWT token (async)"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, security.SECRET_KEY, algorithms=[security.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = schemas.TokenData(email=email)
    except JWTError as e:
        logger.warning(f"JWT decode error: {e}")
        raise credentials_exception
    
    user = await get_user_by_email(db, email=token_data.email)
    if user is None:
        logger.warning(f"User not found for email: {token_data.email}")
        raise credentials_exception
    return user

# --- Authentication Endpoints ---
@app.post("/users/register", response_model=schemas.User, tags=["Authentication"])
async def register_user(user: schemas.UserCreate, db: AsyncSession = Depends(get_async_db)):
    """Register a new user account (async)"""
    try:
        logger.info(f"Registration attempt for email: {user.email}")
        
        # Validate input data
        if not user.email or not user.email.strip():
            logger.warning("Registration failed: Empty email")
            raise HTTPException(status_code=400, detail="Email is required")
        
        if not user.password or len(user.password) < 6:
            logger.warning("Registration failed: Invalid password")
            raise HTTPException(status_code=400, detail="Password must be at least 6 characters long")
        
        # Check if user already exists
        db_user = await get_user_by_email(db, email=user.email.strip().lower())
        if db_user:
            logger.warning(f"Registration failed: Email already exists: {user.email}")
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Create the user
        logger.info("Creating new user...")
        db_user = await create_user(db=db, user=user)
        logger.info(f"User created successfully with ID: {db_user.id}")
        
        return db_user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during registration: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error during registration")

@app.post("/token", response_model=schemas.Token, tags=["Authentication"])
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_async_db)):
    """Login with email and password to get an access token (async)"""
    try:
        logger.info(f"Login attempt for user: {form_data.username}")
        
        user = await get_user_by_email(db, email=form_data.username.strip().lower())
        if not user:
            logger.warning(f"Login failed: User not found: {form_data.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not security.verify_password(form_data.password, user.hashed_password):
            logger.warning(f"Login failed: Incorrect password for user: {form_data.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password", 
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        access_token = security.create_access_token(data={"sub": user.email})
        logger.info(f"Login successful for user: {form_data.username}")
        return {"access_token": access_token, "token_type": "bearer"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during login: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error during login")

# --- User Profile Endpoints ---
@app.get("/users/me", response_model=schemas.User, tags=["User Profile"])
async def read_users_me(current_user: models.User = Depends(get_current_user)):
    """Get the profile of the currently logged-in user"""
    return current_user

@app.put("/users/me", response_model=schemas.User, tags=["User Profile"])
async def update_users_me(
    user_update: schemas.UserUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(get_current_user)
):
    """Update the profile of the currently logged-in user (async)"""
    try:
        updated_user = await update_user(db=db, user=current_user, update_data=user_update)
        logger.info(f"User profile updated for user ID: {current_user.id}")
        return updated_user
    except Exception as e:
        logger.error(f"Error updating user profile: {str(e)}")
        raise HTTPException(status_code=500, detail="Error updating user profile")

@app.get("/users/me/stats", tags=["User Profile"])
async def get_user_statistics(
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get user statistics (async)"""
    try:
        stats = await get_user_stats(db=db, user_id=current_user.id)
        return stats
    except Exception as e:
        logger.error(f"Error getting user stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Error retrieving user statistics")

# --- Itinerary Engine Endpoints ---
@app.post("/itineraries/", response_model=schemas.Itinerary, tags=["Itinerary Engine"])
async def create_itinerary_endpoint(
    itinerary: schemas.ItineraryCreate, 
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(get_current_user)
):
    """Creates a new, empty itinerary for the currently logged-in user (async)"""
    try:
        new_itinerary = await create_itinerary(db=db, itinerary=itinerary, owner_id=current_user.id)
        logger.info(f"Created new itinerary ID: {new_itinerary.id} for user ID: {current_user.id}")
        return new_itinerary
    except Exception as e:
        logger.error(f"Error creating itinerary: {str(e)}")
        raise HTTPException(status_code=500, detail="Error creating itinerary")

@app.get("/itineraries/", response_model=List[schemas.Itinerary], tags=["Itinerary Engine"])
async def get_user_itineraries(
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(get_current_user)
):
    """Gets all itineraries for the currently logged-in user (async)"""
    try:
        itineraries = await get_itineraries_by_owner(db=db, owner_id=current_user.id)
        logger.info(f"Retrieved {len(itineraries)} itineraries for user ID: {current_user.id}")
        return itineraries
    except Exception as e:
        logger.error(f"Error retrieving itineraries: {str(e)}")
        raise HTTPException(status_code=500, detail="Error retrieving itineraries")

@app.get("/itineraries/{itinerary_id}", response_model=schemas.Itinerary, tags=["Itinerary Engine"])
async def get_itinerary_endpoint(
    itinerary_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get a specific itinerary by ID (async)"""
    db_itinerary = await get_itinerary(db, itinerary_id=itinerary_id)
    if db_itinerary is None or db_itinerary.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Itinerary not found or access denied")
    return db_itinerary

@app.post("/itineraries/{itinerary_id}/legs/", response_model=schemas.Leg, tags=["Itinerary Engine"])
async def add_leg_to_itinerary(
    itinerary_id: int, 
    leg: schemas.LegCreate, 
    db: AsyncSession = Depends(get_async_db), 
    current_user: models.User = Depends(get_current_user)
):
    """Adds a travel leg to an existing itinerary (async)"""
    try:
        db_itinerary = await get_itinerary(db, itinerary_id=itinerary_id)
        if db_itinerary is None or db_itinerary.owner_id != current_user.id:
            raise HTTPException(status_code=404, detail="Itinerary not found or access denied")
        
        new_leg = await create_itinerary_leg(db=db, leg=leg, itinerary_id=itinerary_id)
        logger.info(f"Added leg to itinerary ID: {itinerary_id} for user ID: {current_user.id}")
        return new_leg
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding leg to itinerary: {str(e)}")
        raise HTTPException(status_code=500, detail="Error adding leg to itinerary")

@app.post("/itineraries/{itinerary_id}/generate-plan/", response_model=schemas.FullItineraryPlan, tags=["Itinerary Engine"])
async def generate_full_itinerary_plan(
    itinerary_id: int, 
    db: AsyncSession = Depends(get_async_db), 
    current_user: models.User = Depends(get_current_user)
):
    """Generate a complete travel plan for an itinerary including sponsorship offers (async)"""
    try:
        logger.info(f"Generating plan for itinerary ID: {itinerary_id}, user ID: {current_user.id}")
        
        db_itinerary = await get_itinerary(db, itinerary_id=itinerary_id)
        if db_itinerary is None or db_itinerary.owner_id != current_user.id:
            raise HTTPException(status_code=404, detail="Itinerary not found or access denied")
        
        # Generate the full plan with enhanced error handling
        full_plan = await planner.create_full_itinerary_plan(db=db, itinerary=db_itinerary, user=current_user)
        
        logger.info(f"Plan generated successfully for itinerary ID: {itinerary_id}")
        return full_plan
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating itinerary plan: {str(e)}")
        raise HTTPException(status_code=500, detail="Error generating travel plan")

# --- Visa & Country Management Endpoints ---
@app.post("/visa/", response_model=schemas.Country, tags=["Visa & Country Management"])
async def create_new_country(country: schemas.CountryCreate, db: AsyncSession = Depends(get_async_db)):
    """Add a new country with visa information (async)"""
    try:
        db_country = await get_country_by_code(db, country_code=country.code)
        if db_country:
            raise HTTPException(status_code=400, detail="Country with this code already exists")
        
        new_country = await create_country(db=db, country=country)
        logger.info(f"Created new country: {new_country.name} ({new_country.code})")
        return new_country
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating country: {str(e)}")
        raise HTTPException(status_code=500, detail="Error creating country")

@app.get("/visa/{country_code}", response_model=schemas.Country, tags=["Visa & Country Management"])
async def get_visa_info(country_code: str, db: AsyncSession = Depends(get_async_db)):
    """Get visa information for a specific country (async)"""
    try:
        db_country = await get_country_by_code(db, country_code=country_code.upper())
        if db_country is None:
            raise HTTPException(status_code=404, detail="Country data not found")
        return db_country
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving visa info: {str(e)}")
        raise HTTPException(status_code=500, detail="Error retrieving visa information")

# --- External Integrations Endpoints ---
@app.get("/flights/{airline_code}", response_model=List[schemas.FlightData], tags=["External Integrations"])
async def get_flights_for_airline(airline_code: str):
    """Get available flights for a specific airline"""
    try:
        flight_results = await flights.search_flights_by_airline(airline_code=airline_code)
        if not flight_results:
            raise HTTPException(status_code=404, detail="No flights found for this airline")
        return flight_results
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching flights: {str(e)}")
        raise HTTPException(status_code=500, detail="Error searching flights")

# --- API Status Endpoints ---
@app.get("/api/status", tags=["System"])
async def get_api_status():
    """Get the current status of external API integrations"""
    try:
        status = planner.get_api_status()
        # Test database connection
        db_status = await test_database_connection()
        return {
            "timestamp": datetime.now().isoformat(),
            "database_connected": db_status,
            "external_apis": status
        }
    except Exception as e:
        logger.error(f"Error getting API status: {str(e)}")
        return {
            "timestamp": datetime.now().isoformat(),
            "database_connected": False,
            "external_apis": {"error": str(e)}
        }

@app.post("/api/reset-quota", tags=["System"])
async def reset_api_quota():
    """Reset API quota status (admin function)"""
    try:
        planner.reset_all_quota_status()
        logger.info("API quota status reset successfully")
        return {"message": "API quota status reset successfully"}
    except Exception as e:
        logger.error(f"Error resetting API quota: {str(e)}")
        raise HTTPException(status_code=500, detail="Error resetting API quota")

# --- Health Check ---
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint with database status"""
    try:
        db_status = await test_database_connection()
        return {
            "status": "healthy",
            "message": "Nomad's Compass API is running",
            "timestamp": datetime.now().isoformat(),
            "version": "3.2.0",
            "database_connected": db_status,
            "async_enabled": True
        }
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return {
            "status": "degraded",
            "message": "API running with limited functionality",
            "timestamp": datetime.now().isoformat(),
            "version": "3.2.0",
            "database_connected": False,
            "async_enabled": True,
            "error": str(e)
        }

@app.get("/", tags=["Health"])
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to Nomad's Compass API",
        "version": "3.2.0",
        "docs": "/docs",
        "health": "/health",
        "features": ["async_database", "jwt_auth", "external_apis"]
    }

# Global exception handler
@app.exception_handler(500)
async def internal_server_error_handler(request, exc):
    logger.error(f"Internal server error: {exc}")
    return HTTPException(status_code=500, detail="Internal server error")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")