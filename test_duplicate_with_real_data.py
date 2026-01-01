#!/usr/bin/env python3
"""
Test duplicate detection with real Google Sheet data
Simulates what n8n should do
"""
from data_handler import DataHandler

SHEET_ID = "1miEzcr-TEERKgI2Zf2BQZkah6hUWR8iGpYeF_NcGMcA"

# Simulate new listing from API (the one that's being duplicated)
new_listing_from_api = {
    "job_id": "1339462428",
    "title": "Full-Time Farm Hand – Mixed Farming | Spring Plains (Near Wee Waa",
    "url": "https://www.gumtree.com.au/s-ad/spring-plains/agronomy-farm-services/full-time-farm-hand-mixed-farming-spring-plains-near-wee-waa/1339462428",
    "location": "Spring Plains",
    "categoryName": "Agronomy Farm Services",
    "creationDate": "2025-12-31",
    "description": "Full-Time Farm Hand...",
    "phone": None,
    "phoneNumberExists": False,
    "scraped_at": "2026-01-01 05:41:00",
    "lastEdited": None,
    "success": True,
    "_fromAPI": True  # This is how n8n marks it
}

def normalize_job_id(job_id):
    """Same as n8n workflow"""
    if job_id is None or job_id == '':
        return ''
    return str(job_id).strip()

def main():
    print("=" * 60)
    print("Testing Duplicate Detection with Real Data")
    print("=" * 60)
    
    # Read existing data from Google Sheet
    data_handler = DataHandler()
    data_handler.sheet_id = SHEET_ID
    
    print("\n1. Reading existing data from Google Sheet...")
    existing_data = data_handler._read_existing_sheet_data()
    print(f"   ✅ Found {len(existing_data)} existing records")
    
    # Create set of existing job_ids (same as n8n)
    existing_job_ids = set()
    for item in existing_data:
        job_id = normalize_job_id(item.get("job_id"))
        if job_id:
            existing_job_ids.add(job_id)
    
    print(f"   ✅ Found {len(existing_job_ids)} unique job_ids")
    print(f"   Sample job_ids: {list(existing_job_ids)[:5]}")
    
    # Test the new listing
    print(f"\n2. Testing new listing from API:")
    print(f"   job_id: {new_listing_from_api['job_id']}")
    print(f"   title: {new_listing_from_api['title'][:50]}...")
    
    # Normalize the new listing's job_id
    new_job_id = normalize_job_id(new_listing_from_api["job_id"])
    print(f"   Normalized job_id: '{new_job_id}'")
    
    # Check if it's a duplicate
    print(f"\n3. Checking for duplicate...")
    is_duplicate = new_job_id and new_job_id in existing_job_ids
    
    if is_duplicate:
        print(f"   ✅ DUPLICATE DETECTED!")
        print(f"   job_id '{new_job_id}' already exists in sheet")
        print(f"   This listing should be SKIPPED")
    else:
        print(f"   ❌ NOT detected as duplicate")
        print(f"   job_id '{new_job_id}' not found in existing job_ids")
        print(f"   This listing would be SAVED (but it shouldn't!)")
    
    # Verify the comparison works
    print(f"\n4. Verification:")
    print(f"   new_job_id type: {type(new_job_id).__name__}")
    print(f"   new_job_id value: '{new_job_id}'")
    print(f"   existing_job_ids contains '{new_job_id}': {new_job_id in existing_job_ids}")
    
    # Check exact match
    if "1339462428" in existing_job_ids:
        print(f"   ✅ String '1339462428' is in existing_job_ids")
    else:
        print(f"   ❌ String '1339462428' NOT in existing_job_ids")
        print(f"   This is the problem!")
    
    print("\n" + "=" * 60)
    if is_duplicate:
        print("✅ TEST PASSED: Duplicate detection logic works correctly!")
    else:
        print("❌ TEST FAILED: Duplicate not detected!")
    print("=" * 60)

if __name__ == "__main__":
    main()

