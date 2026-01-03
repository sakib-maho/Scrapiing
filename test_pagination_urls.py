#!/usr/bin/env python3
"""
Test script to verify pagination URL construction
Tests if page URLs are constructed correctly according to Gumtree format:
- Page 1: https://www.gumtree.com.au/s-hospitality-tourism/sydney/c18342l3003435
- Page 2+: https://www.gumtree.com.au/s-hospitality-tourism/sydney/page-2/c18342l3003435
"""
import re
from urllib.parse import urlparse, urlunparse, urlencode

def test_pagination_url_construction():
    """Test the pagination URL construction logic"""
    
    # Test category URL from user's example
    category = "s-hospitality-tourism/sydney/c18342l3003435"
    base_url = "https://www.gumtree.com.au"
    
    print("="*70)
    print("Testing Pagination URL Construction")
    print("="*70)
    print(f"\nBase category: {category}")
    print(f"Base URL: {base_url}\n")
    
    # Simulate the URL construction logic from scrape_category
    category_url = f"{base_url}/{category}"
    parsed_url = urlparse(category_url)
    base_path = urlunparse((parsed_url.scheme, parsed_url.netloc, parsed_url.path, '', '', ''))
    
    print(f"Full category URL: {category_url}")
    print(f"Base path (no query params): {base_path}\n")
    print("-"*70)
    
    # Test pages 1-5
    test_pages = [1, 2, 3, 4, 5]
    expected_urls = {
        1: "https://www.gumtree.com.au/s-hospitality-tourism/sydney/c18342l3003435",
        2: "https://www.gumtree.com.au/s-hospitality-tourism/sydney/page-2/c18342l3003435",
        3: "https://www.gumtree.com.au/s-hospitality-tourism/sydney/page-3/c18342l3003435",
        4: "https://www.gumtree.com.au/s-hospitality-tourism/sydney/page-4/c18342l3003435",
        5: "https://www.gumtree.com.au/s-hospitality-tourism/sydney/page-5/c18342l3003435",
    }
    
    all_passed = True
    
    for page in test_pages:
        # Build URL with proper pagination format (same logic as in scrape_category)
        if page > 1:
            # Find the category ID pattern (starts with /c followed by alphanumeric)
            category_id_pattern = re.search(r'(/c[a-z0-9]+)', base_path)
            if category_id_pattern:
                # Insert page number before category ID
                category_id_start = category_id_pattern.start()
                url = base_path[:category_id_start] + f"/page-{page}" + base_path[category_id_start:]
            else:
                # Fallback: if no category ID pattern found, append /page-{page}/
                url = f"{base_path.rstrip('/')}/page-{page}/"
        else:
            # Page 1: use URL as-is (no page number in path)
            url = base_path
        
        expected = expected_urls[page]
        passed = url == expected
        
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"Page {page}: {status}")
        print(f"  Generated: {url}")
        print(f"  Expected:  {expected}")
        
        if not passed:
            all_passed = False
            print(f"  ⚠️  MISMATCH!")
        print()
    
    print("="*70)
    if all_passed:
        print("✅ ALL TESTS PASSED! Pagination URLs are constructed correctly.")
    else:
        print("❌ SOME TESTS FAILED! Check the URLs above.")
    print("="*70)
    
    return all_passed


def test_with_location_parameter():
    """Test pagination URLs with location query parameter"""
    
    print("\n" + "="*70)
    print("Testing Pagination URLs with Location Parameter")
    print("="*70)
    
    category = "s-hospitality-tourism/sydney/c18342l3003435"
    base_url = "https://www.gumtree.com.au"
    location = "Sydney"
    
    category_url = f"{base_url}/{category}"
    parsed_url = urlparse(category_url)
    base_path = urlunparse((parsed_url.scheme, parsed_url.netloc, parsed_url.path, '', '', ''))
    
    print(f"\nCategory: {category}")
    print(f"Location: {location}\n")
    
    for page in [1, 2, 3]:
        # Build URL with pagination
        if page > 1:
            category_id_pattern = re.search(r'(/c[a-z0-9]+)', base_path)
            if category_id_pattern:
                category_id_start = category_id_pattern.start()
                url = base_path[:category_id_start] + f"/page-{page}" + base_path[category_id_start:]
            else:
                url = f"{base_path.rstrip('/')}/page-{page}/"
        else:
            url = base_path
        
        # Add location as query parameter
        params = {"location": location}
        query_string = urlencode(params, doseq=True)
        url_with_location = f"{url}?{query_string}"
        
        print(f"Page {page}: {url_with_location}")
    
    print("="*70)


def test_different_category_formats():
    """Test with different category URL formats"""
    
    print("\n" + "="*70)
    print("Testing Different Category URL Formats")
    print("="*70)
    
    test_cases = [
        "s-hospitality-tourism/sydney/c18342l3003435",
        "s-farming-veterinary/nsw/c21210l3008839",
        "https://www.gumtree.com.au/s-hospitality-tourism/sydney/c18342l3003435",
    ]
    
    base_url = "https://www.gumtree.com.au"
    
    for category in test_cases:
        print(f"\nCategory: {category}")
        
        # Handle category URL (same logic as scrape_category)
        if category.startswith("http"):
            category_url = category
        else:
            category_url = f"{base_url}/{category}"
        
        parsed_url = urlparse(category_url)
        base_path = urlunparse((parsed_url.scheme, parsed_url.netloc, parsed_url.path, '', '', ''))
        
        # Test page 2
        category_id_pattern = re.search(r'(/c[a-z0-9]+)', base_path)
        if category_id_pattern:
            category_id_start = category_id_pattern.start()
            page2_url = base_path[:category_id_start] + "/page-2" + base_path[category_id_start:]
        else:
            page2_url = f"{base_path.rstrip('/')}/page-2/"
        
        print(f"  Page 1: {base_path}")
        print(f"  Page 2: {page2_url}")
    
    print("="*70)


if __name__ == "__main__":
    # Run all tests
    test1_passed = test_pagination_url_construction()
    test_with_location_parameter()
    test_different_category_formats()
    
    print("\n" + "="*70)
    if test1_passed:
        print("✅ MAIN TEST PASSED - Pagination is working correctly!")
    else:
        print("❌ MAIN TEST FAILED - Please review the URL construction logic")
    print("="*70)

