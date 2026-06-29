from django.core.management.base import BaseCommand
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
import os

class Command(BaseCommand):
    help = 'Generates a 2048-bit RSA key pair for WhatsApp Flow Data Endpoint'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.NOTICE('Generating 2048-bit RSA key pair...'))

        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )

        # Get private key PEM
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        )

        # Get public key PEM
        public_key = private_key.public_key()
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )

        # Output directory
        output_dir = 'flow_keys'
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # Save to files
        private_key_path = os.path.join(output_dir, 'private_key.pem')
        public_key_path = os.path.join(output_dir, 'public_key.pem')

        with open(private_key_path, 'wb') as f:
            f.write(private_pem)

        with open(public_key_path, 'wb') as f:
            f.write(public_pem)

        self.stdout.write(self.style.SUCCESS(f'Keys generated successfully in /{output_dir}'))
        
        self.stdout.write('\n' + '='*50 + '\n')
        self.stdout.write(self.style.WARNING('STEP 1: ADD TO SETTINGS.PY'))
        self.stdout.write('Copy the exact contents of private_key.pem and set it as FLOW_PRIVATE_KEY in your settings.py:')
        self.stdout.write('\nFLOW_PRIVATE_KEY = """')
        self.stdout.write(private_pem.decode('utf-8').strip())
        self.stdout.write('"""\n')
        
        self.stdout.write('\n' + '='*50 + '\n')
        self.stdout.write(self.style.WARNING('STEP 2: UPLOAD TO META'))
        self.stdout.write('Open public_key.pem and upload its contents to your Meta Business Manager WhatsApp Flow Data Endpoint configuration.')
        self.stdout.write('='*50 + '\n')
