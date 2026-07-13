import pytest
from app import app, db
from models import User, Conversation

@pytest.fixture
def client():
    # Setup in-memory test database for authentication tests
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['JWT_SECRET_KEY'] = 'test-secret-key'
    
    with app.app_context():
        db.create_all()
        yield app.test_client()
        db.drop_all()

def test_auth_registration_success(client):
    """Verifies that user registration succeeds and auto-creates a default conversation."""
    resp = client.post('/api/auth/register', json={
        'username': 'operator',
        'password': 'securepassword'
    })
    assert resp.status_code == 201
    assert b"registered successfully" in resp.data
    
    # Check if conversation was created in DB
    with app.app_context():
        user = User.query.filter_by(username='operator').first()
        assert user is not None
        assert len(user.conversations) == 1
        assert user.conversations[0].title == "Initial Chat"

def test_auth_registration_duplicate(client):
    """Verifies duplicate codenames are rejected."""
    client.post('/api/auth/register', json={
        'username': 'operator',
        'password': 'securepassword'
    })
    resp = client.post('/api/auth/register', json={
        'username': 'operator',
        'password': 'differentpassword'
    })
    assert resp.status_code == 400
    assert b"already taken" in resp.data

def test_auth_login_success(client):
    """Verifies valid password returns JWT token."""
    client.post('/api/auth/register', json={
        'username': 'operator',
        'password': 'securepassword'
    })
    
    resp = client.post('/api/auth/login', json={
        'username': 'operator',
        'password': 'securepassword'
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'token' in data
    assert data['user']['username'] == 'operator'

def test_auth_login_failure(client):
    """Verifies incorrect passwords and users are rejected."""
    client.post('/api/auth/register', json={
        'username': 'operator',
        'password': 'securepassword'
    })
    
    # Wrong password
    resp = client.post('/api/auth/login', json={
        'username': 'operator',
        'password': 'wrongpassword'
    })
    assert resp.status_code == 401
    assert b"Invalid username or password" in resp.data
    
    # Non-existent user
    resp = client.post('/api/auth/login', json={
        'username': 'nonexistent',
        'password': 'securepassword'
    })
    assert resp.status_code == 401
