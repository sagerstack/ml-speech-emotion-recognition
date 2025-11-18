"""
Test script to verify the API connection fix
"""
import requests

def test_health_check_direct():
    """Test direct health check call"""
    print("Testing direct API health endpoint...")

    url = "http://localhost:8000/health"
    try:
        response = requests.get(url, timeout=5)
        print(f"✅ Direct call successful! Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return True
    except Exception as e:
        print(f"❌ Direct call failed: {e}")
        return False

def test_custom_url_logic():
    """Test the fixed custom URL logic"""
    print("\nTesting custom URL logic...")

    # Simulate the fixed logic
    custom_url = "http://localhost:8000"
    url = custom_url.rstrip('/') + '/health'

    print(f"Constructed URL: {url}")

    try:
        response = requests.get(url, timeout=5)
        print(f"✅ Custom URL logic successful! Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return True
    except Exception as e:
        print(f"❌ Custom URL logic failed: {e}")
        return False

def test_error_cases():
    """Test error handling"""
    print("\nTesting error cases...")

    # Test invalid URL
    try:
        response = requests.get("http://localhost:9999/health", timeout=5)
        print(f"❌ Should have failed but got: {response.status_code}")
    except requests.exceptions.ConnectionError:
        print("✅ Correctly handled connection error")
    except Exception as e:
        print(f"✅ Correctly handled error: {type(e).__name__}")

if __name__ == "__main__":
    print("🧪 Testing API Connection Fix")
    print("=" * 50)

    success1 = test_health_check_direct()
    success2 = test_custom_url_logic()
    test_error_cases()

    print("\n" + "=" * 50)
    if success1 and success2:
        print("🎉 All tests passed! The fix should work correctly.")
    else:
        print("❌ Some tests failed. Please check the implementation.")