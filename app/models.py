from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Date
from sqlalchemy.orm import relationship
from .async_database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    instagram_handle = Column(String, nullable=True)
    itineraries = relationship("Itinerary", back_populates="owner", cascade="all, delete-orphan")

class Country(Base):
    __tablename__ = "countries"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    code = Column(String(3), unique=True, index=True)
    visa_policy = Column(String, default="Visa Required")
    processing_time_days = Column(Integer, default=14)
    requirements = relationship("VisaRequirement", back_populates="country", cascade="all, delete-orphan")

class VisaRequirement(Base):
    __tablename__ = "visa_requirements"
    id = Column(Integer, primary_key=True, index=True)
    document_name = Column(String, index=True)
    description = Column(String, nullable=True)
    is_mandatory = Column(Boolean, default=True)
    country_id = Column(Integer, ForeignKey("countries.id"))
    country = relationship("Country", back_populates="requirements")

class Itinerary(Base):
    __tablename__ = "itineraries"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User", back_populates="itineraries")
    legs = relationship("Leg", back_populates="itinerary", cascade="all, delete-orphan", lazy="joined")  # Added lazy="joined"

class Leg(Base):
    __tablename__ = "legs"
    id = Column(Integer, primary_key=True, index=True)
    origin_airport = Column(String(3), index=True)
    destination_airport = Column(String(3), index=True)
    travel_date = Column(Date)
    itinerary_id = Column(Integer, ForeignKey("itineraries.id"))
    itinerary = relationship("Itinerary", back_populates="legs")