import json
from typing import Optional
import hashlib
import bcrypt

class HelperFunctions:
    # Fingerprint helper
    def compute_device_id(fingerprint: dict) -> Optional[str]:
        try:
                if not fingerprint:
                    return None
                j = json.dumps(fingerprint, sort_keys=True)
                return hashlib.sha256(j.encode()).hexdigest()
        except Exception as e:
            print(f"Error getting compute device id: {e}")
            
    # Password helper
    def hash_password(password: str) -> bytes:
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt())

    def check_password(password: str, pw_hash: bytes) -> bool:
        try:
            return bcrypt.checkpw(password.encode(), pw_hash)
        except Exception:
            return False