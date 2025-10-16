#!/usr/bin/env python3
"""
Generate test files with synthetic PII data for testing the scanner
"""

import random
import string
import os
import argparse
from pathlib import Path


class TestDataGenerator:
    """Generate synthetic PII data for testing"""

    def __init__(self):
        self.ssns = []
        self.credit_cards = []
        self.emails = []
        self.phones = []
        self.aws_keys = []

    @staticmethod
    def generate_ssn():
        """Generate a valid-looking SSN (avoiding invalid prefixes)"""
        # Valid SSN: not starting with 000, 666, or 9xx
        area = random.randint(1, 665)
        if area == 666:
            area = 665
        group = random.randint(1, 99)
        serial = random.randint(1, 9999)
        return f"{area:03d}-{group:02d}-{serial:04d}"

    @staticmethod
    def generate_credit_card():
        """Generate a valid credit card number with Luhn check"""
        # Generate 15 digits
        digits = [random.randint(0, 9) for _ in range(15)]

        # Calculate Luhn checksum
        checksum = 0
        for i, digit in enumerate(digits):
            if i % 2 == 0:  # Every second digit from left
                doubled = digit * 2
                checksum += doubled if doubled < 10 else doubled - 9
            else:
                checksum += digit

        # Calculate check digit
        check_digit = (10 - (checksum % 10)) % 10
        digits.append(check_digit)

        # Format as credit card
        card = ''.join(str(d) for d in digits)
        return f"{card[:4]}-{card[4:8]}-{card[8:12]}-{card[12:]}"

    @staticmethod
    def generate_email():
        """Generate a random email address"""
        names = ['john', 'jane', 'bob', 'alice', 'charlie', 'eve', 'michael', 'sarah']
        domains = ['example.com', 'test.org', 'demo.net', 'sample.io']
        name = random.choice(names)
        domain = random.choice(domains)
        return f"{name}.{random.randint(1,999)}@{domain}"

    @staticmethod
    def generate_phone():
        """Generate a US phone number"""
        area = random.randint(200, 999)
        if area in [555, 666, 800, 888, 900]:  # Avoid special prefixes
            area = 202
        exchange = random.randint(200, 999)
        number = random.randint(0, 9999)
        return f"({area}) {exchange}-{number:04d}"

    @staticmethod
    def generate_aws_key():
        """Generate a fake AWS access key"""
        chars = string.ascii_uppercase + string.digits
        key = ''.join(random.choice(chars) for _ in range(16))
        return f"AKIA{key}"

    def generate_clean_text(self, lines=20):
        """Generate clean text with no PII"""
        templates = [
            "This is a normal line of text with no sensitive information.",
            "The quick brown fox jumps over the lazy dog.",
            "Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
            "Data processing completed successfully.",
            "System status: operational.",
            "No issues detected in the logs.",
            "Application performance is within normal parameters.",
            "User session established at system time.",
            "Configuration settings have been updated.",
            "Backup process initiated for database records.",
        ]

        return '\n'.join(random.choice(templates) for _ in range(lines))

    def generate_text_with_pii(self, lines=50, pii_density=0.1):
        """
        Generate text with mixed content and PII

        Args:
            lines: Number of lines to generate
            pii_density: Probability of a line containing PII (0.0 to 1.0)
        """
        text_lines = []
        clean_templates = [
            "Processing user data for account verification.",
            "Customer information updated in the system.",
            "Transaction completed successfully for order.",
            "User profile has been synchronized.",
            "Payment method verification in progress.",
            "Account status updated to active.",
            "Security audit completed for user session.",
            "Database record updated with new information.",
            "Email notification sent to registered address.",
            "Phone verification code dispatched.",
        ]

        pii_templates = [
            "Customer SSN: {ssn} verified",
            "Payment card: {cc} on file",
            "Contact email: {email} registered",
            "Phone number: {phone} confirmed",
            "AWS Access Key: {aws} in use",
            "Employee record {ssn} updated",
            "Credit card {cc} authorized",
            "User email {email} verified",
            "Contact: {phone} for support",
            "API Key {aws} generated",
        ]

        for _ in range(lines):
            if random.random() < pii_density:
                # Add PII line
                template = random.choice(pii_templates)
                line = template.format(
                    ssn=self.generate_ssn(),
                    cc=self.generate_credit_card(),
                    email=self.generate_email(),
                    phone=self.generate_phone(),
                    aws=self.generate_aws_key()
                )
            else:
                # Add clean line
                line = random.choice(clean_templates)

            text_lines.append(line)

        return '\n'.join(text_lines)

    def generate_file(self, filename, file_type='mixed', size_kb=None):
        """
        Generate a test file

        Args:
            filename: Output filename
            file_type: 'clean', 'mixed', or 'dense'
            size_kb: Target file size in KB (approximate)
        """
        if size_kb:
            lines = size_kb * 10  # Rough estimate: 100 bytes per line
        else:
            lines = random.randint(50, 500)

        if file_type == 'clean':
            content = self.generate_clean_text(lines)
        elif file_type == 'dense':
            content = self.generate_text_with_pii(lines, pii_density=0.5)
        else:  # mixed
            content = self.generate_text_with_pii(lines, pii_density=0.1)

        with open(filename, 'w') as f:
            f.write(content)

        print(f"Created: {filename} ({os.path.getsize(filename)} bytes)")


def main():
    parser = argparse.ArgumentParser(description='Generate test files with PII for scanner testing')
    parser.add_argument('--output-dir', '-o', default='test_files', help='Output directory')
    parser.add_argument('--count', '-c', type=int, default=100, help='Number of files to generate')
    parser.add_argument('--size', '-s', type=int, help='File size in KB (random if not specified)')
    args = parser.parse_args()

    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)

    generator = TestDataGenerator()

    print(f"Generating {args.count} test files in {output_dir}/")

    # Generate mix of files
    clean_count = int(args.count * 0.3)  # 30% clean files
    mixed_count = int(args.count * 0.5)  # 50% mixed files
    dense_count = args.count - clean_count - mixed_count  # 20% dense files

    file_num = 1

    # Clean files
    for i in range(clean_count):
        filename = output_dir / f"clean_{file_num:04d}.txt"
        size = args.size if args.size else random.choice([1, 2, 5, 10, 20])
        generator.generate_file(filename, file_type='clean', size_kb=size)
        file_num += 1

    # Mixed files
    for i in range(mixed_count):
        filename = output_dir / f"mixed_{file_num:04d}.txt"
        size = args.size if args.size else random.choice([2, 5, 10, 20, 50])
        generator.generate_file(filename, file_type='mixed', size_kb=size)
        file_num += 1

    # Dense files
    for i in range(dense_count):
        filename = output_dir / f"dense_{file_num:04d}.txt"
        size = args.size if args.size else random.choice([5, 10, 20, 50, 100])
        generator.generate_file(filename, file_type='dense', size_kb=size)
        file_num += 1

    print(f"\nGeneration complete!")
    print(f"  Clean files: {clean_count}")
    print(f"  Mixed files: {mixed_count}")
    print(f"  Dense files: {dense_count}")
    print(f"  Total: {args.count}")


if __name__ == '__main__':
    main()
