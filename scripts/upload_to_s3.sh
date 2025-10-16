#!/bin/bash
# Upload test files to S3 bucket

set -e

# Configuration
BUCKET_NAME="${1:-}"
PREFIX="${2:-test-data/}"
LOCAL_DIR="${3:-test_files}"

if [ -z "$BUCKET_NAME" ]; then
    echo "Usage: $0 <bucket-name> [prefix] [local-dir]"
    echo "Example: $0 my-scanner-bucket test-data/ test_files/"
    exit 1
fi

echo "Uploading files from $LOCAL_DIR to s3://$BUCKET_NAME/$PREFIX"

# Check if directory exists
if [ ! -d "$LOCAL_DIR" ]; then
    echo "Error: Directory $LOCAL_DIR does not exist"
    exit 1
fi

# Count files
FILE_COUNT=$(find "$LOCAL_DIR" -type f | wc -l)
echo "Found $FILE_COUNT files to upload"

# Upload with progress
aws s3 sync "$LOCAL_DIR" "s3://$BUCKET_NAME/$PREFIX" \
    --no-progress \
    --storage-class STANDARD

echo "Upload complete!"
echo "Files available at: s3://$BUCKET_NAME/$PREFIX"

# List uploaded files
echo -e "\nUploaded files:"
aws s3 ls "s3://$BUCKET_NAME/$PREFIX" --recursive --human-readable --summarize
