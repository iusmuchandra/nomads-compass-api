# In app/models.py
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base

class Country(Base):
    __tablename__ = "countries"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    code = Column(String(3), unique=True, index=True)  # e.g., "THA"
    visa_policy = Column(String, default="Visa Required")
    processing_time_days = Column(Integer, default=14)

    requirements = relationship("VisaRequirement", back_populates="country")

class VisaRequirement(Base):
    __tablename__ = "visa_requirements"

    id = Column(Integer, primary_key=True, index=True)
    document_name = Column(String, index=True)
    description = Column(String)
    is_mandatory = Column(Boolean, default=True)
    country_id = Column(Integer, ForeignKey("countries.id"))

    country = relationship("Country", back_populates="requirements")