"""
GET /results endpoint - Returns scan findings with filtering and pagination
"""

import json
import logging
from typing import Dict, Any, Optional
import uuid
import base64

from config import Config
from database import get_db_manager

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def encode_cursor(finding_id: int) -> str:
    """
    Encode finding_id as base64 cursor

    Args:
        finding_id: Finding ID

    Returns:
        Base64 encoded cursor
    """
    cursor_str = json.dumps({'finding_id': finding_id})
    return base64.b64encode(cursor_str.encode('utf-8')).decode('utf-8')


def decode_cursor(cursor: str) -> Optional[int]:
    """
    Decode base64 cursor to finding_id

    Args:
        cursor: Base64 encoded cursor

    Returns:
        Finding ID or None if invalid
    """
    try:
        cursor_str = base64.b64decode(cursor.encode('utf-8')).decode('utf-8')
        cursor_data = json.loads(cursor_str)
        return cursor_data.get('finding_id')
    except Exception as e:
        logger.error(f"Error decoding cursor: {e}")
        return None


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for GET /results

    Args:
        event: API Gateway event
        context: Lambda context

    Returns:
        API Gateway response
    """
    try:
        # Extract query parameters
        query_params = event.get('queryStringParameters', {}) or {}

        # Parse filters
        job_id_str = query_params.get('job_id')
        finding_type = query_params.get('finding_type')
        limit_str = query_params.get('limit', str(Config.DEFAULT_PAGE_SIZE))
        cursor_str = query_params.get('cursor')

        # Validate job_id if provided
        job_id = None
        if job_id_str:
            try:
                job_id = uuid.UUID(job_id_str)
            except ValueError:
                return {
                    'statusCode': 400,
                    'headers': {'Content-Type': 'application/json'},
                    'body': json.dumps({'error': 'Invalid job_id format'})
                }

        # Validate finding_type if provided
        valid_types = {'ssn', 'credit_card', 'aws_access_key', 'aws_secret_key', 'email', 'phone_us', 'phone_intl'}
        if finding_type and finding_type not in valid_types:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': f'Invalid finding_type. Valid types: {", ".join(valid_types)}'})
            }

        # Parse limit
        try:
            limit = int(limit_str)
            if limit <= 0:
                raise ValueError()
            if limit > Config.MAX_PAGE_SIZE:
                limit = Config.MAX_PAGE_SIZE
        except ValueError:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': f'Invalid limit. Must be between 1 and {Config.MAX_PAGE_SIZE}'})
            }

        # Decode cursor
        cursor = None
        if cursor_str:
            cursor = decode_cursor(cursor_str)
            if cursor is None:
                return {
                    'statusCode': 400,
                    'headers': {'Content-Type': 'application/json'},
                    'body': json.dumps({'error': 'Invalid cursor'})
                }

        logger.info(f"Getting findings: job_id={job_id}, type={finding_type}, limit={limit}, cursor={cursor}")

        # Get findings from database
        db = get_db_manager()
        findings, next_cursor_id, has_more = db.get_findings(
            job_id=job_id,
            finding_type=finding_type,
            limit=limit,
            cursor=cursor
        )

        # Prepare response
        response_body = {
            'findings': findings,
            'count': len(findings),
            'has_more': has_more
        }

        # Add next cursor if there are more results
        if has_more and next_cursor_id:
            response_body['next_cursor'] = encode_cursor(next_cursor_id)

        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps(response_body)
        }

    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'Internal server error'})
        }
