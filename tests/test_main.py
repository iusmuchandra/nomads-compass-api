import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

# Import your app and modules
from app.async_main import app
from app import async_crud, schemas, security

# By marking classes, we avoid applying the asyncio mark to synchronous tests
@pytest.mark.asyncio
class TestHealthEndpoints:
    """Test basic health and status endpoints"""

    async def test_health_check(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data

    async def test_root_endpoint(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert data["version"] == "3.2.0"

@pytest.fixture
def test_user_data():
    """Sample user data for testing"""
    return {
        "email": "testuser@example.com",
        "password": "testpassword123",
        "instagram_handle": "test_handle"
    }

@pytest.fixture
async def auth_headers(async_session: AsyncSession, test_user_data: dict):
    """Create a test user and return auth headers"""
    user_in = schemas.UserCreate(**test_user_data)
    await async_crud.create_user(db=async_session, user=user_in)

    login_data = {
        "username": test_user_data["email"],
        "password": test_user_data["password"]
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/token", data=login_data)
    
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

@pytest.mark.asyncio
class TestAuthentication:
    """Test user authentication endpoints"""

    async def test_user_registration_success(self):
        # Use a unique email for this specific test to guarantee it doesn't already exist
        unique_user_data = {
            "email": "success_user@example.com",
            "password": "password123",
            "instagram_handle": "success_handle"
        }
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post("/users/register", json=unique_user_data)
        
        # Add a print statement to see the API response if the test fails
        if response.status_code != 200:
            print(f"Registration failed with response: {response.json()}")

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == unique_user_data["email"]

    async def test_user_registration_duplicate_email(self, async_session: AsyncSession, test_user_data):
        user_in = schemas.UserCreate(**test_user_data)
        await async_crud.create_user(db=async_session, user=user_in)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post("/users/register", json=test_user_data)
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"]

    async def test_login_success(self, async_session: AsyncSession, test_user_data):
        user_in = schemas.UserCreate(**test_user_data)
        await async_crud.create_user(db=async_session, user=user_in)

        login_data = { "username": test_user_data["email"], "password": test_user_data["password"] }
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post("/token", data=login_data)
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
    
    async def test_get_current_user(self, auth_headers, test_user_data):
        headers = await auth_headers
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get("/users/me", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user_data["email"]

@pytest.mark.asyncio
class TestItineraryEngine:
    """Test itinerary management endpoints"""

    async def test_create_itinerary(self, auth_headers):
        itinerary_data = {"name": "Test Trip"}
        headers = await auth_headers
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post("/itineraries/", json=itinerary_data, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Trip"

    async def test_add_leg_and_generate_plan(self, auth_headers):
        itinerary_data = {"name": "Test Trip"}
        headers = await auth_headers
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post("/itineraries/", json=itinerary_data, headers=headers)
            itinerary_id = response.json()["id"]

            leg_data = { "origin_airport": "DEL", "destination_airport": "BKK", "travel_date": "2025-12-01" }
            response = await ac.post(f"/itineraries/{itinerary_id}/legs/", json=leg_data, headers=headers)
            assert response.status_code == 200

            response = await ac.post(f"/itineraries/{itinerary_id}/generate-plan/", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "itinerary_details" in data

@pytest.mark.asyncio
class TestCRUDOperations:
    """Test direct async database CRUD operations"""

    async def test_create_user(self, async_session: AsyncSession):
        user_data = schemas.UserCreate(email="crud@test.com", password="testpass123")
        db_user = await async_crud.create_user(db=async_session, user=user_data)
        assert db_user.email == "crud@test.com"
        assert db_user.id is not None

    async def test_get_user_by_email(self, async_session: AsyncSession):
        user_data = schemas.UserCreate(email="getuser@test.com", password="testpass123")
        await async_crud.create_user(db=async_session, user=user_data)
        
        db_user = await async_crud.get_user_by_email(db=async_session, email="getuser@test.com")
        assert db_user is not None
        assert db_user.email == "getuser@test.com"

class TestSecurity:
    """Test security functions (these are synchronous)"""

    def test_password_hashing(self):
        password = "testpassword123"
        hashed = security.get_password_hash(password)
        assert hashed != password
        assert security.verify_password(password, hashed)