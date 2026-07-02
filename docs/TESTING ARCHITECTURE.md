1. Testing Strategy
1.1 Testing Pyramid
┌─────────────────────────────────────────────────────────────────────────────┐
│                    TESTING PYRAMID                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│                          ┌─────────────┐                                   │
│                         /   E2E Tests  \                                   │
│                        /   (UI, API)    \                                  │
│                       /    (Few)         \                                 │
│                      ┌─────────────────────┐                                │
│                     /   Integration Tests   \                              │
│                    /    (Component, API)    \                             │
│                   /     (Some)               \                            │
│                  ┌───────────────────────────────┐                         │
│                 /       Unit Tests                \                        │
│                /      (Fast, Many)                 \                       │
│               /                                    \                      │
│              ┌─────────────────────────────────────────┐                   │
│              │         Performance Tests               │                   │
│              │    (Load, Stress, Scalability)          │                   │
│              └─────────────────────────────────────────┘                   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
1.2 Test Categories
Test Categories:
  Unit Tests:
    - Individual functions and methods
    - Mocked dependencies
    - Fast execution (<100ms each)
    - 90%+ coverage target
    - Run on every commit
    
  Integration Tests:
    - Database interactions
    - API endpoints
    - External service integrations
    - Real dependencies (test databases)
    - Run on every PR
    
  E2E Tests:
    - Full user journeys
    - Complete system flow
    - Real browser simulation
    - Run nightly
    - Critical path coverage
    
  Performance Tests:
    - Load testing (1000 req/sec)
    - Stress testing (200% capacity)
    - Scalability testing (horizontal)
    - Database performance
    - Run weekly
    
  Security Tests:
    - Vulnerability scanning
    - Penetration testing
    - Dependency security
    - Static code analysis
    - Run daily
	
2. Unit Testing
2.1 Pytest Configuration
# pytest.ini
[pytest]
minversion = 7.0
testpaths = tests/unit
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    -v
    --strict-markers
    --tb=short
    --cov=src
    --cov-report=term
    --cov-report=html
    --cov-report=xml
markers =
    unit: Unit tests
    integration: Integration tests
    e2e: End-to-end tests
    slow: Slow tests
    performance: Performance tests
	
2.2 Unit Test Examples
# tests/unit/test_search_service.py
import pytest
from unittest.mock import Mock, AsyncMock
from services.search_service import SearchService
from models.search import SearchRequest, SearchResult

@pytest.fixture
def mock_repositories():
    return {
        'search_repo': Mock(),
        'embedding_service': Mock(),
        'cache_service': Mock(),
        'scoring_service': Mock()
    }

@pytest.fixture
def search_service(mock_repositories):
    return SearchService(**mock_repositories)

class TestSearchService:
    
    @pytest.mark.unit
    async def test_search_returns_results(self, search_service, mock_repositories):
        # Arrange
        query = "data science jobs in Germany"
        filters = {"domain": "jobs", "country": "Germany"}
        user_id = "test_user"
        
        mock_repositories['search_repo'].vector_search = AsyncMock(
            return_value=[{"id": "1", "title": "Data Scientist"}]
        )
        mock_repositories['search_repo'].keyword_search = AsyncMock(
            return_value=[{"id": "2", "title": "ML Engineer"}]
        )
        mock_repositories['scoring_service'].score_results = AsyncMock(
            return_value=SearchResult(
                items=[{"id": "1", "score": 0.95}, {"id": "2", "score": 0.85}],
                total=2
            )
        )
        
        # Act
        result = await search_service.search(query, filters, user_id)
        
        # Assert
        assert len(result.items) == 2
        assert result.total == 2
        assert result.items[0]['score'] == 0.95
        
    @pytest.mark.unit
    async def test_search_caches_results(self, search_service, mock_repositories):
        # Arrange
        query = "test query"
        filters = {}
        user_id = "test_user"
        
        # Mock cache hit
        mock_repositories['cache_service'].get = AsyncMock(
            return_value=SearchResult(items=[{"id": "1"}], total=1).to_dict()
        )
        
        # Act
        result = await search_service.search(query, filters, user_id)
        
        # Assert
        assert len(result.items) == 1
        mock_repositories['search_repo'].vector_search.assert_not_called()
        
    @pytest.mark.unit
    async def test_search_handles_empty_results(self, search_service, mock_repositories):
        # Arrange
        query = "nonexistent query"
        filters = {}
        user_id = "test_user"
        
        mock_repositories['search_repo'].vector_search = AsyncMock(return_value=[])
        mock_repositories['search_repo'].keyword_search = AsyncMock(return_value=[])
        mock_repositories['scoring_service'].score_results = AsyncMock(
            return_value=SearchResult(items=[], total=0)
        )
        
        # Act
        result = await search_service.search(query, filters, user_id)
        
        # Assert
        assert len(result.items) == 0
        assert result.total == 0
        
    @pytest.mark.unit
    async def test_search_error_handling(self, search_service, mock_repositories):
        # Arrange
        query = "test query"
        filters = {}
        user_id = "test_user"
        
        mock_repositories['search_repo'].vector_search = AsyncMock(
            side_effect=Exception("Database error")
        )
        
        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            await search_service.search(query, filters, user_id)
        assert "Database error" in str(exc_info.value)
3. Integration Testing
3.1 API Integration Tests
# tests/integration/test_api.py
import pytest
from fastapi.testclient import TestClient
from main import app
from database import SessionLocal
from models import User

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def db_session():
    session = SessionLocal()
    yield session
    session.close()

@pytest.fixture
def test_user(db_session):
    user = User(
        email="test@example.com",
        full_name="Test User",
        password_hash="hashed_password"
    )
    db_session.add(user)
    db_session.commit()
    return user

@pytest.mark.integration
class TestAuthAPI:
    
    def test_register_user(self, client):
        # Arrange
        data = {
            "email": "new@example.com",
            "password": "SecurePassword123!",
            "full_name": "New User"
        }
        
        # Act
        response = client.post("/api/v1/auth/register", json=data)
        
        # Assert
        assert response.status_code == 200
        assert response.json()["email"] == data["email"]
        assert "user_id" in response.json()
        
    def test_login_user(self, client, test_user):
        # Arrange
        data = {
            "email": test_user.email,
            "password": "testpassword"
        }
        
        # Act
        response = client.post("/api/v1/auth/login", json=data)
        
        # Assert
        assert response.status_code == 200
        assert "access_token" in response.json()
        assert "refresh_token" in response.json()
        
    def test_login_invalid_credentials(self, client):
        # Arrange
        data = {
            "email": "wrong@example.com",
            "password": "wrongpassword"
        }
        
        # Act
        response = client.post("/api/v1/auth/login", json=data)
        
        # Assert
        assert response.status_code == 401
        assert "Invalid credentials" in response.json()["detail"]

@pytest.mark.integration
class TestSearchAPI:
    
    def test_search_requires_auth(self, client):
        # Act
        response = client.post("/api/v1/search", json={"query": "test"})
        
        # Assert
        assert response.status_code == 401
        
    def test_search_with_auth(self, client, test_user):
        # Arrange
        # Login to get token
        login_response = client.post("/api/v1/auth/login", json={
            "email": test_user.email,
            "password": "testpassword"
        })
        token = login_response.json()["access_token"]
        
        # Act
        response = client.post(
            "/api/v1/search",
            json={"query": "test search"},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # Assert
        assert response.status_code == 200
        assert "results" in response.json()
        assert "pagination" in response.json()

4. E2E Testing
4.1 Playwright Tests
// tests/e2e/auth.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Authentication Flow', () => {
  test('should register new user', async ({ page }) => {
    await page.goto('/register');
    
    // Fill registration form
    await page.fill('[name="email"]', 'e2e-test@example.com');
    await page.fill('[name="password"]', 'SecurePassword123!');
    await page.fill('[name="full_name"]', 'E2E Test User');
    await page.click('button[type="submit"]');
    
    // Wait for redirect
    await page.waitForURL('/login?registered=true');
    
    // Verify registration success message
    await expect(page.locator('.alert-success')).toHaveText(
      'Account created successfully! Please login.'
    );
  });
  
  test('should login and access dashboard', async ({ page }) => {
    // Navigate to login page
    await page.goto('/login');
    
    // Fill login form
    await page.fill('[name="email"]', 'test@example.com');
    await page.fill('[name="password"]', 'testpassword');
    await page.click('button[type="submit"]');
    
    // Wait for redirect
    await page.waitForURL('/dashboard');
    
    // Verify dashboard loaded
    await expect(page.locator('h1')).toHaveText('Welcome back, Test User!');
    await expect(page.locator('.dashboard-stats')).toBeVisible();
  });
  
  test('should perform search', async ({ page }) => {
    // Login first
    await page.goto('/login');
    await page.fill('[name="email"]', 'test@example.com');
    await page.fill('[name="password"]', 'testpassword');
    await page.click('button[type="submit"]');
    await page.waitForURL('/dashboard');
    
    // Perform search
    await page.fill('.search-input', 'data science jobs');
    await page.press('.search-input', 'Enter');
    
    // Wait for results
    await page.waitForSelector('.search-results');
    
    // Verify results
    const results = await page.locator('.search-result-item').count();
    expect(results).toBeGreaterThan(0);
  });
  
  test('should save opportunity', async ({ page }) => {
    // Login and search
    await page.goto('/login');
    await page.fill('[name="email"]', 'test@example.com');
    await page.fill('[name="password"]', 'testpassword');
    await page.click('button[type="submit"]');
    await page.waitForURL('/dashboard');
    
    await page.fill('.search-input', 'data science jobs');
    await page.press('.search-input', 'Enter');
    await page.waitForSelector('.search-result-item');
    
    // Save first result
    const saveButton = page.locator('.save-opportunity-button').first();
    await saveButton.click();
    
    // Wait for save confirmation
    await expect(page.locator('.save-success')).toBeVisible();
    
    // Navigate to saved opportunities
    await page.click('a[href="/saved"]');
    await page.waitForURL('/saved');
    
    // Verify opportunity is saved
    await expect(page.locator('.saved-opportunity')).toBeVisible();
  });
});

5. Performance Testing
5.1 Locust Load Tests
# tests/performance/locustfile.py
from locust import HttpUser, task, between
import random
import json

class WildAutomationsUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        """Login on start"""
        self.login()
    
    def login(self):
        """Login to get token"""
        response = self.client.post("/api/v1/auth/login", json={
            "email": f"test{random.randint(1, 1000)}@example.com",
            "password": "testpassword"
        })
        
        if response.status_code == 200:
            self.token = response.json()["access_token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            # Register if login fails
            self.client.post("/api/v1/auth/register", json={
                "email": f"test{random.randint(1, 1000)}@example.com",
                "password": "testpassword",
                "full_name": "Test User"
            })
            self.login()
    
    @task(3)
    def search(self):
        """Perform search"""
        queries = [
            "data science jobs",
            "apartment for rent",
            "Toyota Corolla",
            "scholarships for international students",
            "visa sponsorship"
        ]
        
        self.client.post(
            "/api/v1/search",
            json={
                "query": random.choice(queries),
                "filters": {
                    "domains": ["jobs", "real_estate", "vehicles"],
                    "limit": 20
                }
            },
            headers=self.headers
        )
    
    @task(2)
    def get_opportunities(self):
        """Get opportunities"""
        self.client.get(
            "/api/v1/opportunities",
            headers=self.headers
        )
    
    @task(1)
    def get_profile(self):
        """Get user profile"""
        self.client.get(
            "/api/v1/profile",
            headers=self.headers
        )
    
    @task(1)
    def update_preferences(self):
        """Update preferences"""
        self.client.put(
            "/api/v1/profile/preferences",
            json={
                "domains": ["jobs", "real_estate"],
                "notifications": {"enabled": True}
            },
            headers=self.headers
        )
		
5.2 Load Test Configuration
# tests/performance/locust.conf
locustfile = tests/performance/locustfile.py
host = https://api.wildautomations.io
users = 1000
spawn_rate = 10
run_time = 1h
html = reports/performance_report.html
csv = reports/performance_metrics