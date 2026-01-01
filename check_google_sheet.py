#!/usr/bin/env python3
"""
Check Google Sheet data to verify duplicate detection
"""
import os
from data_handler import DataHandler

# Sheet ID from the URL
SHEET_ID = "1miEzcr-TEERKgI2Zf2BQZkah6hUWR8iGpYeF_NcGMcA"

def main():
    print("=" * 60)
    print("Checking Google Sheet Data")
    print("=" * 60)
    print(f"Sheet ID: {SHEET_ID}\n")
    
    # Create data handler
    data_handler = DataHandler()
    data_handler.sheet_id = SHEET_ID
    
    try:
        # Read existing data
        print("Reading data from Google Sheet...")
        existing_data = data_handler._read_existing_sheet_data()
        
        print(f"\n✅ Successfully read {len(existing_data)} records from Google Sheet\n")
        
        if len(existing_data) == 0:
            print("⚠️  WARNING: No data found in sheet!")
            print("   This means duplicate detection won't work.")
            return
        
        # Extract job_ids
        job_ids = []
        for item in existing_data:
            job_id = item.get("job_id")
            if job_id:
                job_ids.append(str(job_id).strip())
        
        print(f"📊 Found {len(job_ids)} records with job_id\n")
        
        # Show first 10 job_ids
        print("First 10 job_ids in sheet:")
        for i, job_id in enumerate(job_ids[:10], 1):
            print(f"  {i}. {job_id}")
        
        # Check for the specific job_id that's being duplicated
        test_job_id = "1339462428"
        if test_job_id in job_ids:
            print(f"\n✅ Found job_id {test_job_id} in sheet (row {job_ids.index(test_job_id) + 2})")
            print("   This should be detected as a duplicate!")
        else:
            print(f"\n❌ job_id {test_job_id} NOT found in sheet")
            print("   This explains why it's not being detected as duplicate")
        
        # Show sample record
        if existing_data:
            print(f"\n📋 Sample record (first one):")
            sample = existing_data[0]
            print(f"   job_id: {sample.get('job_id')} (type: {type(sample.get('job_id')).__name__})")
            print(f"   title: {sample.get('title', '')[:50]}...")
            print(f"   url: {sample.get('url', '')[:50]}...")
        
        # Check for duplicates in the sheet itself
        from collections import Counter
        job_id_counts = Counter(job_ids)
        duplicates = {jid: count for jid, count in job_id_counts.items() if count > 1}
        
        if duplicates:
            print(f"\n⚠️  Found {len(duplicates)} duplicate job_ids in the sheet itself:")
            for jid, count in list(duplicates.items())[:5]:
                print(f"   job_id {jid}: appears {count} times")
        else:
            print(f"\n✅ No duplicates found in sheet (all job_ids are unique)")
        
        print("\n" + "=" * 60)
        print("Summary:")
        print(f"  Total records: {len(existing_data)}")
        print(f"  Records with job_id: {len(job_ids)}")
        print(f"  Unique job_ids: {len(set(job_ids))}")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error reading Google Sheet: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

