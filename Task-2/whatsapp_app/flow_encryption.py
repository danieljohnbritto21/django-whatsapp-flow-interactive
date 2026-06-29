"""
WhatsApp Flow Encryption Service

Handles RSA + AES-GCM encryption/decryption for WhatsApp Flow data endpoints.
WhatsApp sends encrypted payloads that must be decrypted using a private RSA key
and AES-GCM, and responses must be encrypted back using the same AES key with
a flipped IV.

Requirements:
    pip install cryptography
"""

import json
import logging
from base64 import b64decode, b64encode

from cryptography.hazmat.primitives.asymmetric.padding import OAEP, MGF1
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from django.conf import settings

logger = logging.getLogger(__name__)


class FlowEncryptionService:
    """Encrypt and decrypt WhatsApp Flow data endpoint payloads."""

    def __init__(self):
        private_key_pem = getattr(settings, 'FLOW_PRIVATE_KEY', '')
        if private_key_pem:
            if isinstance(private_key_pem, str):
                private_key_pem = private_key_pem.encode('utf-8')
            self._private_key = load_pem_private_key(private_key_pem, password=None)
        else:
            self._private_key = None
            logger.warning("FLOW_PRIVATE_KEY not configured — Flow encryption disabled")

    @property
    def is_configured(self):
        return self._private_key is not None

    def decrypt_request(self, encrypted_flow_data_b64, encrypted_aes_key_b64, initial_vector_b64):
        """
        Decrypt an incoming WhatsApp Flow request.

        Args:
            encrypted_flow_data_b64: Base64-encoded AES-GCM encrypted payload
            encrypted_aes_key_b64: Base64-encoded RSA-encrypted AES key
            initial_vector_b64: Base64-encoded initialization vector

        Returns:
            tuple: (decrypted_data_dict, aes_key_bytes, iv_bytes)
        """
        if not self.is_configured:
            raise RuntimeError("Flow encryption not configured — set FLOW_PRIVATE_KEY in settings")

        # Decode from base64
        encrypted_flow_data = b64decode(encrypted_flow_data_b64)
        encrypted_aes_key = b64decode(encrypted_aes_key_b64)
        iv = b64decode(initial_vector_b64)

        # Step 1: Decrypt the AES key using RSA-OAEP
        aes_key = self._private_key.decrypt(
            encrypted_aes_key,
            OAEP(
                mgf=MGF1(algorithm=SHA256()),
                algorithm=SHA256(),
                label=None
            )
        )

        # Step 2: Decrypt the flow data using AES-128-GCM
        # Last 16 bytes are the GCM authentication tag
        encrypted_body = encrypted_flow_data[:-16]
        auth_tag = encrypted_flow_data[-16:]

        decryptor = Cipher(
            algorithms.AES(aes_key),
            modes.GCM(iv, auth_tag)
        ).decryptor()

        decrypted_bytes = decryptor.update(encrypted_body) + decryptor.finalize()
        decrypted_data = json.loads(decrypted_bytes.decode('utf-8'))

        logger.info(f"Flow request decrypted — action: {decrypted_data.get('action')}")
        return decrypted_data, aes_key, iv

    def encrypt_response(self, response_dict, aes_key, iv):
        """
        Encrypt a response to send back to WhatsApp.

        The IV is flipped (bitwise NOT) as required by WhatsApp Flows spec.

        Args:
            response_dict: Dictionary to encrypt as JSON
            aes_key: AES key from the decrypted request
            iv: IV from the decrypted request (will be flipped)

        Returns:
            str: Base64-encoded encrypted response
        """
        # Flip the IV (bitwise NOT of each byte)
        flipped_iv = bytes([b ^ 0xFF for b in iv])

        # Encrypt with AES-128-GCM using the flipped IV
        encryptor = Cipher(
            algorithms.AES(aes_key),
            modes.GCM(flipped_iv)
        ).encryptor()

        response_json = json.dumps(response_dict).encode('utf-8')
        ciphertext = encryptor.update(response_json) + encryptor.finalize()

        # Append the GCM tag to the ciphertext and encode as base64
        encrypted_response = b64encode(ciphertext + encryptor.tag).decode('utf-8')

        logger.info("Flow response encrypted successfully")
        return encrypted_response


# Singleton instance
flow_encryption = FlowEncryptionService()
