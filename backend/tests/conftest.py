import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.session import Base, get_db
from app.models.user import User
from app.models.part import Part, PartStatus
from app.models.unfold import UnfoldJob, UnfoldResult, BendRecord, UnfoldJobStatus
from app.core.config import Settings
from app.core.auth import token_validator


# Test database URL (in-memory SQLite)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def test_settings():
    return Settings(
        ENV="testing",
        SECRET_KEY="test-secret",
        DATABASE_URL=TEST_DATABASE_URL,
        KEYCLOAK_URL="http://localhost:8080",
        KEYCLOAK_REALM="test",
        KEYCLOAK_CLIENT_ID="test-client",
        KEYCLOAK_CLIENT_SECRET="test-secret",
        FRONTEND_URL="http://localhost:5173"
    )


@pytest_asyncio.fixture(scope="function")
async def db_engine():
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine):
    async_session = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def test_user(db_session):
    user = User(
        keycloak_sub="test-sub-123",
        email="test@example.com",
        username="testuser",
        roles=["viewer", "operator"]
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture(scope="function")
async def test_part(db_session, test_user):
    part = Part(
        owner_id=test_user.id,
        filename="test.step",
        original_filename="test.step",
        content_type="application/step",
        file_size=1024,
        file_path="/tmp/test.step",
        status=PartStatus.READY,
        metadata_={"volume": 1000.0, "face_count": 10}
    )
    db_session.add(part)
    await db_session.commit()
    await db_session.refresh(part)
    return part


@pytest.fixture
def mock_token_validator(monkeypatch):
    """Mock token validation for testing."""
    async def mock_validate(token: str):
        return {
            "sub": "test-sub-123",
            "email": "test@example.com",
            "preferred_username": "testuser",
            "realm_access": {"roles": ["viewer", "operator"]},
            "aud": "test-client",
            "iss": "http://localhost:8080/realms/test"
        }

    monkeypatch.setattr(token_validator, "validate_token", mock_validate)