#!/usr/bin/env python3
"""
Check SQS Dead Letter Queue for failed messages
"""

import boto3
import json
import argparse
from datetime import datetime


def check_dlq(queue_url, max_messages=10):
    """
    Check DLQ for messages

    Args:
        queue_url: DLQ URL
        max_messages: Maximum messages to retrieve
    """
    sqs = boto3.client('sqs')

    print(f"Checking DLQ: {queue_url}")
    print("=" * 80)

    # Get queue attributes
    attrs = sqs.get_queue_attributes(
        QueueUrl=queue_url,
        AttributeNames=['ApproximateNumberOfMessages', 'ApproximateNumberOfMessagesNotVisible']
    )

    total_messages = int(attrs['Attributes'].get('ApproximateNumberOfMessages', 0))
    in_flight = int(attrs['Attributes'].get('ApproximateNumberOfMessagesNotVisible', 0))

    print(f"Total messages in DLQ: {total_messages}")
    print(f"Messages in flight: {in_flight}")
    print()

    if total_messages == 0:
        print("No messages in DLQ. Good!")
        return

    # Receive messages
    print(f"Retrieving up to {max_messages} messages...\n")

    response = sqs.receive_message(
        QueueUrl=queue_url,
        MaxNumberOfMessages=min(max_messages, 10),
        AttributeNames=['All'],
        MessageAttributeNames=['All']
    )

    messages = response.get('Messages', [])

    if not messages:
        print("Could not retrieve messages (they may be in flight)")
        return

    print(f"Retrieved {len(messages)} messages:\n")

    for i, message in enumerate(messages, 1):
        print(f"Message {i}:")
        print(f"  Message ID: {message['MessageId']}")
        print(f"  Receipt Handle: {message['ReceiptHandle'][:50]}...")

        # Parse body
        try:
            body = json.loads(message['Body'])
            print(f"  Job ID: {body.get('job_id')}")
            print(f"  S3 Key: {body.get('s3_key')}")
            print(f"  Attempt: {body.get('attempt', 'N/A')}")
        except json.JSONDecodeError:
            print(f"  Body: {message['Body'][:100]}...")

        # Get attributes
        attributes = message.get('Attributes', {})
        if 'ApproximateReceiveCount' in attributes:
            print(f"  Receive Count: {attributes['ApproximateReceiveCount']}")
        if 'SentTimestamp' in attributes:
            timestamp = int(attributes['SentTimestamp']) / 1000
            dt = datetime.fromtimestamp(timestamp)
            print(f"  Sent: {dt}")

        print()

    print("=" * 80)
    print("\nTo delete messages from DLQ (if resolved), run:")
    print(f"aws sqs purge-queue --queue-url {queue_url}")


def main():
    parser = argparse.ArgumentParser(description='Check SQS Dead Letter Queue')
    parser.add_argument('queue_url', help='DLQ URL')
    parser.add_argument('--max-messages', '-m', type=int, default=10,
                       help='Maximum messages to retrieve (default: 10)')
    args = parser.parse_args()

    check_dlq(args.queue_url, args.max_messages)


if __name__ == '__main__':
    main()
