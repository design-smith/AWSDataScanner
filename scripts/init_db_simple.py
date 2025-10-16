#!/usr/bin/env python3
"""
Simple database initialization script.
Connects via Lambda invoke since Lambda has VPC access.
"""
import json
import sys

# Read SQL files
with open('database/schema.sql', 'r', encoding='utf-8') as f:
    schema = f.read()

with open('database/indexes.sql', 'r', encoding='utf-8') as f:
    indexes = f.read()

# Combined SQL
full_sql = schema + "\n\n" + indexes

# Create a simple Lambda code that executes SQL
lambda_code = f'''
import json
import psycopg2

def lambda_handler(event, context):
    try:
        # Connect to database
        conn = psycopg2.connect(
            host="aws-data-scanner-db-dev.covom8oag137.us-east-1.rds.amazonaws.com",
            port=5432,
            database="datascanner",
            user="dbadmin",
            password="ChangeMe123!",
            connect_timeout=10
        )

        # Execute SQL
        cur = conn.cursor()
        cur.execute("""
{full_sql}
        """)
        conn.commit()
        cur.close()
        conn.close()

        return {{
            "statusCode": 200,
            "body": json.dumps({{"message": "Database initialized successfully"}})
        }}
    except Exception as e:
        return {{
            "statusCode": 500,
            "body": json.dumps({{"error": str(e)}})
        }}
'''

print("Lambda code to execute SQL:")
print("=" * 80)
print(lambda_code)
print("=" * 80)
print("\nYou can either:")
print("1. Copy this code to AWS Lambda console and run it")
print("2. Or use the AWS CLI to create a temp Lambda with this code")
