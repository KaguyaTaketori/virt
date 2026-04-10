import hmac
import hashlib
from app.loguru_config import logger

def verify_hmac_signature(body: bytes, signature_header: str | None, secret: str) -> bool:
    if not secret:
        return True
    if not signature_header:
        logger.warning("HMAC secret 已配置但请求缺少 X-Hub-Signature")
        return False

    algo, _, sig_hex = signature_header.partition("=")
    if algo != "sha1":
        return False

    expected = hmac.new(secret.encode(), body, hashlib.sha1).hexdigest()
    return hmac.compare_digest(expected, sig_hex)