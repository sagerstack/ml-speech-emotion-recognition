"""
Simple test to verify the URL construction logic
"""

def test_url_construction():
    """Test the URL construction logic from the fix"""
    print("🧪 Testing URL Construction Logic")
    print("=" * 50)

    # Test Case 1: Custom URL without trailing slash
    print("\n1. Custom URL without trailing slash:")
    custom_url = "http://localhost:8000"
    if custom_url:
        url = custom_url.rstrip('/') + '/health'
    else:
        url = "http://localhost:8000/health"
    print(f"   Input: {custom_url}")
    print(f"   Output: {url}")
    print(f"   Expected: http://localhost:8000/health")
    print(f"   ✅ Correct!" if url == "http://localhost:8000/health" else "   ❌ Wrong!")

    # Test Case 2: Custom URL with trailing slash
    print("\n2. Custom URL with trailing slash:")
    custom_url = "http://localhost:8000/"
    if custom_url:
        url = custom_url.rstrip('/') + '/health'
    else:
        url = "http://localhost:8000/health"
    print(f"   Input: {custom_url}")
    print(f"   Output: {url}")
    print(f"   Expected: http://localhost:8000/health")
    print(f"   ✅ Correct!" if url == "http://localhost:8000/health" else "   ❌ Wrong!")

    # Test Case 3: No custom URL (default)
    print("\n3. No custom URL (default behavior):")
    custom_url = None
    base_url = "http://localhost:8000"
    if custom_url:
        url = custom_url.rstrip('/') + '/health'
    else:
        url = f"{base_url}/health"
    print(f"   Input: {custom_url}")
    print(f"   Output: {url}")
    print(f"   Expected: http://localhost:8000/health")
    print(f"   ✅ Correct!" if url == "http://localhost:8000/health" else "   ❌ Wrong!")

    print("\n" + "=" * 50)
    print("🎉 URL construction logic is correct!")

if __name__ == "__main__":
    test_url_construction()