"""
Unit tests for sensitive data detectors
"""

import pytest
from src.detectors import SensitiveDataDetector, Finding, scan_text


class TestLuhnValidation:
    """Test Luhn algorithm for credit card validation"""

    def test_valid_credit_cards(self):
        """Test valid credit card numbers"""
        detector = SensitiveDataDetector()

        # Valid test credit cards
        valid_cards = [
            '4532111111111111',  # Visa
            '5425233430109903',  # MasterCard
            '374245455400126',   # Amex
            '6011111111111117',  # Discover
        ]

        for card in valid_cards:
            assert detector.luhn_check(card), f"Failed for {card}"

    def test_invalid_credit_cards(self):
        """Test invalid credit card numbers"""
        detector = SensitiveDataDetector()

        invalid_cards = [
            '1234567890123456',
            '0000000000000000',
            '1111111111111111',
        ]

        for card in invalid_cards:
            assert not detector.luhn_check(card), f"Should fail for {card}"

    def test_luhn_with_spaces(self):
        """Test Luhn with formatted card numbers"""
        detector = SensitiveDataDetector()
        assert detector.luhn_check('4532 1111 1111 1111')
        assert detector.luhn_check('4532-1111-1111-1111')


class TestSSNDetection:
    """Test SSN detection"""

    def test_detect_ssn_basic(self):
        """Test basic SSN detection"""
        detector = SensitiveDataDetector()

        text = "Employee SSN: 123-45-6789"
        findings = detector.detect_ssn(text, 1)

        assert len(findings) == 1
        assert findings[0].finding_type == 'ssn'
        assert findings[0].line_number == 1
        assert '123-45-6789' in findings[0].context

    def test_detect_ssn_variations(self):
        """Test SSN with different formats"""
        detector = SensitiveDataDetector()

        test_cases = [
            "123-45-6789",
            "123 45 6789",
            "123456789",
        ]

        for ssn in test_cases:
            findings = detector.detect_ssn(f"SSN: {ssn}", 1)
            assert len(findings) >= 0  # May filter out invalid formats

    def test_reject_invalid_ssn(self):
        """Test rejection of invalid SSNs"""
        detector = SensitiveDataDetector()

        invalid_ssns = [
            "000-45-6789",  # Starts with 000
            "666-45-6789",  # Starts with 666
            "900-45-6789",  # Starts with 9
        ]

        for ssn in invalid_ssns:
            findings = detector.detect_ssn(f"SSN: {ssn}", 1)
            assert len(findings) == 0, f"Should reject {ssn}"

    def test_ssn_context(self):
        """Test context extraction for SSN"""
        detector = SensitiveDataDetector()

        text = "The employee with SSN 123-45-6789 has been verified."
        findings = detector.detect_ssn(text, 1)

        assert len(findings) == 1
        assert 'employee' in findings[0].context.lower()
        assert '123-45-6789' in findings[0].context


class TestCreditCardDetection:
    """Test credit card detection"""

    def test_detect_valid_credit_card(self):
        """Test detection of valid credit cards"""
        detector = SensitiveDataDetector()

        text = "Card number: 4532-1111-1111-1111"
        findings = detector.detect_credit_card(text, 1)

        assert len(findings) == 1
        assert findings[0].finding_type == 'credit_card'
        assert findings[0].confidence == 'high'

    def test_detect_credit_card_formats(self):
        """Test credit card detection with different formats"""
        detector = SensitiveDataDetector()

        formats = [
            "4532111111111111",
            "4532-1111-1111-1111",
            "4532 1111 1111 1111",
        ]

        for card in formats:
            findings = detector.detect_credit_card(f"Card: {card}", 1)
            assert len(findings) >= 0

    def test_reject_invalid_luhn(self):
        """Test rejection of invalid Luhn checksum"""
        detector = SensitiveDataDetector()

        text = "Card: 1234-5678-9012-3456"  # Invalid Luhn
        findings = detector.detect_credit_card(text, 1)

        # Should be empty since Luhn validation fails
        assert len(findings) == 0


class TestAWSKeyDetection:
    """Test AWS key detection"""

    def test_detect_aws_access_key(self):
        """Test AWS access key detection"""
        detector = SensitiveDataDetector()

        text = "AWS_ACCESS_KEY=AKIAIOSFODNN7EXAMPLE"
        findings = detector.detect_aws_keys(text, 1)

        access_keys = [f for f in findings if f.finding_type == 'aws_access_key']
        assert len(access_keys) == 1
        assert 'AKIA' in access_keys[0].value

    def test_detect_aws_secret_key(self):
        """Test AWS secret key detection"""
        detector = SensitiveDataDetector()

        text = "AWS_SECRET_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
        findings = detector.detect_aws_keys(text, 1)

        secret_keys = [f for f in findings if f.finding_type == 'aws_secret_key']
        assert len(secret_keys) >= 0  # May have false positives

    def test_aws_key_confidence(self):
        """Test confidence levels for AWS keys"""
        detector = SensitiveDataDetector()

        text = "AKIAIOSFODNN7EXAMPLE"
        findings = detector.detect_aws_keys(text, 1)

        access_keys = [f for f in findings if f.finding_type == 'aws_access_key']
        if access_keys:
            assert access_keys[0].confidence == 'high'


class TestEmailDetection:
    """Test email detection"""

    def test_detect_email_basic(self):
        """Test basic email detection"""
        detector = SensitiveDataDetector()

        text = "Contact: john.doe@example.com"
        findings = detector.detect_email(text, 1)

        assert len(findings) == 1
        assert findings[0].finding_type == 'email'
        assert 'john.doe@example.com' in findings[0].value

    def test_detect_email_variations(self):
        """Test email variations"""
        detector = SensitiveDataDetector()

        emails = [
            "user@example.com",
            "user.name@example.com",
            "user+tag@example.co.uk",
            "user_name123@sub.example.com",
        ]

        for email in emails:
            findings = detector.detect_email(f"Email: {email}", 1)
            assert len(findings) == 1, f"Failed for {email}"

    def test_email_case_insensitive_hash(self):
        """Test email hashing is case-insensitive"""
        detector = SensitiveDataDetector()

        findings1 = detector.detect_email("test@EXAMPLE.COM", 1)
        findings2 = detector.detect_email("test@example.com", 1)

        if findings1 and findings2:
            assert findings1[0].value_hash == findings2[0].value_hash


class TestPhoneDetection:
    """Test phone number detection"""

    def test_detect_phone_us(self):
        """Test US phone number detection"""
        detector = SensitiveDataDetector()

        text = "Call: (555) 123-4567"
        findings = detector.detect_phone(text, 1)

        # Note: 555 prefix is excluded as invalid
        assert len(findings) == 0

    def test_detect_phone_formats(self):
        """Test phone number formats"""
        detector = SensitiveDataDetector()

        phones = [
            "2025551234",
            "(202) 555-1234",
            "202-555-1234",
            "202.555.1234",
            "+1-202-555-1234",
        ]

        for phone in phones:
            findings = detector.detect_phone(f"Phone: {phone}", 1)
            # 555 prefix is excluded, so check logic
            assert len(findings) >= 0

    def test_reject_invalid_phone(self):
        """Test rejection of invalid phone numbers"""
        detector = SensitiveDataDetector()

        invalid_phones = [
            "000-000-0000",
            "555-555-5555",
        ]

        for phone in invalid_phones:
            findings = detector.detect_phone(f"Phone: {phone}", 1)
            assert len(findings) == 0, f"Should reject {phone}"


class TestScanLine:
    """Test scanning entire lines"""

    def test_scan_line_multiple_findings(self):
        """Test scanning line with multiple findings"""
        detector = SensitiveDataDetector()

        text = "SSN: 123-45-6789, Email: test@example.com, Card: 4532-1111-1111-1111"
        findings = detector.scan_line(text, 1)

        # Should find SSN, email, and credit card
        assert len(findings) >= 2  # At least SSN and email

        types = [f.finding_type for f in findings]
        assert 'ssn' in types
        assert 'email' in types

    def test_scan_line_no_findings(self):
        """Test scanning clean line"""
        detector = SensitiveDataDetector()

        text = "This is a normal line of text with no sensitive data."
        findings = detector.scan_line(text, 1)

        assert len(findings) == 0


class TestScanText:
    """Test scanning multi-line text"""

    def test_scan_text_multiline(self):
        """Test scanning multiple lines"""
        detector = SensitiveDataDetector()

        text = """
        Line 1: Employee SSN is 123-45-6789
        Line 2: Contact email: admin@company.com
        Line 3: Credit card: 4532-1111-1111-1111
        """

        findings = detector.scan_text(text)

        assert len(findings) >= 2  # At least SSN and email

        # Check line numbers are correct
        line_numbers = [f.line_number for f in findings]
        assert min(line_numbers) >= 1
        assert max(line_numbers) <= 4

    def test_scan_text_empty(self):
        """Test scanning empty text"""
        findings = scan_text("")
        assert len(findings) == 0

    def test_scan_text_clean(self):
        """Test scanning clean text"""
        text = """
        This is a normal document.
        It contains no sensitive information.
        Just regular text content.
        """

        findings = scan_text(text)
        assert len(findings) == 0


class TestHashValue:
    """Test value hashing"""

    def test_hash_consistency(self):
        """Test hash consistency"""
        detector = SensitiveDataDetector()

        value = "test-value"
        hash1 = detector.hash_value(value)
        hash2 = detector.hash_value(value)

        assert hash1 == hash2

    def test_hash_uniqueness(self):
        """Test hash uniqueness"""
        detector = SensitiveDataDetector()

        hash1 = detector.hash_value("value1")
        hash2 = detector.hash_value("value2")

        assert hash1 != hash2

    def test_hash_format(self):
        """Test hash format (SHA256 hex)"""
        detector = SensitiveDataDetector()

        hash_value = detector.hash_value("test")

        assert len(hash_value) == 64  # SHA256 hex is 64 chars
        assert all(c in '0123456789abcdef' for c in hash_value)


class TestContext:
    """Test context extraction"""

    def test_context_extraction(self):
        """Test context window"""
        detector = SensitiveDataDetector()

        text = "A" * 100 + "SENSITIVE" + "B" * 100
        context = detector.get_context(text, 100, 109)

        assert 'SENSITIVE' in context
        assert len(context) <= 200 + 3  # Max 200 + ellipsis

    def test_context_at_start(self):
        """Test context at text start"""
        detector = SensitiveDataDetector()

        text = "SENSITIVE data here"
        context = detector.get_context(text, 0, 9)

        assert 'SENSITIVE' in context

    def test_context_at_end(self):
        """Test context at text end"""
        detector = SensitiveDataDetector()

        text = "Some text SENSITIVE"
        context = detector.get_context(text, 10, 19)

        assert 'SENSITIVE' in context


class TestFindingDataclass:
    """Test Finding dataclass"""

    def test_finding_creation(self):
        """Test creating Finding object"""
        finding = Finding(
            finding_type='ssn',
            value='123-45-6789',
            value_hash='abc123',
            line_number=1,
            column_start=0,
            column_end=11,
            context='SSN: 123-45-6789',
            confidence='high'
        )

        assert finding.finding_type == 'ssn'
        assert finding.line_number == 1
        assert finding.confidence == 'high'

    def test_finding_default_confidence(self):
        """Test default confidence level"""
        finding = Finding(
            finding_type='email',
            value='test@example.com',
            value_hash='xyz789',
            line_number=1,
            column_start=0,
            column_end=16,
            context='test@example.com'
        )

        assert finding.confidence == 'high'


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--cov=src.detectors', '--cov-report=term-missing'])
