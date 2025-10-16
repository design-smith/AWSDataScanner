#!/bin/bash
# Test API endpoints

set -e

# Configuration
API_URL="${1:-}"

if [ -z "$API_URL" ]; then
    echo "Usage: $0 <api-gateway-url>"
    echo "Example: $0 https://abc123.execute-api.us-east-1.amazonaws.com/dev"
    exit 1
fi

echo "Testing API at: $API_URL"
echo "================================"

# Test 1: POST /scan
echo -e "\n1. Testing POST /scan"
SCAN_RESPONSE=$(curl -s -X POST "$API_URL/scan" \
    -H "Content-Type: application/json" \
    -d '{
        "job_name": "Test Scan",
        "s3_bucket": "your-bucket-name",
        "s3_prefix": "test-data/"
    }')

echo "Response: $SCAN_RESPONSE"

# Extract job_id
JOB_ID=$(echo "$SCAN_RESPONSE" | jq -r '.job_id')

if [ "$JOB_ID" = "null" ]; then
    echo "Error: Failed to create scan job"
    exit 1
fi

echo "Created job: $JOB_ID"

# Test 2: GET /jobs/{job_id}
echo -e "\n2. Testing GET /jobs/$JOB_ID"
sleep 2  # Wait a bit for processing

JOB_RESPONSE=$(curl -s -X GET "$API_URL/jobs/$JOB_ID")
echo "Response: $JOB_RESPONSE" | jq '.'

# Test 3: GET /results (all findings)
echo -e "\n3. Testing GET /results (first 10)"
RESULTS_RESPONSE=$(curl -s -X GET "$API_URL/results?limit=10")
echo "Response: $RESULTS_RESPONSE" | jq '.findings | length' | xargs echo "Found findings:"

# Test 4: GET /results (filtered by job_id)
echo -e "\n4. Testing GET /results?job_id=$JOB_ID"
RESULTS_JOB=$(curl -s -X GET "$API_URL/results?job_id=$JOB_ID&limit=5")
echo "Response: $RESULTS_JOB" | jq '.'

# Test 5: GET /results (filtered by finding_type)
echo -e "\n5. Testing GET /results?finding_type=ssn"
RESULTS_SSN=$(curl -s -X GET "$API_URL/results?finding_type=ssn&limit=5")
echo "Response: $RESULTS_SSN" | jq '.findings | length' | xargs echo "SSN findings:"

# Test 6: Pagination test
echo -e "\n6. Testing pagination"
PAGE1=$(curl -s -X GET "$API_URL/results?limit=2")
CURSOR=$(echo "$PAGE1" | jq -r '.next_cursor')

if [ "$CURSOR" != "null" ]; then
    echo "First page cursor: $CURSOR"
    PAGE2=$(curl -s -X GET "$API_URL/results?limit=2&cursor=$CURSOR")
    echo "Second page: $PAGE2" | jq '.findings | length' | xargs echo "Findings on page 2:"
else
    echo "No pagination cursor (less than 2 results)"
fi

echo -e "\n================================"
echo "API tests complete!"
