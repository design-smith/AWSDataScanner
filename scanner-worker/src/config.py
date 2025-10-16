"""
Configuration management for scanner worker
"""

import os
from decouple import config


class Config:
    """Configuration class with environment variables"""

    # AWS Configuration
    AWS_REGION = config('AWS_REGION', default='us-east-1')
    SQS_QUEUE_URL = config('SQS_QUEUE_URL')
    S3_BUCKET = config('S3_BUCKET', default=None)

    # Database Configuration
    DB_HOST = config('DB_HOST')
    DB_PORT = config('DB_PORT', default=5432, cast=int)
    DB_NAME = config('DB_NAME', default='scanner_db')
    DB_USER = config('DB_USERNAME', default='postgres')
    DB_PASSWORD = config('DB_PASSWORD')

    # Worker Configuration
    POLL_WAIT_TIME = config('POLL_WAIT_TIME', default=20, cast=int)
    MAX_MESSAGES = config('MAX_MESSAGES', default=1, cast=int)
    VISIBILITY_TIMEOUT = config('VISIBILITY_TIMEOUT', default=300, cast=int)
    MAX_FILE_SIZE = config('MAX_FILE_SIZE', default=500 * 1024 * 1024, cast=int)  # 500MB
    CHUNK_SIZE = config('CHUNK_SIZE', default=10 * 1024 * 1024, cast=int)  # 10MB

    # Logging
    LOG_LEVEL = config('LOG_LEVEL', default='INFO')

    # Connection Pooling
    DB_POOL_SIZE = config('DB_POOL_SIZE', default=5, cast=int)
    DB_MAX_OVERFLOW = config('DB_MAX_OVERFLOW', default=10, cast=int)

    @classmethod
    def get_database_url(cls) -> str:
        """Generate database URL for SQLAlchemy"""
        return f"postgresql://{cls.DB_USER}:{cls.DB_PASSWORD}@{cls.DB_HOST}:{cls.DB_PORT}/{cls.DB_NAME}"

    @classmethod
    def validate(cls):
        """Validate required configuration"""
        required = ['SQS_QUEUE_URL', 'DB_HOST', 'DB_PASSWORD']
        missing = [key for key in required if not getattr(cls, key, None)]

        if missing:
            raise ValueError(f"Missing required configuration: {', '.join(missing)}")
