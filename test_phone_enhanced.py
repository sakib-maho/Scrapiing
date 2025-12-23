"""
Test script for enhanced phone extraction
"""
from phone_extractor_enhanced import PhoneExtractorEnhanced

# Test URLs
test_urls = [
    "https://www.gumtree.com.au/s-ad/nowra/other/farm-position-available/1339200872",
    "https://www.gumtree.com.au/web/listing/warehousing-storage-distribution/1338712225",
]

print("="*70)
print("Enhanced Phone Extraction Test")
print("="*70)

for test_url in test_urls:
    print(f"\n{'='*70}")
    print(f"Testing: {test_url}")
    print('='*70)
    
    extractor = PhoneExtractorEnhanced()
    
    try:
        result = extractor.extract_phone(test_url, debug=True)
        
        print(f"\n{'─'*70}")
        print("RESULT:")
        print(f"{'─'*70}")
        print(f"Phone: {result['phone'] if result['phone'] else '(empty)'}")
        print(f"Source: {result['source']}")
        print(f"Reason: {result['reason'] if result['reason'] else '(success)'}")
        print(f"{'─'*70}")
        
        if result['phone']:
            print(f"✓✓✓ SUCCESS: Phone number extracted: {result['phone']}")
        else:
            print(f"✗✗✗ FAILED: {result['reason']}")
    
    except Exception as e:
        print(f"\n✗ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        extractor.client.close()

print(f"\n{'='*70}")
print("Test Complete")
print("="*70)

