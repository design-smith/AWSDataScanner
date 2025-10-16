#!/usr/bin/env python3
"""
Initialize RDS database with schema and indexes
"""

import psycopg2
import sys
from pathlib import Path

# Database connection details
DB_HOST = "aws-data-scanner-db-dev.covom8oag137.us-east-1.rds.amazonaws.com"
DB_PORT = 5432
DB_NAME = "datascanner"
DB_USER = "dbadmin"
DB_PASSWORD = "ChangeMe123!"

def read_sql_file(filepath):
    """Read SQL file"""
    with open(filepath, 'r') as f:
        return f.read()

def main():
    print(f"Connecting to database: {DB_HOST}")

    try:
        # Connect to database
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        conn.autocommit = True
        cur = conn.cursor()

        print("Connected successfully!")

        # Read and execute schema.sql
        print("\nExecuting schema.sql...")
        schema_path = Path(__file__).parent.parent / "database" / "schema.sql"
        schema_sql = read_sql_file(schema_path)
        cur.execute(schema_sql)
        print("✓ Schema created successfully!")

        # Read and execute indexes.sql
        print("\nExecuting indexes.sql...")
        indexes_path = Path(__file__).parent.parent / "database" / "indexes.sql"
        indexes_sql = read_sql_file(indexes_path)
        cur.execute(indexes_sql)
        print("✓ Indexes created successfully!")

        # Verify tables exist
        print("\nVerifying tables...")
        cur.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)

        tables = cur.fetchall()
        print(f"\nFound {len(tables)} tables:")
        for table in tables:
            print(f"  - {table[0]}")

        # Check table counts
        print("\nTable row counts:")
        for table in tables:
            cur.execute(f"SELECT COUNT(*) FROM {table[0]}")
            count = cur.fetchone()[0]
            print(f"  - {table[0]}: {count} rows")

        cur.close()
        conn.close()

        print("\n✅ Database initialization complete!")

    except psycopg2.Error as e:
        print(f"\n❌ Database error: {e}")
        sys.exit(1)
    except FileNotFoundError as e:
        print(f"\n❌ File not found: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
