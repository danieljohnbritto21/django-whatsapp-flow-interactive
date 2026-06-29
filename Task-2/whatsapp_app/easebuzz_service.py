"""
Easebuzz Payment Gateway Service

Handles payment initiation, hash generation, callback verification,
and transaction status checks for Easebuzz payment gateway.

Configuration (in Django settings):
    EASEBUZZ_MERCHANT_KEY = 'your_merchant_key'
    EASEBUZZ_SALT = 'your_salt'
    EASEBUZZ_ENV = 'test'  # or 'prod'
"""

import hashlib
import logging
import uuid
import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class EasebuzzService:
    """Service to interact with Easebuzz Payment Gateway."""

    def __init__(self):
        self.merchant_key = getattr(settings, 'EASEBUZZ_MERCHANT_KEY', '')
        self.salt = getattr(settings, 'EASEBUZZ_SALT', '')
        self.env = getattr(settings, 'EASEBUZZ_ENV', 'test')

        if self.env == 'prod':
            self.base_url = 'https://pay.easebuzz.in'
            self.api_url = 'https://dashboard.easebuzz.in'
        else:
            self.base_url = 'https://testpay.easebuzz.in'
            self.api_url = 'https://testdashboard.easebuzz.in'

    @property
    def is_configured(self):
        return bool(self.merchant_key and self.salt)

    def _generate_hash(self, hash_string):
        """Generate SHA-512 hash from the given string."""
        return hashlib.sha512(hash_string.encode('utf-8')).hexdigest()

    def _generate_initiate_hash(self, params):
        """
        Generate hash for payment initiation.
        Sequence: key|txnid|amount|productinfo|firstname|email|udf1|udf2|udf3|udf4|udf5||||||salt
        """
        hash_sequence = '|'.join([
            str(params.get('key', '')).strip(),
            str(params.get('txnid', '')).strip(),
            str(params.get('amount', '')).strip(),
            str(params.get('productinfo', '')).strip(),
            str(params.get('firstname', '')).strip(),
            str(params.get('email', '')).strip(),
            str(params.get('udf1', '')).strip(),
            str(params.get('udf2', '')).strip(),
            str(params.get('udf3', '')).strip(),
            str(params.get('udf4', '')).strip(),
            str(params.get('udf5', '')).strip(),
            '', '', '', '', '',  # udf6-udf10 empty
            str(self.salt).strip(),
        ])
        return self._generate_hash(hash_sequence)

    def _verify_response_hash(self, response_data):
        """
        Verify hash from Easebuzz callback/response.
        Reverse sequence: salt|status||||||udf5|udf4|udf3|udf2|udf1|email|firstname|productinfo|amount|txnid|key
        """
        hash_sequence = '|'.join([
            str(self.salt).strip(),
            str(response_data.get('status', '')).strip(),
            '', '', '', '', '',  # udf10-udf6 empty
            str(response_data.get('udf5', '')).strip(),
            str(response_data.get('udf4', '')).strip(),
            str(response_data.get('udf3', '')).strip(),
            str(response_data.get('udf2', '')).strip(),
            str(response_data.get('udf1', '')).strip(),
            str(response_data.get('email', '')).strip(),
            str(response_data.get('firstname', '')).strip(),
            str(response_data.get('productinfo', '')).strip(),
            str(response_data.get('amount', '')).strip(),
            str(response_data.get('txnid', '')).strip(),
            str(response_data.get('key', self.merchant_key)).strip(),
        ])
        expected_hash = self._generate_hash(hash_sequence)
        return expected_hash == response_data.get('hash', '')

    def generate_txnid(self):
        """Generate a unique transaction ID."""
        return f"THG{uuid.uuid4().hex[:12].upper()}"

    def initiate_payment(self, donation):
        """
        Initiate a payment with Easebuzz.

        Args:
            donation: Donation model instance

        Returns:
            dict: {'success': bool, 'payment_url': str, 'txnid': str, 'access_key': str}
        """
        if not self.is_configured:
            logger.error("Easebuzz not configured — set EASEBUZZ_MERCHANT_KEY and EASEBUZZ_SALT")
            return {'success': False, 'error': 'Easebuzz not configured'}

        txnid = self.generate_txnid()
        callback_url = getattr(settings, 'EASEBUZZ_CALLBACK_URL', '')

        params = {
            'key': self.merchant_key,
            'txnid': txnid,
            'amount': f"{float(donation.amount):.2f}",
            'productinfo': f"Thaagam Foundation - {donation.get_cause_display()}",
            'firstname': donation.full_name,
            'email': donation.email,
            'phone': donation.mobile_number,
            'surl': callback_url,  # Success URL
            'furl': callback_url,  # Failure URL
            'udf1': donation.reference_number,
            'udf2': donation.category or '',
            'udf3': donation.whatsapp_phone_number,
            'udf4': '',
            'udf5': '',
        }

        # Generate hash
        params['hash'] = self._generate_initiate_hash(params)

        try:
            url = f"{self.base_url}/payment/initiateLink"
            logger.info(f"Initiating Easebuzz payment — txnid: {txnid}, amount: {params['amount']}")

            response = requests.post(url, data=params)
            response.raise_for_status()
            result = response.json()

            if result.get('status') == 1:
                access_key = result.get('data')
                payment_url = f"{self.base_url}/pay/{access_key}"

                # Update donation with Easebuzz details
                donation.easebuzz_txnid = txnid
                donation.easebuzz_access_key = access_key
                donation.payment_method = 'EASEBUZZ'
                donation.payment_status = 'INITIATED'
                donation.save()

                logger.info(f"Easebuzz payment initiated — txnid: {txnid}, url: {payment_url}")
                return {
                    'success': True,
                    'payment_url': payment_url,
                    'txnid': txnid,
                    'access_key': access_key,
                }
            else:
                error_msg = result.get('data', 'Unknown error')
                logger.error(f"Easebuzz initiation failed: {error_msg}")
                return {'success': False, 'error': error_msg}

        except requests.RequestException as e:
            logger.error(f"Easebuzz API error: {str(e)}")
            return {'success': False, 'error': str(e)}

    def verify_callback(self, response_data):
        """
        Verify an Easebuzz payment callback.

        Args:
            response_data: POST data from Easebuzz callback

        Returns:
            dict: {'verified': bool, 'status': str, 'txnid': str, ...}
        """
        is_valid = self._verify_response_hash(response_data)

        return {
            'verified': is_valid,
            'txnid': response_data.get('txnid', ''),
            'status': response_data.get('status', ''),
            'amount': response_data.get('amount', ''),
            'easepayid': response_data.get('easepayid', ''),
            'email': response_data.get('email', ''),
            'firstname': response_data.get('firstname', ''),
            'reference_number': response_data.get('udf1', ''),
            'category': response_data.get('udf2', ''),
            'whatsapp_phone': response_data.get('udf3', ''),
        }

    def get_transaction_status(self, txnid):
        """
        Check transaction status via Easebuzz API.

        Args:
            txnid: Transaction ID

        Returns:
            dict: Transaction status details
        """
        if not self.is_configured:
            return {'success': False, 'error': 'Easebuzz not configured'}

        params = {
            'key': self.merchant_key,
            'txnid': txnid,
        }

        hash_string = f"{self.merchant_key}|{txnid}|{self.salt}"
        params['hash'] = self._generate_hash(hash_string)

        try:
            url = f"{self.api_url}/transaction/v1/retrieve"
            response = requests.post(url, data=params)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Easebuzz status check error: {str(e)}")
            return {'success': False, 'error': str(e)}


# Singleton instance
easebuzz_service = EasebuzzService()
