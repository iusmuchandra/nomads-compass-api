# In seed.py

# --- NEW IMPORTS ---
from app.database import SessionLocal, engine, Base
from app.models import Country, VisaRequirement
# -----------------

def seed_database():
    # --- NEW LINE: This creates the tables. ---
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Tables created.")
    # ------------------------------------------

    db = SessionLocal()

    try:
        # Check if Thailand already exists to avoid duplicate entries
        thailand = db.query(Country).filter(Country.code == "THA").first()
        
        if not thailand:
            print("Seeding data for Thailand...")
            
            # Create the Country object
            thailand = Country(
                name="Thailand",
                code="THA",
                visa_policy="Visa on Arrival",
                processing_time_days=1
            )
            
            # Create the list of requirements
            requirements_data = [
                {"document_name": "Passport", "description": "Valid for at least 6 months"},
                {"document_name": "Return Flight Ticket", "description": "Proof of onward travel within 15 days"},
                {"document_name": "Proof of Accommodation", "description": "Hotel bookings for the duration of stay"},
                {"document_name": "Passport Size Photo", "description": "4x6 cm, white background, matte finish"},
                {"document_name": "Proof of Funds", "description": "10,000 THB per person or 20,000 THB per family"},
            ]

            # Create VisaRequirement objects and associate them with the country
            for req_data in requirements_data:
                requirement = VisaRequirement(**req_data)
                thailand.requirements.append(requirement)

            # Add the new country and its requirements to the session and commit
            db.add(thailand)
            db.commit()
            print("Thailand has been seeded successfully.")
        else:
            print("Thailand data already exists.")

    finally:
        db.close()

if __name__ == "__main__":
    seed_database()