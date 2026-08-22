
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
import base64

priv_key = ec.generate_private_key(ec.SECP256R1())

priv_pem = priv_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.TraditionalOpenSSL,
    encryption_algorithm=serialization.NoEncryption(),
).decode().strip()

pub_bytes = priv_key.public_key().public_bytes(
    encoding=serialization.Encoding.X962,
    format=serialization.PublicFormat.UncompressedPoint,
)
pub_b64 = base64.urlsafe_b64encode(pub_bytes).rstrip(b'=').decode()

print("\n✅ Copy these into your .env file:\n")
print(f"VAPID_PUBLIC_KEY={pub_b64}")
print(f"VAPID_PRIVATE_KEY={priv_pem}")
print("\nAlso set:  VAPID_EMAIL=mailto:your@email.com\n")
