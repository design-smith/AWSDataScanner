"""
File scanner implementation with S3 streaming
"""

import logging
import io
from typing import List, Optional, Tuple
import boto3
from botocore.exceptions import ClientError

from detectors import SensitiveDataDetector, Finding
from config import Config

logger = logging.getLogger(__name__)


class FileScanner:
    """File scanner with S3 streaming support"""

    def __init__(self):
        """Initialize scanner with S3 client and detector"""
        self.s3_client = boto3.client('s3', region_name=Config.AWS_REGION)
        self.detector = SensitiveDataDetector()
        self.chunk_size = Config.CHUNK_SIZE
        self.max_file_size = Config.MAX_FILE_SIZE

    def is_text_file(self, s3_bucket: str, s3_key: str) -> bool:
        """
        Check if file is likely a text file based on extension and magic bytes

        Args:
            s3_bucket: S3 bucket name
            s3_key: S3 object key

        Returns:
            True if text file, False otherwise
        """
        # Check extension
        text_extensions = {
            '.txt', '.log', '.csv', '.json', '.xml', '.html', '.htm',
            '.md', '.py', '.js', '.java', '.c', '.cpp', '.h', '.sh',
            '.yml', '.yaml', '.toml', '.ini', '.cfg', '.conf', '.sql'
        }

        if any(s3_key.lower().endswith(ext) for ext in text_extensions):
            return True

        # For files without clear extension, check magic bytes
        try:
            response = self.s3_client.get_object(
                Bucket=s3_bucket,
                Key=s3_key,
                Range='bytes=0-1023'  # Read first 1KB
            )

            sample = response['Body'].read(1024)

            # Check for null bytes (binary indicator)
            if b'\x00' in sample:
                return False

            # Try to decode as UTF-8
            try:
                sample.decode('utf-8')
                return True
            except UnicodeDecodeError:
                return False

        except ClientError as e:
            logger.error(f"Error checking file type for {s3_key}: {e}")
            return False

    def get_file_size(self, s3_bucket: str, s3_key: str) -> Optional[int]:
        """
        Get file size from S3

        Args:
            s3_bucket: S3 bucket name
            s3_key: S3 object key

        Returns:
            File size in bytes or None if error
        """
        try:
            response = self.s3_client.head_object(Bucket=s3_bucket, Key=s3_key)
            return response['ContentLength']
        except ClientError as e:
            logger.error(f"Error getting file size for {s3_key}: {e}")
            return None

    def scan_file_streaming(self, s3_bucket: str, s3_key: str) -> Tuple[List[Finding], Optional[str]]:
        """
        Scan S3 file using streaming to handle large files

        Args:
            s3_bucket: S3 bucket name
            s3_key: S3 object key

        Returns:
            Tuple of (findings list, error message)
        """
        findings = []
        error_message = None

        try:
            # Check file size
            file_size = self.get_file_size(s3_bucket, s3_key)
            if file_size is None:
                return findings, "Could not determine file size"

            if file_size > self.max_file_size:
                logger.warning(f"File {s3_key} exceeds max size ({file_size} bytes), skipping")
                return findings, f"File too large: {file_size} bytes"

            # Check if text file
            if not self.is_text_file(s3_bucket, s3_key):
                logger.info(f"Skipping non-text file: {s3_key}")
                return findings, "Non-text file, skipped"

            # Stream file content
            logger.info(f"Scanning file: {s3_key} ({file_size} bytes)")

            response = self.s3_client.get_object(Bucket=s3_bucket, Key=s3_key)
            body = response['Body']

            line_number = 0
            buffer = ""

            # Read file in chunks
            for chunk in body.iter_chunks(chunk_size=self.chunk_size):
                try:
                    text = chunk.decode('utf-8')
                except UnicodeDecodeError:
                    logger.warning(f"Unicode decode error in {s3_key}, trying latin-1")
                    try:
                        text = chunk.decode('latin-1')
                    except Exception as e:
                        logger.error(f"Failed to decode chunk in {s3_key}: {e}")
                        continue

                # Add to buffer
                buffer += text

                # Process complete lines
                lines = buffer.split('\n')
                buffer = lines[-1]  # Keep incomplete line in buffer

                for line in lines[:-1]:
                    line_number += 1
                    line_findings = self.detector.scan_line(line, line_number)
                    findings.extend(line_findings)

            # Process remaining buffer
            if buffer:
                line_number += 1
                line_findings = self.detector.scan_line(buffer, line_number)
                findings.extend(line_findings)

            logger.info(f"Scan complete: {s3_key}, found {len(findings)} findings")

        except ClientError as e:
            error_message = f"S3 error: {str(e)}"
            logger.error(f"Error scanning file {s3_key}: {error_message}")

        except Exception as e:
            error_message = f"Unexpected error: {str(e)}"
            logger.error(f"Unexpected error scanning file {s3_key}: {error_message}")

        return findings, error_message

    def scan_file(self, s3_bucket: str, s3_key: str) -> Tuple[List[Finding], Optional[str]]:
        """
        Main scan method (delegates to streaming implementation)

        Args:
            s3_bucket: S3 bucket name
            s3_key: S3 object key

        Returns:
            Tuple of (findings list, error message)
        """
        return self.scan_file_streaming(s3_bucket, s3_key)
