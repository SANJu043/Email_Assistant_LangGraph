import sqlite3
import json
from datetime import datetime
from langchain_core.messages import messages_to_dict, messages_from_dict

DB_PATH = "data/email_agent.db"

class EmailDatabase:
    def __init__(self):
        # check_same_thread=False allows Streamlit threads to share the connection
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        
        # --- THE FIX: Enable Write-Ahead Logging (WAL) ---
        # This prevents "database locked" and "disk I/O" errors
        self.conn.execute("PRAGMA journal_mode=WAL;")
        
        self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()
        
        # 1. Emails Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS emails (
                id TEXT PRIMARY KEY,
                sender TEXT,
                subject TEXT,
                body TEXT,
                status TEXT, 
                graph_state TEXT, 
                summary TEXT,
                last_updated TIMESTAMP
            )
        """)
        
        # 2. Preferences Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS preferences (
                key TEXT PRIMARY KEY,
                value TEXT,
                created_at TIMESTAMP
            )
        """)
        
        self.conn.commit()
        cursor.close()

    # --- PREFERENCES METHODS ---
    def add_preference(self, key, value):
        cursor = self.conn.cursor()
        try:
            cursor.execute("INSERT OR REPLACE INTO preferences (key, value, created_at) VALUES (?, ?, ?)", 
                        (key, value, datetime.now()))
            self.conn.commit()
        finally:
            cursor.close()

    def get_all_preferences(self):
        cursor = self.conn.cursor()
        try:
            cursor.execute("SELECT value FROM preferences")
            rows = cursor.fetchall()
            if not rows:
                return "No specific preferences yet."
            return "\n".join([f"- {row[0]}" for row in rows])
        finally:
            cursor.close()

    def clear_preferences(self):
        cursor = self.conn.cursor()
        try:
            cursor.execute("DELETE FROM preferences")
            self.conn.commit()
        finally:
            cursor.close()

    # --- EMAIL METHODS ---
    def email_exists(self, email_id):
        cursor = self.conn.cursor()
        try:
            cursor.execute("SELECT 1 FROM emails WHERE id = ?", (email_id,))
            return cursor.fetchone() is not None
        finally:
            cursor.close()

    def _serialize_state(self, state):
        if not state: return "{}"
        serializable_state = state.copy()
        if "messages" in serializable_state and serializable_state["messages"]:
            if not isinstance(serializable_state["messages"][0], dict):
                serializable_state["messages"] = messages_to_dict(serializable_state["messages"])
        return json.dumps(serializable_state)

    def _deserialize_state(self, json_str):
        if not json_str: return {}
        try:
            state = json.loads(json_str)
            if "messages" in state and state["messages"]:
                state["messages"] = messages_from_dict(state["messages"])
            return state
        except: return {}

    def save_email(self, email_id, sender, subject, body, status="pending", graph_state=None, summary=""):
        cursor = self.conn.cursor()
        state_json = self._serialize_state(graph_state)
        try:
            cursor.execute("""
                INSERT INTO emails (id, sender, subject, body, status, graph_state, summary, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    status = excluded.status,
                    graph_state = excluded.graph_state,
                    summary = excluded.summary,
                    last_updated = excluded.last_updated
            """, (email_id, sender, subject, body, status, state_json, summary, datetime.now()))
            self.conn.commit()
        finally:
            cursor.close()

    def update_state(self, email_id, graph_state, status=None):
        cursor = self.conn.cursor()
        state_json = self._serialize_state(graph_state)
        try:
            if status:
                cursor.execute("UPDATE emails SET graph_state = ?, status = ?, last_updated = ? WHERE id = ?", 
                            (state_json, status, datetime.now(), email_id))
            else:
                cursor.execute("UPDATE emails SET graph_state = ?, last_updated = ? WHERE id = ?", 
                            (state_json, datetime.now(), email_id))
            self.conn.commit()
        finally:
            cursor.close()

    def get_all_emails(self):
        cursor = self.conn.cursor()
        try:
            cursor.execute("SELECT * FROM emails ORDER BY last_updated DESC")
            rows = cursor.fetchall()
            results = []
            for row in rows:
                results.append({
                    "id": row[0], "sender": row[1], "subject": row[2], "body": row[3],
                    "status": row[4], "graph_state": self._deserialize_state(row[5]), "summary": row[6]
                })
            return results
        finally:
            cursor.close()