"""
GitHub signs webhook deliveries with HMAC-SHA256 over the raw request body,
sent as `X-Hub-Signature-256: sha256=<hex digest>`.

We must:
  - compute the digest over the exact raw bytes (not re-serialized JSON)
  - compare using a constant-time comparison
  - never log the secret or the raw signature
"""
import hashlib
import hmac


def compute_signature(secret: str, raw_body: bytes) -> str:
    digest = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def verify_signature(secret: str, raw_body: bytes, signature_header: str | None) -> bool:
    if not signature_header:
        return False
    expected = compute_signature(secret, raw_body)
    # hmac.compare_digest is constant-time.
    return hmac.compare_digest(expected, signature_header)
