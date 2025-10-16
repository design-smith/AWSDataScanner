"""
Configuration management for API handler
"""

import os
from decouple import config


class Config:
    """Configuration class with environment variables"""

    # AWS Configuration
    AWS_REGION = config('AWS_REGION', default='us-east-1')
    SQS_QUEUE_URL = config('SQS_QUEUE_URL')

    # Database Configuration
    DB_HOST = config('DB_HOST')
    DB_PORT = config('DB_PORT', default=5432, cast=int)
    DB_NAME = config('DB_NAME', default='scanner_db')
    DB_USER = config('DB_USER', default='postgres')
    DB_PASSWORD = config('DB_PASSWORD')

    # Pagination
    DEFAULT_PAGE_SIZE = config('DEFAULT_PAGE_SIZE', default=100, cast=int)
    MAX_PAGE_SIZE = config('MAX_PAGE_SIZE', default=1000, cast=int)

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
