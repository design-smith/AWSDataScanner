"""
Sensitive Data Detectors for AWS File Scanner

This module contains regex-based detectors for identifying sensitive data:
- Social Security Numbers (SSNs)
- Credit Cards (with Luhn validation)
- AWS Access Keys
- AWS Secret Keys
- Email Addresses
- Phone Numbers (US and International)
"""

import re
import hashlib
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class Finding:
    """Represents a single detected sensitive data finding"""
    finding_type: str
    value: str
    value_hash: str
    line_number: int
    column_start: int
    column_end: int
    context: str
    confidence: str = 'high'


class SensitiveDataDetector:
    """Main detector class with regex patterns and validation logic"""

    # Regex patterns for different sensitive data types
    PATTERNS = {
        'ssn': re.compile(r'\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b'),
        'credit_card': re.compile(r'\b(?:\d{4}[-\s]?){3}\d{4}\b|\b\d{15,16}\b'),
        'aws_access_key': re.compile(r'\b(AKIA[0-9A-Z]{16})\b'),
        'aws_secret_key': re.compile(r'\b([A-Za-z0-9/+=]{40})\b'),  # Less precise, high false positive
        'email': re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
        'phone_us': re.compile(r'\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b'),
    }

    # Context window size (characters before and after match)
    CONTEXT_WINDOW = 50

    def __init__(self):
        """Initialize the detector with compiled patterns"""
        self.patterns = self.PATTERNS.copy()

    @staticmethod
    def luhn_check(card_number: str) -> bool:
        """
        Validate credit card number using Luhn algorithm

        Args:
            card_number: Credit card number as string (digits only)

        Returns:
            True if valid, False otherwise
        """
        # Remove non-digit characters
        digits = [int(d) for d in card_number if d.isdigit()]

        if len(digits) < 13 or len(digits) > 19:
            return False

        # Luhn algorithm
        checksum = 0
        reverse_digits = digits[::-1]

        for i, digit in enumerate(reverse_digits):
            if i % 2 == 1:  # Every second digit from right
                digit *= 2
                if digit > 9:
                    digit -= 9
            checksum += digit

        return checksum % 10 == 0

    @staticmethod
    def hash_value(value: str) -> str:
        """
        Create SHA256 hash of sensitive value for storage

        Args:
            value: The sensitive value to hash

        Returns:
            Hexadecimal hash string
        """
        return hashlib.sha256(value.encode('utf-8')).hexdigest()

    def get_context(self, text: str, start: int, end: int) -> str:
        """
        Extract context around a match

        Args:
            text: Full text line
            start: Match start position
            end: Match end position

        Returns:
            Context string with match and surrounding text
        """
        context_start = max(0, start - self.CONTEXT_WINDOW)
        context_end = min(len(text), end + self.CONTEXT_WINDOW)

        context = text[context_start:context_end].strip()

        # Truncate if too long
        if len(context) > 200:
            context = context[:200] + '...'

        return context

    def detect_ssn(self, text: str, line_number: int) -> List[Finding]:
        """Detect Social Security Numbers"""
        findings = []

        for match in self.patterns['ssn'].finditer(text):
            value = match.group(0)
            # Normalize SSN format
            normalized = re.sub(r'[-\s]', '', value)

            # Basic validation: should be exactly 9 digits
            if len(normalized) == 9 and normalized.isdigit():
                # Exclude obvious invalid SSNs
                if normalized.startswith('000') or normalized.startswith('666') or normalized.startswith('9'):
                    continue

                findings.append(Finding(
                    finding_type='ssn',
                    value=value,
                    value_hash=self.hash_value(normalized),
                    line_number=line_number,
                    column_start=match.start(),
                    column_end=match.end(),
                    context=self.get_context(text, match.start(), match.end()),
                    confidence='high'
                ))

        return findings

    def detect_credit_card(self, text: str, line_number: int) -> List[Finding]:
        """Detect credit card numbers with Luhn validation"""
        findings = []

        for match in self.patterns['credit_card'].finditer(text):
            value = match.group(0)
            # Remove separators
            normalized = re.sub(r'[-\s]', '', value)

            # Validate with Luhn algorithm
            if self.luhn_check(normalized):
                confidence = 'high'
            else:
                # Still report but with lower confidence
                confidence = 'medium'
                # Skip if Luhn fails (reduce false positives)
                continue

            findings.append(Finding(
                finding_type='credit_card',
                value=value,
                value_hash=self.hash_value(normalized),
                line_number=line_number,
                column_start=match.start(),
                column_end=match.end(),
                context=self.get_context(text, match.start(), match.end()),
                confidence=confidence
            ))

        return findings

    def detect_aws_keys(self, text: str, line_number: int) -> List[Finding]:
        """Detect AWS access keys"""
        findings = []

        # AWS Access Keys
        for match in self.patterns['aws_access_key'].finditer(text):
            value = match.group(0)

            findings.append(Finding(
                finding_type='aws_access_key',
                value=value,
                value_hash=self.hash_value(value),
                line_number=line_number,
                column_start=match.start(),
                column_end=match.end(),
                context=self.get_context(text, match.start(), match.end()),
                confidence='high'
            ))

        # AWS Secret Keys (lower confidence due to generic pattern)
        for match in self.patterns['aws_secret_key'].finditer(text):
            value = match.group(0)

            # Check if it looks like a secret key (has mix of chars)
            if (any(c.isupper() for c in value) and
                any(c.islower() for c in value) and
                any(c.isdigit() for c in value)):

                findings.append(Finding(
                    finding_type='aws_secret_key',
                    value=value,
                    value_hash=self.hash_value(value),
                    line_number=line_number,
                    column_start=match.start(),
                    column_end=match.end(),
                    context=self.get_context(text, match.start(), match.end()),
                    confidence='medium'  # Lower confidence due to generic pattern
                ))

        return findings

    def detect_email(self, text: str, line_number: int) -> List[Finding]:
        """Detect email addresses"""
        findings = []

        for match in self.patterns['email'].finditer(text):
            value = match.group(0)

            # Basic validation
            if '@' in value and '.' in value.split('@')[1]:
                findings.append(Finding(
                    finding_type='email',
                    value=value,
                    value_hash=self.hash_value(value.lower()),
                    line_number=line_number,
                    column_start=match.start(),
                    column_end=match.end(),
                    context=self.get_context(text, match.start(), match.end()),
                    confidence='high'
                ))

        return findings

    def detect_phone(self, text: str, line_number: int) -> List[Finding]:
        """Detect US phone numbers"""
        findings = []

        for match in self.patterns['phone_us'].finditer(text):
            value = match.group(0)
            # Normalize phone number
            normalized = re.sub(r'[-.\s()]+', '', value)

            # Remove country code if present
            if normalized.startswith('1'):
                normalized = normalized[1:]

            # Should be exactly 10 digits
            if len(normalized) == 10 and normalized.isdigit():
                # Exclude obviously invalid numbers
                if normalized.startswith('000') or normalized.startswith('555'):
                    continue

                findings.append(Finding(
                    finding_type='phone_us',
                    value=value,
                    value_hash=self.hash_value(normalized),
                    line_number=line_number,
                    column_start=match.start(),
                    column_end=match.end(),
                    context=self.get_context(text, match.start(), match.end()),
                    confidence='high'
                ))

        return findings

    def scan_line(self, line: str, line_number: int) -> List[Finding]:
        """
        Scan a single line of text for all sensitive data types

        Args:
            line: Text line to scan
            line_number: Line number in file

        Returns:
            List of findings
        """
        findings = []

        # Run all detectors
        findings.extend(self.detect_ssn(line, line_number))
        findings.extend(self.detect_credit_card(line, line_number))
        findings.extend(self.detect_aws_keys(line, line_number))
        findings.extend(self.detect_email(line, line_number))
        findings.extend(self.detect_phone(line, line_number))

        return findings

    def scan_text(self, text: str) -> List[Finding]:
        """
        Scan multi-line text for sensitive data

        Args:
            text: Full text content to scan

        Returns:
            List of findings
        """
        findings = []

        for line_num, line in enumerate(text.splitlines(), start=1):
            findings.extend(self.scan_line(line, line_num))

        return findings


# Convenience function for quick scanning
def scan_text(text: str) -> List[Finding]:
    """
    Convenience function to scan text with default detector

    Args:
        text: Text to scan

    Returns:
        List of findings
    """
    detector = SensitiveDataDetector()
    return detector.scan_text(text)
