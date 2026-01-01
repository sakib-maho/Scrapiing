#!/usr/bin/env node
/**
 * Simple test for duplicate detection
 * Run this to quickly test if duplicate detection logic works
 */

console.log('🧪 Simple Duplicate Detection Test\n');

// Simulate: You have job_id 1339462428 in your Google Sheet
const existingJobIds = new Set(['1339462428']);

// Simulate: New listing comes in with the same job_id
const newListing = { job_id: '1339462428', title: 'Full-Time Farm Hand' };

// Normalize function (same as in n8n workflow)
function normalizeJobId(jobId) {
  if (jobId === null || jobId === undefined || jobId === '') return '';
  return String(jobId).trim();
}

// Test the comparison
const normalizedJobId = normalizeJobId(newListing.job_id);
const isDuplicate = normalizedJobId && existingJobIds.has(normalizedJobId);

console.log('📊 Test Scenario:');
console.log(`   Existing job_id in sheet: 1339462428`);
console.log(`   New listing job_id: ${newListing.job_id}`);
console.log(`   Normalized: "${normalizedJobId}"`);
console.log(`   Is duplicate? ${isDuplicate ? '✅ YES (will be skipped)' : '❌ NO (will be saved)'}\n`);

if (isDuplicate) {
  console.log('✅ SUCCESS: Duplicate detection is working!');
  console.log('   The listing will be SKIPPED and NOT saved to Google Sheets.');
} else {
  console.log('❌ FAILURE: Duplicate detection is NOT working!');
  console.log('   The listing will be SAVED even though it already exists.');
}

// Test with different formats
console.log('\n📋 Testing different formats:');
const testCases = [
  { job_id: 1339462428, description: 'Number format' },
  { job_id: '1339462428', description: 'String format' },
  { job_id: ' 1339462428 ', description: 'String with spaces' },
  { job_id: '9999999999', description: 'Different job_id (should pass)' },
];

testCases.forEach(test => {
  const normalized = normalizeJobId(test.job_id);
  const isDup = normalized && existingJobIds.has(normalized);
  const status = isDup ? '❌ DUPLICATE' : '✅ NEW';
  console.log(`   ${status}: ${test.description} (${test.job_id})`);
});

console.log('\n✅ All tests complete!');

