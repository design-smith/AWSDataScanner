"""
Database operations for scanner worker
"""

import logging
from typing import List, Optional
from datetime import datetime
from contextlib import contextmanager

from sqlalchemy import create_engine, Column, String, Integer, BigInteger, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, insert
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from sqlalchemy.exc import SQLAlchemyError

from config import Config

logger = logging.getLogger(__name__)

Base = declarative_base()


# SQLAlchemy Models
class Job(Base):
    """Job model"""
    __tablename__ = 'jobs'

    job_id = Column(UUID(as_uuid=True), primary_key=True)
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
    """Database manager with connection pooling"""

    def __init__(self):
        """Initialize database engine and session factory"""
        self.engine = create_engine(
            Config.get_database_url(),
            pool_size=Config.DB_POOL_SIZE,
            max_overflow=Config.DB_MAX_OVERFLOW,
            pool_pre_ping=True,  # Verify connections before using
            echo=False
        )
        self.SessionLocal = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)
        logger.info("Database connection pool initialized")

    @contextmanager
    def get_session(self):
        """Context manager for database sessions"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()

    def update_object_status(self, session: Session, object_id: int, status: str,
                            error_message: Optional[str] = None):
        """
        Update job object status

        Args:
            session: Database session
            object_id: Object ID
            status: New status
            error_message: Error message if failed
        """
        try:
            obj = session.query(JobObject).filter(JobObject.object_id == object_id).first()
            if obj:
                obj.status = status
                obj.scanned_at = datetime.utcnow() if status in ('completed', 'failed') else None
                obj.attempts += 1

                if error_message:
                    obj.error_message = error_message

                session.flush()
                logger.info(f"Updated object {object_id} to status: {status}")
            else:
                logger.warning(f"Object {object_id} not found")

        except SQLAlchemyError as e:
            logger.error(f"Error updating object status: {e}")
            raise

    def bulk_insert_findings(self, session: Session, findings_data: List[dict]):
        """
        Bulk insert findings with ON CONFLICT DO NOTHING for deduplication

        Args:
            session: Database session
            findings_data: List of finding dictionaries
        """
        if not findings_data:
            return

        try:
            # Use PostgreSQL's ON CONFLICT DO NOTHING for idempotency
            stmt = insert(Finding).values(findings_data)
            stmt = stmt.on_conflict_do_nothing(
                index_elements=['object_id', 'finding_type', 'line_number', 'column_start', 'value_hash']
            )

            session.execute(stmt)
            session.flush()
            logger.info(f"Bulk inserted {len(findings_data)} findings (with deduplication)")

        except SQLAlchemyError as e:
            logger.error(f"Error bulk inserting findings: {e}")
            raise

    def get_object_by_job_and_key(self, session: Session, job_id: str, s3_key: str) -> Optional[JobObject]:
        """
        Get job object by job_id and s3_key

        Args:
            session: Database session
            job_id: Job UUID
            s3_key: S3 object key

        Returns:
            JobObject or None
        """
        try:
            return session.query(JobObject).filter(
                JobObject.job_id == job_id,
                JobObject.s3_key == s3_key
            ).first()

        except SQLAlchemyError as e:
            logger.error(f"Error querying job object: {e}")
            return None

    def mark_object_scanning(self, session: Session, object_id: int):
        """Mark object as scanning"""
        self.update_object_status(session, object_id, 'scanning')

    def mark_object_completed(self, session: Session, object_id: int):
        """Mark object as completed"""
        self.update_object_status(session, object_id, 'completed')

    def mark_object_failed(self, session: Session, object_id: int, error_message: str):
        """Mark object as failed"""
        self.update_object_status(session, object_id, 'failed', error_message)

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


def close_db():
    """Close global database manager"""
    global db_manager
    if db_manager:
        db_manager.close()
        db_manager = None
