"""
Database operations for API handler
"""

import logging
from typing import List, Optional, Dict, Tuple
from datetime import datetime
import uuid

from sqlalchemy import create_engine, Column, String, Integer, BigInteger, Text, DateTime, ForeignKey, func, and_, or_
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import SQLAlchemyError

from config import Config

logger = logging.getLogger(__name__)

Base = declarative_base()


# SQLAlchemy Models
class Job(Base):
    """Job model"""
    __tablename__ = 'jobs'

    job_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_name = Column(String(255), nullable=False)
    s3_bucket = Column(String(255), nullable=False)
    s3_prefix = Column(String(1024))
    status = Column(String(50), nullable=False)
    total_objects = Column(Integer, default=0)
    completed_objects = Column(Integer, default=0)
    failed_objects = Column(Integer, default=0)
    total_findings = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime)


class JobObject(Base):
    """Job object model"""
    __tablename__ = 'job_objects'

    object_id = Column(BigInteger, primary_key=True, autoincrement=True)
    job_id = Column(UUID(as_uuid=True), ForeignKey('jobs.job_id', ondelete='CASCADE'), nullable=False)
    s3_key = Column(String(1024), nullable=False)
    file_size_bytes = Column(BigInteger)
    status = Column(String(50), nullable=False, default='pending')
    findings_count = Column(Integer, default=0)
    error_message = Column(Text)
    attempts = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    scanned_at = Column(DateTime)


class Finding(Base):
    """Finding model"""
    __tablename__ = 'findings'

    finding_id = Column(BigInteger, primary_key=True, autoincrement=True)
    object_id = Column(BigInteger, ForeignKey('job_objects.object_id', ondelete='CASCADE'), nullable=False)
    job_id = Column(UUID(as_uuid=True), ForeignKey('jobs.job_id', ondelete='CASCADE'), nullable=False)
    finding_type = Column(String(50), nullable=False)
    value_hash = Column(String(64), nullable=False)
    line_number = Column(Integer)
    column_start = Column(Integer)
    column_end = Column(Integer)
    context = Column(Text)
    confidence = Column(String(20), default='high')
    detected_at = Column(DateTime, default=datetime.utcnow)


class DatabaseManager:
    """Database manager for API operations"""

    def __init__(self):
        """Initialize database engine and session factory"""
        self.engine = create_engine(
            Config.get_database_url(),
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
            echo=False
        )
        self.SessionLocal = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)
        logger.info("Database connection pool initialized")

    def create_job(self, job_name: str, s3_bucket: str, s3_prefix: Optional[str],
                   total_objects: int) -> uuid.UUID:
        """
        Create a new scan job

        Args:
            job_name: Name of the job
            s3_bucket: S3 bucket name
            s3_prefix: S3 prefix filter
            total_objects: Total number of objects to scan

        Returns:
            Job UUID
        """
        session = self.SessionLocal()
        try:
            job = Job(
                job_name=job_name,
                s3_bucket=s3_bucket,
                s3_prefix=s3_prefix,
                status='pending',
                total_objects=total_objects
            )
            session.add(job)
            session.commit()
            job_id = job.job_id
            logger.info(f"Created job {job_id}")
            return job_id

        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error creating job: {e}")
            raise
        finally:
            session.close()

    def create_job_objects(self, job_id: uuid.UUID, s3_keys: List[Dict[str, any]]):
        """
        Create job objects for a job

        Args:
            job_id: Job UUID
            s3_keys: List of dicts with 's3_key' and 'file_size_bytes'
        """
        session = self.SessionLocal()
        try:
            objects = [
                JobObject(
                    job_id=job_id,
                    s3_key=item['s3_key'],
                    file_size_bytes=item.get('file_size_bytes', 0),
                    status='pending'
                )
                for item in s3_keys
            ]

            session.bulk_save_objects(objects)
            session.commit()
            logger.info(f"Created {len(objects)} job objects for job {job_id}")

        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error creating job objects: {e}")
            raise
        finally:
            session.close()

    def get_job(self, job_id: uuid.UUID) -> Optional[Dict]:
        """
        Get job details with status counts

        Args:
            job_id: Job UUID

        Returns:
            Job dict or None
        """
        session = self.SessionLocal()
        try:
            job = session.query(Job).filter(Job.job_id == job_id).first()

            if not job:
                return None

            # Get status counts
            status_counts = session.query(
                JobObject.status,
                func.count(JobObject.object_id).label('count')
            ).filter(
                JobObject.job_id == job_id
            ).group_by(JobObject.status).all()

            objects_by_status = {status: count for status, count in status_counts}

            return {
                'job_id': str(job.job_id),
                'job_name': job.job_name,
                's3_bucket': job.s3_bucket,
                's3_prefix': job.s3_prefix,
                'status': job.status,
                'total_objects': job.total_objects,
                'objects_by_status': objects_by_status,
                'completed_objects': job.completed_objects,
                'failed_objects': job.failed_objects,
                'total_findings': job.total_findings,
                'created_at': job.created_at.isoformat() if job.created_at else None,
                'updated_at': job.updated_at.isoformat() if job.updated_at else None,
                'completed_at': job.completed_at.isoformat() if job.completed_at else None
            }

        except SQLAlchemyError as e:
            logger.error(f"Error getting job: {e}")
            return None
        finally:
            session.close()

    def get_findings(self, job_id: Optional[uuid.UUID] = None,
                    finding_type: Optional[str] = None,
                    limit: int = 100,
                    cursor: Optional[int] = None) -> Tuple[List[Dict], Optional[int], bool]:
        """
        Get findings with filtering and pagination

        Args:
            job_id: Filter by job ID
            finding_type: Filter by finding type
            limit: Page size
            cursor: Pagination cursor (finding_id)

        Returns:
            Tuple of (findings list, next_cursor, has_more)
        """
        session = self.SessionLocal()
        try:
            # Build query
            query = session.query(
                Finding,
                JobObject.s3_key
            ).join(
                JobObject,
                Finding.object_id == JobObject.object_id
            )

            # Apply filters
            filters = []
            if job_id:
                filters.append(Finding.job_id == job_id)
            if finding_type:
                filters.append(Finding.finding_type == finding_type)
            if cursor:
                filters.append(Finding.finding_id < cursor)

            if filters:
                query = query.filter(and_(*filters))

            # Order by finding_id descending (newest first)
            query = query.order_by(Finding.finding_id.desc())

            # Limit to page size + 1 to check if there are more results
            results = query.limit(limit + 1).all()

            # Check if there are more results
            has_more = len(results) > limit
            if has_more:
                results = results[:limit]

            # Format findings
            findings = []
            for finding, s3_key in results:
                findings.append({
                    'finding_id': finding.finding_id,
                    'job_id': str(finding.job_id),
                    's3_key': s3_key,
                    'finding_type': finding.finding_type,
                    'value_hash': finding.value_hash,
                    'line_number': finding.line_number,
                    'column_start': finding.column_start,
                    'column_end': finding.column_end,
                    'context': finding.context,
                    'confidence': finding.confidence,
                    'detected_at': finding.detected_at.isoformat() if finding.detected_at else None
                })

            # Get next cursor
            next_cursor = findings[-1]['finding_id'] if findings and has_more else None

            logger.info(f"Retrieved {len(findings)} findings")
            return findings, next_cursor, has_more

        except SQLAlchemyError as e:
            logger.error(f"Error getting findings: {e}")
            return [], None, False
        finally:
            session.close()

    def close(self):
        """Close database engine"""
        self.engine.dispose()
        logger.info("Database connection pool closed")


# Global database manager instance
db_manager: Optional[DatabaseManager] = None


def get_db_manager() -> DatabaseManager:
    """Get or create global database manager"""
    global db_manager
    if db_manager is None:
        db_manager = DatabaseManager()
    return db_manager
