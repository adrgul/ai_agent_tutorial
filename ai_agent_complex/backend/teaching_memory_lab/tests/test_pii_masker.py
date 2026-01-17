"""Test suite for PII masking."""

import pytest
from ..utils.pii_masker import PIIMasker, mask_pii


def test_mask_email_placeholder():
    """Test email masking with placeholder mode"""
    masker = PIIMasker(mode="placeholder")
    
    text = "Contact me at john.doe@example.com for details."
    result = masker.mask_pii(text)
    
    assert "[EMAIL]" in result
    assert "john.doe@example.com" not in result


def test_mask_email_pseudonymize():
    """Test email masking with pseudonymize mode"""
    masker = PIIMasker(mode="pseudonymize")
    
    text = "Contact me at john.doe@example.com for details."
    result = masker.mask_pii(text)
    
    # Should contain a hash, not the original email
    assert "john.doe@example.com" not in result
    assert "email_" in result.lower()


def test_mask_phone_placeholder():
    """Test phone number masking"""
    masker = PIIMasker(mode="placeholder")
    
    text = "Call me at +1-555-123-4567 or 555.987.6543"
    result = masker.mask_pii(text)
    
    assert "[PHONE]" in result
    assert "555-123-4567" not in result
    assert "555.987.6543" not in result


def test_mask_iban_placeholder():
    """Test IBAN masking"""
    masker = PIIMasker(mode="placeholder")
    
    text = "Transfer to GB82WEST12345698765432"
    result = masker.mask_pii(text)
    
    assert "[IBAN]" in result
    assert "GB82WEST12345698765432" not in result


def test_mask_credit_card_placeholder():
    """Test credit card masking"""
    masker = PIIMasker(mode="placeholder")
    
    text = "Card: 4532-1234-5678-9010"
    result = masker.mask_pii(text)
    
    assert "[CREDIT_CARD]" in result
    assert "4532-1234-5678-9010" not in result


def test_mask_multiple_pii_types():
    """Test masking multiple PII types in one text"""
    masker = PIIMasker(mode="placeholder")
    
    text = """
    Contact: john@example.com
    Phone: +1-555-1234
    Card: 4532123456789010
    """
    result = masker.mask_pii(text)
    
    assert "[EMAIL]" in result
    assert "[PHONE]" in result
    assert "[CREDIT_CARD]" in result
    assert "john@example.com" not in result


def test_no_pii_found():
    """Test text with no PII"""
    masker = PIIMasker(mode="placeholder")
    
    text = "This is a normal message with no sensitive information."
    result = masker.mask_pii(text)
    
    # Should be unchanged
    assert result == text


def test_pseudonymize_consistent():
    """Test that pseudonymization is consistent (same input -> same hash)"""
    masker = PIIMasker(mode="pseudonymize", salt="test_salt")
    
    text1 = "Email: test@example.com"
    text2 = "Email: test@example.com"
    
    result1 = masker.mask_pii(text1)
    result2 = masker.mask_pii(text2)
    
    # Should produce same hash
    assert result1 == result2


def test_pseudonymize_different_for_different_values():
    """Test that different values get different hashes"""
    masker = PIIMasker(mode="pseudonymize", salt="test_salt")
    
    text1 = "Email: alice@example.com"
    text2 = "Email: bob@example.com"
    
    result1 = masker.mask_pii(text1)
    result2 = masker.mask_pii(text2)
    
    # Should produce different hashes
    assert result1 != result2


def test_mask_pii_convenience_function():
    """Test the convenience function mask_pii()"""
    text = "Contact: john@example.com, Phone: +1-555-1234"
    result = mask_pii(text)
    
    assert "[EMAIL]" in result
    assert "[PHONE]" in result
    assert "john@example.com" not in result


def test_empty_text():
    """Test masking empty text"""
    masker = PIIMasker()
    
    result = masker.mask_pii("")
    assert result == ""


def test_none_text():
    """Test masking None"""
    masker = PIIMasker()
    
    result = masker.mask_pii(None)
    assert result == ""
