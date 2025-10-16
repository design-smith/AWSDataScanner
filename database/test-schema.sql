INSERT INTO jobs (job_id, job_name, s3_bucket, s3_prefix, status, total_objects)
VALUES
    ('550e8400-e29b-41d4-a716-446655440000', 'Test Job 1', 'test-bucket', 'uploads/2024/01/', 'running', 3),
    ('550e8400-e29b-41d4-a716-446655440001', 'Test Job 2', 'test-bucket', 'uploads/2024/02/', 'completed', 2);

INSERT INTO job_objects (object_id, job_id, s3_key, file_size_bytes, status, scanned_at)
VALUES
    (1, '550e8400-e29b-41d4-a716-446655440000', 'uploads/2024/01/doc1.txt', 1024, 'completed', CURRENT_TIMESTAMP),
    (2, '550e8400-e29b-41d4-a716-446655440000', 'uploads/2024/01/doc2.txt', 2048, 'completed', CURRENT_TIMESTAMP),
    (3, '550e8400-e29b-41d4-a716-446655440000', 'uploads/2024/01/doc3.txt', 512, 'pending', NULL),
    (4, '550e8400-e29b-41d4-a716-446655440001', 'uploads/2024/02/doc1.txt', 4096, 'completed', CURRENT_TIMESTAMP),
    (5, '550e8400-e29b-41d4-a716-446655440001', 'uploads/2024/02/doc2.txt', 8192, 'completed', CURRENT_TIMESTAMP);

INSERT INTO findings (object_id, job_id, finding_type, value_hash, line_number, column_start, column_end, context, confidence)
VALUES
    (1, '550e8400-e29b-41d4-a716-446655440000', 'ssn', 'a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3', 10, 5, 16, 'Employee SSN: 123-45-6789 on file', 'high'),
    (1, '550e8400-e29b-41d4-a716-446655440000', 'email', 'b3d7f5c9e8f2a1d4c6b9a8e7f6d5c4b3a2e1f9d8c7b6a5e4d3c2b1a9f8e7d6c5', 15, 20, 35, 'Contact: john.doe@example.com for more', 'high'),
    (2, '550e8400-e29b-41d4-a716-446655440000', 'credit_card', 'c3499c2729730a7f807efb8676a92dcb6f8a3f8f3c3e3d3c3b3a3938373635343', 5, 10, 29, 'Card: 4532-1488-0343-6467', 'high'),
    (4, '550e8400-e29b-41d4-a716-446655440001', 'aws_access_key', 'd5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6', 8, 15, 35, 'Access key: AKIAIOSFODNN7EXAMPLE found', 'high'),
    (5, '550e8400-e29b-41d4-a716-446655440001', 'phone_us', 'e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9', 20, 8, 20, 'Call: (555) 123-4567', 'high');

SELECT 'Jobs:' as table_name, COUNT(*) as count FROM jobs
UNION ALL
SELECT 'Job Objects:', COUNT(*) FROM job_objects
UNION ALL
SELECT 'Findings:', COUNT(*) FROM findings;