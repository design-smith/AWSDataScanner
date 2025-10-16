"""
GET /jobs/{job_id} endpoint - Returns job status and progress
"""

import json
import logging
from typing import Dict, Any
import uuid

from database import get_db_manager

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for GET /jobs/{job_id}

    Args:
        event: API Gateway event
        context: Lambda context

    Returns:
        API Gateway response
    """
    try:
        # Extract job_id from path parameters
        path_params = event.get('pathParameters', {})
        job_id_str = path_params.get('job_id')

        if not job_id_str:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'Missing job_id in path'})
            }

        # Validate UUID format
        try:
            job_id = uuid.UUID(job_id_str)
        except ValueError:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'Invalid job_id format'})
            }

        logger.info(f"Getting job details for {job_id}")

        # Get job from database
        db = get_db_manager()
        job = db.get_job(job_id)

        if not job:
            return {
                'statusCode': 404,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'Job not found'})
            }

        # Return job details
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps(job)
        }

    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'Internal server error'})
        }
