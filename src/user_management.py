import bcrypt
from typing import Optional, Dict
from sqlite_manager import SQLiteManager

class UserManagement:
    def __init__(self):
        self.db = SQLiteManager()
    
    def _hash_password(self, password: str) -> str:
        """
        Hashes a password using bcrypt and returns the result as a string for a database storage.
        """
        # Encode the plaintext password to bytes (required by bcrypt)
        password_bytes = password.encode('utf-8')
        
        # Generate a salt and hash the password in one step
        hashed_bytes = bcrypt.hashpw(password_bytes, bcrypt.gensalt(rounds=12))
        
        return hashed_bytes.decode('utf-8')
    
    def create_user(self, email: str, username: str, password: str) -> Optional[Dict]:
        if not username or not password:
            return None
        
        pw_hash = self._hash_password(password)
        
        # Check if the username already exists (Optional, but highly recommended)
        existing_user = self.db.get_user_credentials(username, pw_hash)
        if existing_user:
            print(f"Error: User '{username}' already exists.")
            return None
        
        new_user = self.db.create_new_user(email, username, pw_hash)
        return new_user
    
    def get_user(self, username: str):
        existing_user = self.db.get_user_credentials(username, pw_hash)
        