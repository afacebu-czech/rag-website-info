import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union, Literal
import uuid
import src.config as config

if config.USE_OLLAMA:
    DB_PATH = "./vectorstore/sql_lite/rag_chatbot.db"
else:
    DB_PATH = "./database/structured/rag_chatbot.db"

class SQLiteManager:
    """
    General-purpose SQLite manager that can:
    - Execute any SQL query
    - Handle table creation and CRUD operations
    - Provide conversation-specific helper methods (for chat history)
    """
    
    def __init__(self, db_path: str=DB_PATH):
        self.db_path = db_path
        self._init_default_schema()
        
    # --- Core Connection Utilities ---
    def _connect(self):
        """Create and return a SQLite connection."""
        return sqlite3.connect(self.db_path, check_same_thread=False)
    
    def execute(
        self,
        query: str,
        params: Union[Tuple, List, Dict] = (),
        fetch: str = "none",
        as_dict: bool = False
    ) -> Optional[Union[List[Tuple], Tuple]]:
        """
        Generic SQL executor.
        fetch: 'none' | 'one' | 'all'
        """
        with self._connect() as conn:
            if as_dict:
                conn.row_factory = sqlite3.Row
            
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            
            if fetch == 'one':
                row = cursor.fetchone()
                return dict(row) if (row and as_dict) else row
            elif fetch == 'all':
                rows = cursor.fetchall()
                return [dict(r) for r in rows] if as_dict else rows
        
    # --- CRUD Utilities ---
    def insert(
        self,
        table: str,
        data: Dict[str, Any]
        ) -> int:
        """Insert a row into a table and return its ID."""
        
        keys = ", ".join(data.keys())
        placeholders = ", ".join(["?" for _ in data])
        query = f"INSERT INTO {table} ({keys}) VALUES ({placeholders})"
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(query, tuple(data.values()))
            conn.commit()
            return cursor.lastrowid
        
    def select(
        self,
        table: str,
        where: Optional[str] = None,
        params: Tuple = (),
        columns: str = "*",
        order_by: Optional[str] = None,
        fetch: Literal["all", "one"] = "all"
    ):
        query = f"SELECT {columns} FROM {table}"
        if where:
            query += f" WHERE {where}"
        if order_by:
            query += f" ORDER BY {order_by}"
        return self.execute(query, params, fetch, as_dict=True)
    
    def update(
        self,
        table: str,
        data: Dict[str, Any],
        where: str,
        params: Tuple
    ):
        """Update rows in a table"""
        set_clause = ", ".join([f"{col} = ?" for col in data.keys()])
        values = tuple(data.values()) + params
        query = f"UPDATE {table} SET {set_clause} WHERE {where}"
        self.execute(query, values)
        
    # --- Default Chat Schema ---
    def _init_default_schema(self):
        """Initialize default tables for chat history"""
        with self._connect() as conn:
            conn.executescript("""
                                CREATE TABLE IF NOT EXISTS users (
                                    id TEXT PRIMARY KEY,
                                    username TEXT UNIQUE NOT NULL,
                                    password_hash TEXT NOT NULL,
                                    email TEXT,
                                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                                );
                                
                                CREATE TABLE IF NOT EXISTS conversations (
                                    id TEXT PRIMARY KEY,
                                    user_id TEXT,
                                    title TEXT,
                                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                    FOREIGN KEY(user_id) REFERENCES users (id)
                                );
                                
                                CREATE TABLE IF NOT EXISTS messages (
                                    id TEXT PRIMARY KEY,
                                    conversation_id TEXT NOT NULL,
                                    position INT,
                                    sender TEXT CHECK(sender IN ('user','assistant')),
                                    message TEXT NOT NULL,
                                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                    FOREIGN KEY(conversation_id) REFERENCES conversations (id)
                                );
                                """)
            conn.commit()
            
    def delete_row(
        self,
        table: str,
        condition: str,
        params: tuple
        ) -> None:
        """Delete specific rows based on condition.
        
        Example:
            db.delete_row("users", "id = ?", (1,))
            db.delete_row("users", "username = ?", ("admin",))
        """
        query = f"DELETE FROM {table} WHERE {condition}"
        self.execute(query, params)
        
    def delete_all_rows(self, table: str) -> None:
        """
        Delete all rows in a table (but keep the structure).
        
        Example:
            db.delete_all_rows("users")
        """
        query = f"DELETE FROM {table}"
        self.execute(query)
            
    # --- Chat Conversation Helpers ---
    def create_conversation(
        self,
        conversation_id: str,
        title: str,
        user_id: Optional[str] = None
    ) -> int:
        """Create a new conversation."""
        existing = self.get_conversation_of_user(conversation_id, user_id)
        if not existing:
            return self.insert("conversations", {
                "id": conversation_id,
                "title": title,
                "user_id": user_id,
        })
        
    def add_message(
        self,
        conversation_id: int,
        sender: str,
        message: str
    ):
        """Store a new chat message in SQLite with sequential position"""
        # Get the last position for this conversation
        query = "SELECT COALESCE(MAX(position), 0) FROM messages WHERE conversation_id = ?"
        params = (conversation_id,)
        cursor = self.execute(query, params, "one", as_dict=False)
        last_position = cursor[0] or 0
        new_position = last_position + 1
        
        self.insert("messages", {
            "id": f"MSG_{uuid.uuid4().hex[:12]}",
            "conversation_id": conversation_id,
            "position": new_position,
            "sender": sender,
            "message": message
        })
        
        return new_position
    
    def get_all_messages_from_conversation(self, conversation_id: str) -> List[Dict]:
        """Retrieve all messages for a conversation ordered by position."""
        return self.select(
            "messages",
            where="conversation_id = ?",
            params=(conversation_id,),
            columns="sender, message, created_at",
            fetch="all",
            order_by="position ASC"
        )
        
    def get_all_conversations_of_user(self, user_id: Optional[str] = None) -> List[Dict]:
        """
        Get all conversations from SQLite with metadata.
        Each thread includes: id, title/topic, created_at, message_count.
        """
        if user_id:
            return self.select(
                "conversations",
                where="user_id = ?",
                params=(user_id,),
                columns="id, title, created_at",
                fetch="all"
            )
        return self.select(
            "conversations",
            columns="id, title, created_at",
            fetch="all"
        )
        
    def get_conversation_of_user(self, conversation_id: str, user_id: str) -> Dict:
        """
        Get the conversation of the conversation_id from SQLite.
        Conversation includes: id, user_id, title
        """
        if conversation_id and user_id:
            return self.select(
                "conversations",
                where="id = ?",
                params=(conversation_id,),
                columns="id, title, created_at",
                fetch="one"
            )
        return None
    
    def update_title(self, conversation_id: str, title: str):
        """
        Updates the title of the conversation in SQLite.
        """
        if conversation_id:
            self.update(
                "conversations",
                data={"title": title},
                where="id = ?",
                params=(conversation_id,)
            )
    
    def get_count_message_of_conversation(self, conversation_id: str):
        """Get the number of messages of the conversation"""
        if conversation_id:
            result = self.select(
                "messages",
                where="conversation_id = ?",
                params=(conversation_id,),
                columns="COUNT(conversation_id)",
                fetch="one"
            )
            return next(iter(result.values())) if result else 0
            
    # --- User Helpers
        
def scripts():
    sql = SQLiteManager()

    num_messages = sql.get_count_message_of_conversation(conversation_id="CNV_c0e80ac0b99f")
    print(num_messages)

def main():
    scripts()
    
if __name__ == "__main__":
    main()