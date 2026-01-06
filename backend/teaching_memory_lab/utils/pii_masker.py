"""
PII (Personally Identifiable Information) masker for teaching.

Demonstrates simple pattern-based PII detection and masking before
messages are persisted or included in summaries.

Production systems should use more sophisticated NER models.
"""
import re
from typing import Dict, Any
import hashlib


# PII patterns (simplified for teaching)
EMAIL_PATTERN = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
PHONE_PATTERN = r'\b(?:\+?1[-.]?)?\(?([0-9]{3})\)?[-.]?([0-9]{3})[-.]?([0-9]{4})\b'
IBAN_PATTERN = r'\b[A-Z]{2}[0-9]{2}[A-Z0-9]{11,30}\b'
CREDIT_CARD_PATTERN = r'\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13})\b'


class PIIMasker:
    """
    PII masker with placeholder or pseudonymization modes.
    
    Modes:
    - placeholder: Replace with [EMAIL], [PHONE], etc.
    - pseudonymize: Replace with salted hash for consistency
    """
    
    def __init__(self, mode: str = "placeholder", salt: str = "teaching-salt"):
        """
        Args:
            mode: "placeholder" or "pseudonymize"
            salt: Salt for hashing in pseudonymize mode
        """
        self.mode = mode
        self.salt = salt
        self.patterns = {
            'email': EMAIL_PATTERN,
            'phone': PHONE_PATTERN,
            'iban': IBAN_PATTERN,
            'credit_card': CREDIT_CARD_PATTERN,
        }
    
    def mask_text(self, text: str) -> Dict[str, Any]:
        """
        Mask PII in text.
        
        Returns:
            {
                "masked_text": str with PII masked,
                "pii_found": list of {"type": str, "count": int}
            }
        """
        masked_text = text
        pii_found = []
        
        for pii_type, pattern in self.patterns.items():
            matches = re.findall(pattern, masked_text)
            if matches:
                pii_found.append({
                    "type": pii_type,
                    "count": len(matches)
                })
                
                if self.mode == "placeholder":
                    # Replace with placeholder
                    placeholder = f"[{pii_type.upper()}]"
                    masked_text = re.sub(pattern, placeholder, masked_text)
                elif self.mode == "pseudonymize":
                    # Replace with consistent hash
                    for match in set(matches):
                        match_str = match if isinstance(match, str) else ''.join(match)
                        hashed = self._hash_value(match_str)
                        masked_text = masked_text.replace(match_str, f"[{pii_type.upper()}:{hashed}]")
        
        return {
            "masked_text": masked_text,
            "pii_found": pii_found
        }
    
    def _hash_value(self, value: str) -> str:
        """Create consistent pseudonymized value using salted hash"""
        content = f"{self.salt}:{value}"
        return hashlib.sha256(content.encode()).hexdigest()[:8]


# Singleton instance for convenience
default_masker = PIIMasker()


def mask_pii(text: str, mode: str = "placeholder") -> Dict[str, Any]:
    """
    Convenience function to mask PII in text.
    
    Returns dict with masked_text and pii_found list.
    """
    masker = PIIMasker(mode=mode)
    return masker.mask_text(text)
