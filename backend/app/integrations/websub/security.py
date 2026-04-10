import hashlib
import hmac
from typing import Optional
from app.loguru_config import logger

_SUPPORTED_ALGOS = {
    "sha256": hashlib.sha256,
    "sha1": hashlib.sha1,
}

def verify_hmac_signature(
    body: bytes,
    signature_header: Optional[str],
    secret: str,
    *,
    preferred_header: Optional[str] = None,
) -> bool:
    if not secret:
        return True
    
    header_to_verify = preferred_header or signature_header
    if not header_to_verify:
        logger.warning("HMAC secret 已配置但请求缺少签名头")
        return False

    algo_name, _, sig_hex = header_to_verify.partition("=")
    algo_name = algo_name.lower()
    
    hash_fn = _SUPPORTED_ALGOS.get(algo_name)
    if hash_fn is None:
        logger.warning("不支持的 HMAC 算法: %s", algo_name)
        return False

    expected = hmac.new(secret.encode("utf-8"), body, hash_fn).hexdigest()
    
    try:
        return hmac.compare_digest(expected, sig_hex)
    except (TypeError, ValueError):
        return False