#!/usr/bin/env node
/**
 * Test script for duplicate detection logic
 * Simulates the n8n Filter Duplicates node behavior
 */

// Sample existing data from Google Sheets (simulated)
const existingData = [
  { job_id: '1339462428', title: 'Existing Listing 1', url: 'https://example.com/1' },
  { job_id: '1234567890', title: 'Existing Listing 2', url: 'https://example.com/2' },
  { job_id: '9876543210', title: 'Existing Listing 3', url: 'https://example.com/3' },
];

// Sample new listings from API (simulated)
const newListings = [
  { job_id: '1339462428', title: 'New Listing 1 (DUPLICATE)', url: 'https://example.com/1', _fromAPI: true },
  { job_id: '1111111111', title: 'New Listing 2 (NEW)', url: 'https://example.com/new1', _fromAPI: true },
  { job_id: '1234567890', title: 'New Listing 3 (DUPLICATE)', url: 'https://example.com/2', _fromAPI: true },
  { job_id: '2222222222', title: 'New Listing 4 (NEW)', url: 'https://example.com/new2', _fromAPI: true },
];

// Helper function to normalize job_id (same as in n8n workflow)
function normalizeJobId(jobId) {
  if (jobId === null || jobId === undefined || jobId === '') return '';
  return String(jobId).trim();
}

// Simulate the Filter Duplicates logic
function filterDuplicates(existingData, newListings) {
  console.log('=== DUPLICATE DETECTION TEST ===\n');
  
  // Create set of existing job_ids
  const existingJobIds = new Set();
  for (const item of existingData) {
    const normalizedId = normalizeJobId(item.job_id);
    if (normalizedId) {
      existingJobIds.add(normalizedId);
    }
  }
  
  console.log('📊 Existing Data:');
  console.log(`   Total existing records: ${existingData.length}`);
  console.log(`   Existing job_ids: ${Array.from(existingJobIds).join(', ')}\n`);
  
  console.log('📥 New Listings from API:');
  console.log(`   Total new listings: ${newListings.length}`);
  newListings.forEach((listing, index) => {
    console.log(`   ${index + 1}. job_id: ${listing.job_id}, title: ${listing.title}`);
  });
  console.log('');
  
  // Filter out duplicates
  const newData = [];
  let skippedCount = 0;
  const skippedListings = [];
  
  for (const listing of newListings) {
    const jobId = normalizeJobId(listing.job_id);
    
    // Skip if job_id already exists
    if (jobId && existingJobIds.has(jobId)) {
      skippedCount++;
      skippedListings.push(listing);
      console.log(`❌ SKIPPED (duplicate): job_id=${jobId}, title="${listing.title}"`);
      continue;
    }
    
    // Add to new data
    newData.push(listing);
    // Track it to avoid duplicates within new listings
    if (jobId) {
      existingJobIds.add(jobId);
    }
    console.log(`✅ ADDED (new): job_id=${jobId}, title="${listing.title}"`);
  }
  
  console.log('\n=== RESULTS ===');
  console.log(`✅ New listings to save: ${newData.length}`);
  console.log(`❌ Skipped (duplicates): ${skippedCount}`);
  console.log(`📊 Total processed: ${newListings.length}`);
  
  // Verify results
  console.log('\n=== VERIFICATION ===');
  const expectedSkipped = 2; // We expect 2 duplicates (1339462428 and 1234567890)
  const expectedNew = 2; // We expect 2 new listings (1111111111 and 2222222222)
  
  if (skippedCount === expectedSkipped && newData.length === expectedNew) {
    console.log('✅ TEST PASSED: Duplicate detection is working correctly!');
  } else {
    console.log('❌ TEST FAILED: Results do not match expected values');
    console.log(`   Expected skipped: ${expectedSkipped}, Got: ${skippedCount}`);
    console.log(`   Expected new: ${expectedNew}, Got: ${newData.length}`);
  }
  
  return {
    newData,
    skippedCount,
    skippedListings,
    existingJobIds: Array.from(existingJobIds)
  };
}

// Run the test
console.log('🧪 Testing Duplicate Detection Logic\n');
const results = filterDuplicates(existingData, newListings);

// Additional test: Test with real job_id from user's issue
console.log('\n\n=== TEST WITH REAL JOB_ID ===');
const realExistingData = [
  { job_id: '1339462428', title: 'Full-Time Farm Hand', url: 'https://www.gumtree.com.au/s-ad/spring-plains/agronomy-farm-services/full-time-farm-hand-mixed-farming-spring-plains-near-wee-waa/1339462428' }
];

const realNewListings = [
  { job_id: '1339462428', title: 'Full-Time Farm Hand (DUPLICATE)', url: 'https://www.gumtree.com.au/s-ad/spring-plains/agronomy-farm-services/full-time-farm-hand-mixed-farming-spring-plains-near-wee-waa/1339462428', _fromAPI: true },
  { job_id: '9999999999', title: 'New Listing (NEW)', url: 'https://example.com/new', _fromAPI: true }
];

console.log('Testing with job_id: 1339462428 (the one that was being saved incorrectly)\n');
const realResults = filterDuplicates(realExistingData, realNewListings);

if (realResults.skippedCount === 1 && realResults.newData.length === 1) {
  console.log('\n✅ REAL TEST PASSED: job_id 1339462428 should be skipped!');
} else {
  console.log('\n❌ REAL TEST FAILED: job_id 1339462428 was not skipped correctly!');
  console.log(`   Skipped: ${realResults.skippedCount} (expected 1)`);
  console.log(`   New: ${realResults.newData.length} (expected 1)`);
}

// Test edge cases
console.log('\n\n=== EDGE CASE TESTS ===');

// Test 1: Number vs String
console.log('\n1. Testing number vs string job_id:');
const test1Existing = [{ job_id: 1339462428 }]; // Number
const test1New = [{ job_id: '1339462428', _fromAPI: true }]; // String
const test1Results = filterDuplicates(test1Existing, test1New);
if (test1Results.skippedCount === 1) {
  console.log('   ✅ PASSED: Number and string job_id are matched correctly');
} else {
  console.log('   ❌ FAILED: Number and string job_id should match');
}

// Test 2: Empty/null job_id
console.log('\n2. Testing empty/null job_id:');
const test2Existing = [{ job_id: '1339462428' }];
const test2New = [
  { job_id: null, _fromAPI: true },
  { job_id: '', _fromAPI: true },
  { job_id: '1339462428', _fromAPI: true }
];
const test2Results = filterDuplicates(test2Existing, test2New);
if (test2Results.skippedCount === 1 && test2Results.newData.length === 2) {
  console.log('   ✅ PASSED: Empty/null job_ids are handled correctly');
} else {
  console.log('   ❌ FAILED: Empty/null job_ids not handled correctly');
}

console.log('\n\n=== ALL TESTS COMPLETE ===');

