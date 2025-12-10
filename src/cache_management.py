from sqlite_manager import SQLiteManager
import streamlit as st

class CacheManagement:
    def __init__(self, db=SQLiteManager):
        self.db = db
    
    def get_db(self):
        return self.db._connect()
    
    