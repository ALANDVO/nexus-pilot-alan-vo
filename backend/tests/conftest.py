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
        env="testing",
        secret_key="test-secret",
        api_host="127.0.1",
        api_port=8000,
        frontend_url="http://127.0.0.1:5173",
        database_url=TEST_DATABASE_URL,
        keycloak_url="http://127.0.0.1:8080",
        keycloak_realm="nexus-pilot",
        keycloak_client_id="nexus-pilot-client",
        keycloak_client_secret="test-secret",
        keycloak_admin_user="admin",
        keycloak_admin_password="admin",
        max_step_size_mb=500,
        memory_envelope_mb=1024,
    )


@pytest_asyncio.fixture(scope="function")
async def db_engine():
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        future=True,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
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
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def test_user(db_session):
    user = User(
        keycloak_sub="test-sub-123",
        email="test@example.com",
        username="testuser",
        roles=["operator", "viewer"],
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture(scope="function")
async def test_part(db_session, test_user):
    part = Part(
        owner_id=test_user.id,
        filename="test_part.step",
        original_filename="test_part.step",
        content_type="application/step",
        file_size=1024,
        file_path="/tmp/test_part.step",
        status=PartStatus.READY,
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
            "realm_access": {"roles": ["operator", "viewer"]},
        }
    monkeypatch.setattr(token_validator, "validate_token", mock_validate)