"""
Event Store - SQLite persistence layer for AG-UI event history
"""
import sqlite3
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import asyncio
from pathlib import Path

logger = logging.getLogger(__name__)


class EventStore:
    """SQLite-based event storage for AG-UI checkpointing"""

    def __init__(self, db_path: str = "agui_events.db"):
        self.db_path = db_path
        self.connection = None
        self._init_db()

    def _init_db(self):
        """Initialize SQLite database and create tables"""
        try:
            self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self.connection.row_factory = sqlite3.Row  # Return rows as dicts

            cursor = self.connection.cursor()

            # Events table - stores all raw events
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    element_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    event_data TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create indexes for events table
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_element_id ON events(element_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_event_type ON events(event_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON events(timestamp)")

            # Threads table - stores thread metadata
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS threads (
                    thread_id TEXT PRIMARY KEY,
                    element_id TEXT NOT NULL UNIQUE,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Messages table - stores accumulated messages
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    message_id TEXT PRIMARY KEY,
                    thread_id TEXT NOT NULL,
                    element_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    status TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    cancelled BOOLEAN DEFAULT FALSE,
                    cancellation_reason TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (thread_id) REFERENCES threads(thread_id)
                )
            """)

            # Thinking events table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS thinking_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    thread_id TEXT NOT NULL,
                    element_id TEXT NOT NULL,
                    message TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (thread_id) REFERENCES threads(thread_id)
                )
            """)

            # Tool executions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tool_executions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    thread_id TEXT NOT NULL,
                    element_id TEXT NOT NULL,
                    tool_name TEXT NOT NULL,
                    tool_args TEXT,
                    tool_result TEXT,
                    status TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (thread_id) REFERENCES threads(thread_id)
                )
            """)

            self.connection.commit()
            logger.info(f"✅ SQLite database initialized at {self.db_path}")

        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    def store_event(self, element_id: str, event_type: str, event_data: Dict[str, Any]):
        """Store a raw event"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                INSERT INTO events (element_id, event_type, event_data, timestamp)
                VALUES (?, ?, ?, ?)
            """, (
                element_id,
                event_type,
                json.dumps(event_data),
                event_data.get('timestamp', datetime.utcnow().isoformat())
            ))
            self.connection.commit()
        except Exception as e:
            logger.error(f"Failed to store event: {e}")
            raise

    def ensure_thread(self, element_id: str, thread_id: str):
        """Ensure thread exists for element"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO threads (thread_id, element_id)
                VALUES (?, ?)
            """, (thread_id, element_id))
            self.connection.commit()
        except Exception as e:
            logger.error(f"Failed to ensure thread: {e}")
            raise

    def store_message_start(self, element_id: str, thread_id: str, message_id: str, timestamp: str):
        """Store new message (start of streaming)"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                INSERT INTO messages (message_id, thread_id, element_id, role, content, status, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (message_id, thread_id, element_id, 'assistant', '', 'streaming', timestamp))
            self.connection.commit()
        except Exception as e:
            logger.error(f"Failed to store message start: {e}")
            raise

    def update_message_content(self, message_id: str, content: str):
        """Update message content (streaming delta)"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                UPDATE messages
                SET content = ?, updated_at = CURRENT_TIMESTAMP
                WHERE message_id = ?
            """, (content, message_id))
            self.connection.commit()
        except Exception as e:
            logger.error(f"Failed to update message content: {e}")
            raise

    def complete_message(self, message_id: str):
        """Mark message as complete"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                UPDATE messages
                SET status = 'complete', updated_at = CURRENT_TIMESTAMP
                WHERE message_id = ?
            """, (message_id,))
            self.connection.commit()
        except Exception as e:
            logger.error(f"Failed to complete message: {e}")
            raise

    def mark_message_cancelled(self, message_id: str, reason: str):
        """Mark a message as cancelled"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                UPDATE messages
                SET cancelled = TRUE,
                    cancellation_reason = ?,
                    status = 'cancelled',
                    updated_at = CURRENT_TIMESTAMP
                WHERE message_id = ?
            """, (reason, message_id))
            self.connection.commit()
            logger.debug(f"💾 Marked message {message_id} as cancelled")
        except Exception as e:
            logger.error(f"Failed to mark message as cancelled: {e}")
            raise

    def store_thinking(self, element_id: str, thread_id: str, message: str, timestamp: str):
        """Store thinking event"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                INSERT INTO thinking_events (thread_id, element_id, message, timestamp)
                VALUES (?, ?, ?, ?)
            """, (thread_id, element_id, message, timestamp))
            self.connection.commit()
        except Exception as e:
            logger.error(f"Failed to store thinking: {e}")
            raise

    def store_tool_start(self, element_id: str, thread_id: str, tool_name: str, tool_args: Dict, start_time: str):
        """Store tool execution start"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                INSERT INTO tool_executions (thread_id, element_id, tool_name, tool_args, status, start_time)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (thread_id, element_id, tool_name, json.dumps(tool_args), 'running', start_time))
            self.connection.commit()
        except Exception as e:
            logger.error(f"Failed to store tool start: {e}")
            raise

    def complete_tool(self, element_id: str, tool_name: str, result: Any, end_time: str):
        """Complete tool execution"""
        try:
            cursor = self.connection.cursor()
            # Find the most recent running tool with this name for this element
            cursor.execute("""
                UPDATE tool_executions
                SET status = 'complete',
                    tool_result = ?,
                    end_time = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = (
                    SELECT id FROM tool_executions
                    WHERE element_id = ? AND tool_name = ? AND status = 'running'
                    ORDER BY start_time DESC
                    LIMIT 1
                )
            """, (json.dumps(result) if result else None, end_time, element_id, tool_name))
            self.connection.commit()
        except Exception as e:
            logger.error(f"Failed to complete tool: {e}")
            raise

    def get_thread_history(self, element_id: str) -> Optional[Dict[str, Any]]:
        """Get complete history for an element"""
        try:
            cursor = self.connection.cursor()

            # Get thread ID
            cursor.execute("SELECT thread_id FROM threads WHERE element_id = ?", (element_id,))
            thread_row = cursor.fetchone()
            if not thread_row:
                return None

            thread_id = thread_row['thread_id']

            # Get messages
            cursor.execute("""
                SELECT message_id as id, role, content, status, timestamp,
                       cancelled, cancellation_reason as cancellationReason
                FROM messages
                WHERE thread_id = ?
                ORDER BY timestamp ASC
            """, (thread_id,))
            messages = [dict(row) for row in cursor.fetchall()]

            # Get thinking events
            cursor.execute("""
                SELECT message, timestamp
                FROM thinking_events
                WHERE thread_id = ?
                ORDER BY timestamp ASC
            """, (thread_id,))
            thinking = [dict(row) for row in cursor.fetchall()]

            # Get tool executions
            cursor.execute("""
                SELECT tool_name as name, tool_args as args, tool_result as result,
                       status, start_time as startTime, end_time as endTime
                FROM tool_executions
                WHERE thread_id = ?
                ORDER BY start_time ASC
            """, (thread_id,))
            tools = []
            for row in cursor.fetchall():
                tool = dict(row)
                # Parse JSON fields
                if tool['args']:
                    tool['args'] = json.loads(tool['args'])
                if tool['result']:
                    tool['result'] = json.loads(tool['result'])
                tools.append(tool)

            return {
                'threadId': thread_id,
                'messages': messages,
                'thinking': thinking,
                'tools': tools
            }

        except Exception as e:
            logger.error(f"Failed to get thread history: {e}")
            raise

    def clear_element_history(self, element_id: str):
        """Clear all history for an element"""
        try:
            cursor = self.connection.cursor()

            # Get thread_id first
            cursor.execute("SELECT thread_id FROM threads WHERE element_id = ?", (element_id,))
            thread_row = cursor.fetchone()
            if not thread_row:
                return

            thread_id = thread_row['thread_id']

            # Delete in correct order (foreign key constraints)
            cursor.execute("DELETE FROM events WHERE element_id = ?", (element_id,))
            cursor.execute("DELETE FROM thinking_events WHERE thread_id = ?", (thread_id,))
            cursor.execute("DELETE FROM tool_executions WHERE thread_id = ?", (thread_id,))
            cursor.execute("DELETE FROM messages WHERE thread_id = ?", (thread_id,))
            cursor.execute("DELETE FROM threads WHERE thread_id = ?", (thread_id,))

            self.connection.commit()
            logger.info(f"🗑️ Cleared SQLite history for element: {element_id}")

        except Exception as e:
            logger.error(f"Failed to clear element history: {e}")
            raise

    def clear_all_history(self):
        """Clear all history from database"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("DELETE FROM events")
            cursor.execute("DELETE FROM thinking_events")
            cursor.execute("DELETE FROM tool_executions")
            cursor.execute("DELETE FROM messages")
            cursor.execute("DELETE FROM threads")
            self.connection.commit()
            logger.info(f"🗑️ Cleared all SQLite history")

        except Exception as e:
            logger.error(f"Failed to clear all history: {e}")
            raise

    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            logger.info("SQLite connection closed")
