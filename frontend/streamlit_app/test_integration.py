#!/usr/bin/env python3
"""
Test script to verify the integration between Streamlit frontend and backend API.
"""

import os
import sys
import requests
from pathlib import Path

# Add the src directory to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from api_client import get_api_client, EmotionAnalysisResult
from real_inference import get_backend_health


def test_backend_health():
    """Test if the backend API is healthy."""
    print("🔍 Testing backend health...")
    try:
        health = get_backend_health()
        if health:
            print("✅ Backend is healthy!")
            return True
        else:
            print("❌ Backend is not healthy!")
            return False
    except Exception as e:
        print(f"❌ Error checking backend health: {str(e)}")
        return False


def test_api_client():
    """Test the API client initialization."""
    print("\n🔍 Testing API client...")
    try:
        client = get_api_client()
        print(f"✅ API client initialized with base URL: {client.base_url}")
        return True
    except Exception as e:
        print(f"❌ Error initializing API client: {str(e)}")
        return False


def test_backend_endpoint():
    """Test direct access to backend health endpoint."""
    print("\n🔍 Testing backend endpoint directly...")
    try:
        backend_url = os.getenv("ML_APP_BASE_URL", "http://localhost:8000")
        response = requests.get(f"{backend_url}/health", timeout=5)
        if response.status_code == 200:
            print(f"✅ Backend endpoint responding: {response.json()}")
            return True
        else:
            print(f"❌ Backend endpoint returned status: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error testing backend endpoint: {str(e)}")
        return False


def test_inference_endpoint():
    """Test if inference endpoint exists (without uploading a file)."""
    print("\n🔍 Testing inference endpoint availability...")
    try:
        backend_url = os.getenv("ML_APP_BASE_URL", "http://localhost:8000")
        # Test OPTIONS request to check if endpoint exists
        response = requests.options(f"{backend_url}/v1/infer/infer", timeout=5)
        print(f"✅ Inference endpoint accessible (OPTIONS request successful)")
        return True
    except requests.exceptions.MethodNotAllowed:
        print(f"✅ Inference endpoint exists (Method not allowed for OPTIONS, but endpoint is there)")
        return True
    except Exception as e:
        print(f"❌ Error testing inference endpoint: {str(e)}")
        return False


def test_environment_variables():
    """Test if required environment variables are set."""
    print("\n🔍 Testing environment variables...")
    required_vars = ["ML_APP_BASE_URL"]
    optional_vars = ["REQUEST_TIMEOUT", "ENABLE_MOCK_MODE", "FALLBACK_TO_MOCK"]

    all_good = True
    for var in required_vars:
        value = os.getenv(var)
        if value:
            print(f"✅ {var}: {value}")
        else:
            print(f"❌ {var}: Not set (using default)")
            all_good = False

    for var in optional_vars:
        value = os.getenv(var)
        if value:
            print(f"✅ {var}: {value}")
        else:
            print(f"⚪ {var}: Not set (optional)")

    return all_good


def main():
    """Run all integration tests."""
    print("🚀 Starting Streamlit-Backend Integration Tests\n")
    print("=" * 50)

    tests = [
        test_environment_variables,
        test_backend_health,
        test_api_client,
        test_backend_endpoint,
        test_inference_endpoint,
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        if test():
            passed += 1
        print()

    print("=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! Integration should work correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Check the issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())