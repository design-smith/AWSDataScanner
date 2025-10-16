#!/usr/bin/env python3
"""
Initialize database via Lambda invocation.
Lambda has VPC access to RDS.
"""
import json
import boto3
import base64

# Read schema files
with open('database/schema.sql', 'r') as f:
    schema_sql = f.read()

with open('database/indexes.sql', 'r') as f:
    indexes_sql = f.read()

# Prepare payload with database credentials and SQL
payload = {
    "action": "init_db",
    "db_config": {
        "host": "aws-data-scanner-db-dev.covom8oag137.us-east-1.rds.amazonaws.com",
        "port": 5432,
        "database": "datascanner",
        "user": "dbadmin",
        "password": "ChangeMe123!"
    },
    "sql_statements": [schema_sql, indexes_sql]
}

# Invoke scan Lambda (it has VPC access)
client = boto3.client('lambda', region_name='us-east-1')

print("Invoking Lambda to initialize database...")
response = client.invoke(
    FunctionName='aws-data-scanner-scan-dev',
    InvocationType='RequestResponse',
    Payload=json.dumps(payload)
)

result = json.loads(response['Payload'].read())
print(json.dumps(result, indent=2))

if response['StatusCode'] == 200:
    print("\n✅ Database initialized successfully!")
else:
    print("\n❌ Database initialization failed!")
    exit(1)
