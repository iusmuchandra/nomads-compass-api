from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List
from jose import JWTError, jwt

from . import models, schemas, crud, flights, planner, security, sponsorship
from .database import engine, get_db

models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Nomad's Compass API",
    description="The core engine for the world's smartest travel agent.",
    version="3.0.0" # Version bump for Creator Connect
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
    except JWTError:
        raise credentials_exception
    user = crud.get_user_by_email(db, email=token_data.email)
    if user is None:
        raise credentials_exception
    return user

# --- Authentication Endpoints ---
@app.post("/users/register", response_model=schemas.User, tags=["Authentication"])
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    return crud.create_user(db=db, user=user)

@app.post("/token", response_model=schemas.Token, tags=["Authentication"])
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = crud.get_user_by_email(db, email=form_data.username)
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = security.create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

# --- User Profile Endpoints ---
@app.get("/users/me", response_model=schemas.User, tags=["User Profile"])
async def read_users_me(current_user: models.User = Depends(get_current_user)):
    """Get the profile of the currently logged-in user."""
    return current_user

@app.put("/users/me", response_model=schemas.User, tags=["User Profile"])
def update_users_me(
    user_update: schemas.UserUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Update the profile of the currently logged-in user."""
    return crud.update_user(db=db, user=current_user, update_data=user_update)

# --- Itinerary Engine Endpoints (Protected) ---
@app.post("/itineraries/", response_model=schemas.Itinerary, tags=["Itinerary Engine"])
def create_new_itinerary(
    itinerary: schemas.ItineraryCreate, 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(get_current_user)
):
    """Creates a new, empty itinerary for the currently logged-in user."""
    return crud.create_itinerary(db=db, itinerary=itinerary, owner_id=current_user.id)

@app.post("/itineraries/{itinerary_id}/legs/", response_model=schemas.Leg, tags=["Itinerary Engine"])
def add_leg_to_itinerary(
    itinerary_id: int, 
    leg: schemas.LegCreate, 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(get_current_user)
):
    """Adds a travel leg to an existing itinerary."""
    db_itinerary = crud.get_itinerary(db, itinerary_id=itinerary_id)
    if db_itinerary is None or db_itinerary.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Itinerary not found or you do not have permission to access it")
    return crud.create_itinerary_leg(db=db, leg=leg, itinerary_id=itinerary_id)

@app.get("/itineraries/{itinerary_id}/plan", response_model=schemas.FullItineraryPlan, tags=["Itinerary Engine"])
async def get_full_itinerary_plan(
    itinerary_id: int, 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(get_current_user)
):
    """
    Retrieves an itinerary and generates a complete plan for all of its legs,
    including potential sponsorship offers for the user.
    """
    db_itinerary = crud.get_itinerary(db, itinerary_id=itinerary_id)
    if db_itinerary is None or db_itinerary.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Itinerary not found or you do not have permission to access it")
    
    full_plan = await planner.create_full_itinerary_plan(db=db, itinerary=db_itinerary, user=current_user)
    return full_plan

# --- Visa & Flight Endpoints (Public) ---
@app.get("/visa/{country_code}", response_model=schemas.Country, tags=["Visa & Country Management"])
def get_visa_info(country_code: str, db: Session = Depends(get_db)):
    db_country = crud.get_country_by_code(db, country_code=country_code)
    if db_country is None:
        raise HTTPException(status_code=404, detail="Country data not found")
    return db_country

@app.get("/flights/{airline_code}", response_model=List[schemas.FlightData], tags=["External Integrations"])
async def get_flights_for_airline(airline_code: str):
    flight_results = await flights.search_flights_by_airline(airline_code=airline_code)
    if not flight_results:
        raise HTTPException(status_code=404, detail="No flights found for this airline.")
    return flight_results