"""
Test script that mimics the Streamlit app behavior to verify the fix
"""

import sys
import os
from pathlib import Path

# Add the streamlit_app directory to Python path
streamlit_app_path = Path(__file__).parent / "streamlit_app"
sys.path.insert(0, str(streamlit_app_path))

# Mock streamlit to avoid dependency issues
class MockStreamlit:
    @staticmethod
    def error(msg):
        print(f"ERROR: {msg}")

# Replace st import
sys.modules['streamlit'] = MockStreamlit()

from utils.api_client import APIClient

def test_api_connection_scenarios():
    """Test different scenarios that match Streamlit usage"""
    print("🧪 Testing API Connection Scenarios")
    print("=" * 60)

    # Create API client like Streamlit does
    api_client = APIClient()

    # Test Case 1: Default health_check (like the working debug script)
    print("\n1. Testing default health_check() call:")
    response1 = api_client.health_check()
    print(f"   Response: {response1}")
    print(f"   Status: {response1.get('status')}")
    if response1.get("status") == "healthy":
        print("   ✅ Default call successful!")
    else:
        print("   ❌ Default call failed!")

    # Test Case 2: Custom URL health_check (like Streamlit app)
    print("\n2. Testing health_check(custom_url) call:")
    api_url = "http://localhost:8000"
    response2 = api_client.health_check(api_url)
    print(f"   API URL: {api_url}")
    print(f"   Response: {response2}")
    print(f"   Status: {response2.get('status')}")
    if response2.get("status") == "healthy":
        print("   ✅ Custom URL call successful!")
        print(f"   📡 Service: {response2.get('service', 'Unknown')}")
        print(f"   🔢 Version: {response2.get('version', 'Unknown')}")
    else:
        print("   ❌ Custom URL call failed!")
        print(f"   🚫 Error: {response2.get('message', 'Unknown error')}")

    # Test Case 3: URL with trailing slash
    print("\n3. Testing health_check with trailing slash:")
    api_url_with_slash = "http://localhost:8000/"
    response3 = api_client.health_check(api_url_with_slash)
    print(f"   API URL: {api_url_with_slash}")
    print(f"   Response: {response3}")
    print(f"   Status: {response3.get('status')}")
    if response3.get("status") == "healthy":
        print("   ✅ URL with trailing slash successful!")
    else:
        print("   ❌ URL with trailing slash failed!")

    # Test Case 4: Invalid URL
    print("\n4. Testing health_check with invalid URL:")
    invalid_url = "http://localhost:9999"
    response4 = api_client.health_check(invalid_url)
    print(f"   API URL: {invalid_url}")
    print(f"   Response: {response4}")
    print(f"   Status: {response4.get('status')}")
    if response4.get("status") == "error":
        print("   ✅ Invalid URL correctly handled!")
        print(f"   💬 Error message: {response4.get('message', 'No message')}")
    else:
        print("   ❌ Invalid URL not handled correctly!")

    print("\n" + "=" * 60)

    # Summary
    success_count = 0
    total_count = 4

    if response1.get("status") == "healthy":
        success_count += 1
    if response2.get("status") == "healthy":
        success_count += 1
    if response3.get("status") == "healthy":
        success_count += 1
    if response4.get("status") == "error":
        success_count += 1

    print(f"📊 Test Results: {success_count}/{total_count} tests passed")

    if success_count == total_count:
        print("🎉 All tests passed! The Streamlit API connection issue is fixed.")
        return True
    else:
        print("❌ Some tests failed. Please check the implementation.")
        return False

if __name__ == "__main__":
    test_api_connection_scenarios()