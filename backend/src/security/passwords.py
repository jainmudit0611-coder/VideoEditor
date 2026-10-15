import logging
import bcrypt

logger = logging.getLogger("brand-guardian-security-passwords")

def hash_password(password: str) -> str:
    """
    Hashes a plaintext password using bcrypt with automatic salt generation.
    Enforces non-empty input and standard bcrypt byte limits.
    """
    if not password:
        raise ValueError("Password cannot be empty.")
    pw_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pw_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a plaintext password against a stored bcrypt hash.
    Returns False on mismatch or corrupted hash format without leaking details.
    """
    if not plain_password or not hashed_password:
        return False
    try:
        pw_bytes = plain_password.encode("utf-8")[:72]
        hash_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(pw_bytes, hash_bytes)
    except Exception as e:
        logger.debug(f"Password verification encountered error: {e}")
        return False
