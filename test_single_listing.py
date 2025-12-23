"""
Test phone extraction for a single listing URL
"""
from gumtree_scraper import GumtreeScraper

test_url = "https://www.gumtree.com.au/s-ad/nowra/other/farm-position-available/1339200872"

print("=" * 60)
print("Testing Phone Extraction for Single Listing")
print("=" * 60)
print(f"URL: {test_url}")
print()

scraper = GumtreeScraper()

try:
    print("Fetching listing details (debug_phone=True)...")
    details = scraper.get_listing_details(test_url, debug_phone=True)

    if details.get("success"):
        print("\n✓ Listing scraped successfully")
        print(f"\nTitle: {str(details.get('title', 'N/A'))[:80]}...")
        print(f"Job ID: {details.get('job_id', 'N/A')}")
        print(f"Location: {details.get('location', 'N/A')}")
        print(f"Phone: {details.get('phone', 'NOT FOUND')}")

        if details.get("phone"):
            print(f"\n✓✓✓ SUCCESS: Phone number found: {details.get('phone')}")
        else:
            print("\n✗✗✗ FAILED: Phone number not found")
            print("\nLook ABOVE for debug logs like:")
            print(" - 'Detected geo/VPN restriction'")
            print(" - 'XHR calls captured: ...'")
            print(" - 'Endpoint ... no phone'")
    else:
        print(f"\n✗ Failed to scrape listing: {details.get('error')}")

    print("\n" + "=" * 60)

finally:
    scraper.close()
