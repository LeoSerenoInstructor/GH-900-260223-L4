"""
Tests for the High School Management System API
"""

import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app import app

client = TestClient(app)


class TestRoot:
    """Tests for root endpoint"""
    
    def test_root_redirect(self):
        """Test that root redirects to static index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestGetActivities:
    """Tests for GET /activities endpoint"""
    
    def test_get_activities_success(self):
        """Test retrieving all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, dict)
        assert "Chess Club" in data
        assert "Basketball" in data
        assert "Soccer" in data
        
    def test_activity_structure(self):
        """Test that each activity has required fields"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity_data in data.items():
            assert "description" in activity_data
            assert "schedule" in activity_data
            assert "max_participants" in activity_data
            assert "participants" in activity_data
            assert isinstance(activity_data["participants"], list)
            
    def test_activities_count(self):
        """Test that there are 9 activities"""
        response = client.get("/activities")
        data = response.json()
        assert len(data) == 9


class TestSignupForActivity:
    """Tests for POST /activities/{activity_name}/signup endpoint"""
    
    def test_signup_success(self):
        """Test successful signup for an activity"""
        response = client.post(
            "/activities/Chess Club/signup",
            params={"email": "newstudent@mergington.edu"}
        )
        assert response.status_code == 200
        assert "Signed up" in response.json()["message"]
        
    def test_signup_nonexistent_activity(self):
        """Test signup for a non-existent activity"""
        response = client.post(
            "/activities/NonExistent/signup",
            params={"email": "student@mergington.edu"}
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "Activity not found"
        
    def test_signup_duplicate_email(self):
        """Test signup with email already registered"""
        # First signup
        client.post(
            "/activities/Biology Club/signup",
            params={"email": "test@mergington.edu"}
        )
        
        # Try to signup again with same email
        response = client.post(
            "/activities/Biology Club/signup",
            params={"email": "test@mergington.edu"}
        )
        assert response.status_code == 400
        assert "already signed up" in response.json()["detail"]
        
    def test_signup_activity_full(self):
        """Test signup when activity is at max capacity"""
        # Get an activity with low capacity
        activities_response = client.get("/activities")
        activities = activities_response.json()
        
        # Chess Club has max_participants: 5 and 2 already signed up
        # We'll need to fill it up
        for i in range(3):
            client.post(
                "/activities/Chess Club/signup",
                params={"email": f"fulltest{i}@mergington.edu"}
            )
        
        # Now try to signup when full
        response = client.post(
            "/activities/Chess Club/signup",
            params={"email": "another@mergington.edu"}
        )
        assert response.status_code == 400
        assert "full" in response.json()["detail"]


class TestRemoveParticipant:
    """Tests for POST /activities/{activity_name}/remove endpoint"""
    
    def test_remove_success(self):
        """Test successful removal of a participant"""
        # First signup
        client.post(
            "/activities/Physics Lab/signup",
            params={"email": "remove_test@mergington.edu"}
        )
        
        # Then remove
        response = client.post(
            "/activities/Physics Lab/remove",
            params={"email": "remove_test@mergington.edu"}
        )
        assert response.status_code == 200
        assert "Removed" in response.json()["message"]
        
    def test_remove_nonexistent_activity(self):
        """Test removal from non-existent activity"""
        response = client.post(
            "/activities/FakeActivity/remove",
            params={"email": "student@mergington.edu"}
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "Activity not found"
        
    def test_remove_non_registered_student(self):
        """Test removal of student not registered in activity"""
        response = client.post(
            "/activities/Woodworking/remove",
            params={"email": "notregistered@mergington.edu"}
        )
        assert response.status_code == 400
        assert "not signed up" in response.json()["detail"]
        
    def test_remove_existing_participant(self):
        """Test removal of initially existing participant"""
        response = client.post(
            "/activities/Chess Club/remove",
            params={"email": "michael@mergington.edu"}
        )
        assert response.status_code == 200
        
        # Verify participant was removed
        activities = client.get("/activities").json()
        assert "michael@mergington.edu" not in activities["Chess Club"]["participants"]


class TestIntegration:
    """Integration tests combining multiple operations"""
    
    def test_signup_and_remove_cycle(self):
        """Test complete cycle of signup and removal"""
        email = "integration@mergington.edu"
        activity = "Pottery Club"
        
        # Signup
        response = client.post(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        assert response.status_code == 200
        
        # Verify signup
        activities = client.get("/activities").json()
        assert email in activities[activity]["participants"]
        
        # Remove
        response = client.post(
            f"/activities/{activity}/remove",
            params={"email": email}
        )
        assert response.status_code == 200
        
        # Verify removal
        activities = client.get("/activities").json()
        assert email not in activities[activity]["participants"]
        
    def test_availability_updates_after_signup(self):
        """Test that availability count updates correctly"""
        email = "availability_test@mergington.edu"
        activity = "Gym Class"
        
        # Get initial availability
        initial = client.get("/activities").json()
        initial_spots = initial[activity]["max_participants"] - len(initial[activity]["participants"])
        
        # Signup
        client.post(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        
        # Get new availability
        after = client.get("/activities").json()
        after_spots = after[activity]["max_participants"] - len(after[activity]["participants"])
        
        # Verify one less spot is available
        assert after_spots == initial_spots - 1
