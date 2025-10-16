"""
Main scanner worker application

Long-polls SQS queue for scan jobs, downloads S3 files,
runs detectors, and writes findings to database.
"""

import json
import logging
import sys
import signal
import time
from typing import Optional, Dict

import boto3
from botocore.exceptions import ClientError

from config import Config
from database import get_db_manager, close_db
from scanner import FileScanner

# Configure logging
logging.basicConfig(
    level=Config.LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)

# Global flag for graceful shutdown
shutdown_flag = False


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    global shutdown_flag
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    shutdown_flag = True


# Register signal handlers
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)


class ScannerWorker:
    """Main worker class for processing scan jobs"""

    def __init__(self):
        """Initialize worker with AWS clients and database"""
        self.sqs_client = boto3.client('sqs', region_name=Config.AWS_REGION)
        self.queue_url = Config.SQS_QUEUE_URL
        self.db_manager = get_db_manager()
        self.scanner = FileScanner()

        logger.info(f"Scanner worker initialized")
        logger.info(f"Queue URL: {self.queue_url}")
        logger.info(f"Poll wait time: {Config.POLL_WAIT_TIME}s")
        logger.info(f"Max messages: {Config.MAX_MESSAGES}")

    def parse_message(self, message_body: str) -> Optional[Dict]:
        """
        Parse SQS message body

        Args:
            message_body: JSON message body

        Returns:
            Parsed message dict or None if invalid
        """
        try:
            data = json.loads(message_body)

            # Validate required fields
            required_fields = ['job_id', 's3_bucket', 's3_key']
            if not all(field in data for field in required_fields):
                logger.error(f"Missing required fields in message: {data}")
                return None

            return data

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in message: {e}")
            return None

    def process_message(self, message: Dict):
        """
        Process a single SQS message

        Args:
            message: SQS message dict
        """
        receipt_handle = message['ReceiptHandle']
        message_id = message['MessageId']

        try:
            # Parse message
            data = self.parse_message(message['Body'])
            if not data:
                logger.error(f"Invalid message format: {message['Body']}")
                # Delete invalid message to prevent reprocessing
                self.delete_message(receipt_handle)
                return

            job_id = data['job_id']
            s3_bucket = data['s3_bucket']
            s3_key = data['s3_key']
            attempt = data.get('attempt', 1)

            logger.info(f"Processing job {job_id}, file: {s3_key} (attempt {attempt})")

            # Get or create job object in database
            with self.db_manager.get_session() as session:
                obj = self.db_manager.get_object_by_job_and_key(session, job_id, s3_key)

                if not obj:
                    logger.error(f"Job object not found for job {job_id}, key {s3_key}")
                    # Delete message since object doesn't exist
                    self.delete_message(receipt_handle)
                    return

                object_id = obj.object_id

                # Mark as scanning
                self.db_manager.mark_object_scanning(session, object_id)

            # Scan file
            findings, error_message = self.scanner.scan_file(s3_bucket, s3_key)

            # Write results to database
            with self.db_manager.get_session() as session:
                if error_message:
                    # Mark as failed
                    self.db_manager.mark_object_failed(session, object_id, error_message)
                    logger.warning(f"Scan failed for {s3_key}: {error_message}")

                else:
                    # Insert findings
                    if findings:
                        findings_data = [
                            {
                                'object_id': object_id,
                                'job_id': job_id,
                                'finding_type': f.finding_type,
                                'value_hash': f.value_hash,
                                'line_number': f.line_number,
                                'column_start': f.column_start,
                                'column_end': f.column_end,
                                'context': f.context,
                                'confidence': f.confidence
                            }
                            for f in findings
                        ]

                        self.db_manager.bulk_insert_findings(session, findings_data)
                        logger.info(f"Inserted {len(findings)} findings for {s3_key}")

                    # Mark as completed
                    self.db_manager.mark_object_completed(session, object_id)
                    logger.info(f"Successfully scanned {s3_key}")

            # Delete message from queue
            self.delete_message(receipt_handle)
            logger.info(f"Completed processing message {message_id}")

        except Exception as e:
            logger.error(f"Error processing message {message_id}: {e}", exc_info=True)
            # Don't delete message - let it retry or go to DLQ

    def delete_message(self, receipt_handle: str):
        """
        Delete message from SQS queue

        Args:
            receipt_handle: Message receipt handle
        """
        try:
            self.sqs_client.delete_message(
                QueueUrl=self.queue_url,
                ReceiptHandle=receipt_handle
            )
            logger.debug("Message deleted from queue")

        except ClientError as e:
            logger.error(f"Error deleting message: {e}")

    def poll_queue(self):
        """Poll SQS queue for messages"""
        try:
            response = self.sqs_client.receive_message(
                QueueUrl=self.queue_url,
                MaxNumberOfMessages=Config.MAX_MESSAGES,
                WaitTimeSeconds=Config.POLL_WAIT_TIME,
                VisibilityTimeout=Config.VISIBILITY_TIMEOUT,
                AttributeNames=['ApproximateReceiveCount']
            )

            messages = response.get('Messages', [])

            if messages:
                logger.info(f"Received {len(messages)} message(s)")

                for message in messages:
                    if shutdown_flag:
                        logger.info("Shutdown flag set, stopping message processing")
                        break

                    self.process_message(message)
            else:
                logger.debug("No messages received")

        except ClientError as e:
            logger.error(f"Error polling queue: {e}")
            time.sleep(5)  # Back off on error

        except Exception as e:
            logger.error(f"Unexpected error polling queue: {e}", exc_info=True)
            time.sleep(5)

    def run(self):
        """Main worker loop"""
        logger.info("Starting scanner worker...")

        try:
            while not shutdown_flag:
                self.poll_queue()

        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")

        finally:
            logger.info("Shutting down worker...")
            close_db()
            logger.info("Worker stopped")


def main():
    """Main entry point"""
    try:
        # Validate configuration
        Config.validate()

        # Create and run worker
        worker = ScannerWorker()
        worker.run()

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
