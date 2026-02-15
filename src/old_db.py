import sqlite3
import json
import os

class MemoryManager:
    def __init__(self, db_path="data/agent_memory.db"):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS preferences (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        self.conn.commit()

    def save_preference(self, key, value):
        """Saves or updates a user preference."""
        cursor = self.conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO preferences (key, value) VALUES (?, ?)", (key, value))
        self.conn.commit()
        print(f"🧠 Memory Updated: [{key}] = {value}")

    def get_all_preferences(self):
        """Returns all preferences as a formatted string for the LLM."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT key, value FROM preferences")
        rows = cursor.fetchall()
        
        if not rows:
            return "No prior preferences found."
            
        memory_str = ""
        for key, value in rows:
            memory_str += f"- {key}: {value}\n"
        return memory_str