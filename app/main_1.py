import time
import logging
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
from jose import JWTError, jwt
from sqlalchemy.exc import OperationalError
from datetime import datetime

import models
import schemas
import crud
import flights
import planner
import security
import sponsorship
from database import engine, get_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize the database with retry logic
def initialize_database():
    max_retries = 5
    retry_delay = 2  # seconds
    
    for attempt in range(max_retries):
        try:
            models.Base.metadata.create_all(bind=engine)
            logger.info("Database tables created successfully.")
            return True
        except OperationalError as e:
            if attempt < max_retries - 1:
                logger.warning(f"Database connection failed (attempt {attempt + 1}/{max_retries}). Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                logger.error(f"Failed to connect to database after {max_retries} attempts: {e}")
                logger.warning("Application will start without database functionality.")
                return False

# Initialize database with retry logic
database_initialized = initialize_database()

app = FastAPI(
    title="Nomad's Compass API",
    description="The core engine for the world's smartest travel agent with AI-powered itinerary planning.",
    version="3.1.0",  # Version bump for enhanced error handling and API quota management
    contact={
        "name": "Nomad's Compass Support",
        "email": "support@nomadscompass.com",
    },
    license_info={
        "name": "MIT",
    },
)

# CORS MIDDLEWARE - More restrictive for production
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React dev server
        "http://localhost:8080",  # Vue dev server
        "http://127.0.0.1:8000",  # FastAPI docs
        "http://localhost:8000",  # FastAPI docs
        "*"  # Remove this in production and add your actual domains
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# --- Security Setup & Dependency ---
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
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
    
    user = crud.get_user_by_email(db, email=token_data.email)
    if user is None:
        logger.warning(f"User not found for email: {token_data.email}")
        raise credentials_exception
    return user

# --- Authentication Endpoints ---
@app.post("/users/register", response_model=schemas.User, tags=["Authentication"])
async def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    """Register a new user account"""
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
        db_user = crud.get_user_by_email(db, email=user.email.strip().lower())
        if db_user:
            logger.warning(f"Registration failed: Email already exists: {user.email}")
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Create the user
        logger.info("Creating new user...")
        db_user = crud.create_user(db=db, user=user)
        logger.info(f"User created successfully with ID: {db_user.id}")
        
        return db_user
        
    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except Exception as e:
        logger.error(f"Unexpected error during registration: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error during registration")

@app.post("/token", response_model=schemas.Token, tags=["Authentication"])
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Login with email and password to get an access token"""
    try:
        logger.info(f"Login attempt for user: {form_data.username}")
        
        user = crud.get_user_by_email(db, email=form_data.username.strip().lower())
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
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Update the profile of the currently logged-in user"""
    try:
        updated_user = crud.update_user(db=db, user=current_user, update_data=user_update)
        logger.info(f"User profile updated for user ID: {current_user.id}")
        return updated_user
    except Exception as e:
        logger.error(f"Error updating user profile: {str(e)}")
        raise HTTPException(status_code=500, detail="Error updating user profile")

# --- Itinerary Engine Endpoints (Protected) ---
@app.post("/itineraries/", response_model=schemas.Itinerary, tags=["Itinerary Engine"])
async def create_itinerary(
    itinerary: schemas.ItineraryCreate, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Creates a new, empty itinerary for the currently logged-in user"""
    try:
        new_itinerary = crud.create_itinerary(db=db, itinerary=itinerary, owner_id=current_user.id)
        logger.info(f"Created new itinerary ID: {new_itinerary.id} for user ID: {current_user.id}")
        return new_itinerary
    except Exception as e:
        logger.error(f"Error creating itinerary: {str(e)}")
        raise HTTPException(status_code=500, detail="Error creating itinerary")

@app.get("/itineraries/", response_model=List[schemas.Itinerary], tags=["Itinerary Engine"])
async def get_user_itineraries(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Gets all itineraries for the currently logged-in user"""
    try:
        itineraries = crud.get_itineraries_by_owner(db=db, owner_id=current_user.id)
        logger.info(f"Retrieved {len(itineraries)} itineraries for user ID: {current_user.id}")
        return itineraries
    except Exception as e:
        logger.error(f"Error retrieving itineraries: {str(e)}")
        raise HTTPException(status_code=500, detail="Error retrieving itineraries")

@app.get("/itineraries/{itinerary_id}", response_model=schemas.Itinerary, tags=["Itinerary Engine"])
async def get_itinerary(
    itinerary_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get a specific itinerary by ID"""
    db_itinerary = crud.get_itinerary(db, itinerary_id=itinerary_id)
    if db_itinerary is None or db_itinerary.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Itinerary not found or access denied")
    return db_itinerary

@app.post("/itineraries/{itinerary_id}/legs/", response_model=schemas.Leg, tags=["Itinerary Engine"])
async def add_leg_to_itinerary(
    itinerary_id: int, 
    leg: schemas.LegCreate, 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(get_current_user)
):
    """Adds a travel leg to an existing itinerary"""
    try:
        db_itinerary = crud.get_itinerary(db, itinerary_id=itinerary_id)
        if db_itinerary is None or db_itinerary.owner_id != current_user.id:
            raise HTTPException(status_code=404, detail="Itinerary not found or access denied")
        
        new_leg = crud.create_itinerary_leg(db=db, leg=leg, itinerary_id=itinerary_id)
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
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(get_current_user)
):
    """Generate a complete travel plan for an itinerary including sponsorship offers"""
    try:
        logger.info(f"Generating plan for itinerary ID: {itinerary_id}, user ID: {current_user.id}")
        
        db_itinerary = crud.get_itinerary(db, itinerary_id=itinerary_id)
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

@app.get("/itineraries/{itinerary_id}/plan", response_model=schemas.FullItineraryPlan, tags=["Itinerary Engine"])
async def get_full_itinerary_plan(
    itinerary_id: int, 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(get_current_user)
):
    """Retrieve an itinerary and generate a complete plan for all of its legs"""
    try:
        db_itinerary = crud.get_itinerary(db, itinerary_id=itinerary_id)
        if db_itinerary is None or db_itinerary.owner_id != current_user.id:
            raise HTTPException(status_code=404, detail="Itinerary not found or access denied")
        
        full_plan = await planner.create_full_itinerary_plan(db=db, itinerary=db_itinerary, user=current_user)
        return full_plan
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving itinerary plan: {str(e)}")
        raise HTTPException(status_code=500, detail="Error retrieving travel plan")

# --- API Status Endpoints ---
@app.get("/api/status", tags=["System"])
async def get_api_status():
    """Get the current status of external API integrations"""
    try:
        status = planner.get_api_status()
        return {
            "timestamp": datetime.now().isoformat(),
            "database_connected": database_initialized,
            "external_apis": status
        }
    except Exception as e:
        logger.error(f"Error getting API status: {str(e)}")
        return {
            "timestamp": datetime.now().isoformat(),
            "database_connected": database_initialized,
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

# --- Visa & Country Management Endpoints (Public) ---
@app.post("/visa/", response_model=schemas.Country, tags=["Visa & Country Management"])
async def create_new_country(country: schemas.CountryCreate, db: Session = Depends(get_db)):
    """Add a new country with visa information"""
    try:
        db_country = crud.get_country_by_code(db, country_code=country.code)
        if db_country:
            raise HTTPException(status_code=400, detail="Country with this code already exists")
        
        new_country = crud.create_country(db=db, country=country)
        logger.info(f"Created new country: {new_country.name} ({new_country.code})")
        return new_country
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating country: {str(e)}")
        raise HTTPException(status_code=500, detail="Error creating country")

@app.get("/visa/{country_code}", response_model=schemas.Country, tags=["Visa & Country Management"])
async def get_visa_info(country_code: str, db: Session = Depends(get_db)):
    """Get visa information for a specific country"""
    try:
        db_country = crud.get_country_by_code(db, country_code=country_code.upper())
        if db_country is None:
            raise HTTPException(status_code=404, detail="Country data not found")
        return db_country
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving visa info: {str(e)}")
        raise HTTPException(status_code=500, detail="Error retrieving visa information")

@app.put("/visa/{country_id}", response_model=schemas.Country, tags=["Visa & Country Management"])
async def update_country_info(country_id: int, country: schemas.CountryUpdate, db: Session = Depends(get_db)):
    """Update visa information for a country"""
    try:
        db_country = crud.update_country(db, country_id=country_id, country_update=country)
        if db_country is None:
            raise HTTPException(status_code=404, detail="Country not found")
        
        logger.info(f"Updated country ID: {country_id}")
        return db_country
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating country: {str(e)}")
        raise HTTPException(status_code=500, detail="Error updating country information")

@app.delete("/visa/{country_id}", response_model=dict, tags=["Visa & Country Management"])
async def delete_country_info(country_id: int, db: Session = Depends(get_db)):
    """Delete a country's visa information"""
    try:
        db_country = crud.delete_country(db, country_id=country_id)
        if db_country is None:
            raise HTTPException(status_code=404, detail="Country not found")
        
        logger.info(f"Deleted country: {db_country.name}")
        return {"message": f"Country '{db_country.name}' deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting country: {str(e)}")
        raise HTTPException(status_code=500, detail="Error deleting country")

# --- External Integrations Endpoints (Public) ---
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

# --- Health Check ---
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "message": "Nomad's Compass API is running",
        "timestamp": datetime.now().isoformat(),
        "version": "3.1.0",
        "database_connected": database_initialized
    }

@app.get("/", tags=["Health"])
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to Nomad's Compass API",
        "version": "3.1.0",
        "docs": "/docs",
        "health": "/health"
    }

# Global exception handler
@app.exception_handler(500)
async def internal_server_error_handler(request, exc):
    logger.error(f"Internal server error: {exc}")
    return HTTPException(status_code=500, detail="Internal server error")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")