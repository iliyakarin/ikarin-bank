"""Security and encryption utilities for data protection.

This module provides tools for encrypting and decrypting sensitive fields
in data payloads, primarily used for Kafka message security.
"""
import logging
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)

# Sensitive fields that ARE encrypted in Kafka messages
SENSITIVE_FIELDS = {
    "sender_email", 
    "recipient_email", 
    "target_email", 
    "email", 
    "first_name", 
    "last_name", 
    "ip", 
    "user_agent"
}

def encrypt_value(value: str, key: str) -> str:
    """Encrypts a string using Fernet symmetric encryption.

    Args:
        value (str): The string to encrypt.
        key (str): The Fernet encryption key.

    Returns:
        str: The encrypted string as a base64 encoded string.
    """
    if not key:
        raise ValueError("Encryption key is required.")
    cipher = Fernet(key.encode())
    return cipher.encrypt(value.encode()).decode()

def decrypt_value(token: str, key: str) -> str:
    """Decrypts a Fernet-encrypted string.

    Args:
        token (str): The encrypted string.
        key (str): The Fernet encryption key.

    Returns:
        str: The decrypted string.
    """
    if not key:
        raise ValueError("Decryption key is required.")
    cipher = Fernet(key.encode())
    return cipher.decrypt(token.encode()).decode()

def decrypt_payload(payload: dict, key: str) -> dict:
    """Recursively decrypts sensitive fields in a dictionary.

    Uses Fernet symmetric encryption to decrypt fields marked as sensitive
    if they have the 'enc_' prefix.

    Args:
        payload (dict): The dictionary containing potentially encrypted fields.
        key (str): The Fernet encryption key.

    Returns:
        dict: A new dictionary with sensitive fields decrypted.
    """
    try:
        decrypted_payload = payload.copy()
        
        for k, v in decrypted_payload.items():
            if k in SENSITIVE_FIELDS and isinstance(v, str) and v.startswith("enc_"):
                try:
                    # 'enc_' prefix is removed before decryption
                    decrypted_payload[k] = decrypt_value(v[4:], key)
                except Exception as e:
                    logger.warning(f"Failed to decrypt field '{k}': {e}")
            elif isinstance(v, dict):
                decrypted_payload[k] = decrypt_payload(v, key)
                
        return decrypted_payload
    except Exception as e:
        logger.error(f"Decryption error: {e}")
        return payload
