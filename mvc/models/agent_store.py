"""SQLite task memory scoped to the browser's signed session."""
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from mvc.models.model_errors import TaskConflictError


def utc_now():
    return datetime.now(timezone.utc).isoformat()


class AgentStore:
    def __init__(self, path):
        self.path = str(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            connection.execute('''CREATE TABLE IF NOT EXISTS agent_tasks (
                task_id TEXT PRIMARY KEY, owner_id TEXT NOT NULL,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                revision INTEGER NOT NULL, state_json TEXT NOT NULL)''')
            connection.execute('CREATE INDEX IF NOT EXISTS agent_tasks_owner ON agent_tasks(owner_id, updated_at)')

    @contextmanager
    def connect(self):
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def get(self, task_id, owner_id):
        with self.connect() as connection:
            row = connection.execute('SELECT * FROM agent_tasks WHERE task_id=? AND owner_id=?',
                                     (task_id, owner_id)).fetchone()
        if row is None:
            raise KeyError('Không tìm thấy yêu cầu trong phiên hiện tại.')
        task = json.loads(row['state_json'])
        task['revision'] = row['revision']
        return task

    def save(self, task, owner_id, expected_revision=None):
        now = utc_now()
        task['updated_at'] = now
        task.setdefault('created_at', now)
        task['revision'] = 1 if expected_revision is None else expected_revision + 1
        value = json.dumps(task, ensure_ascii=False, allow_nan=False)
        with self.connect() as connection:
            if expected_revision is None:
                connection.execute('INSERT INTO agent_tasks VALUES (?,?,?,?,?,?)',
                    (task['task_id'], owner_id, task['created_at'], now, task['revision'], value))
            else:
                cursor = connection.execute('''UPDATE agent_tasks SET updated_at=?, revision=?, state_json=?
                    WHERE task_id=? AND owner_id=? AND revision=?''',
                    (now, task['revision'], value, task['task_id'], owner_id, expected_revision))
                if cursor.rowcount != 1:
                    raise TaskConflictError('Yêu cầu đã thay đổi ở một cửa sổ khác. Hãy tải lại kết quả.')

    def history(self, owner_id, limit=20):
        with self.connect() as connection:
            rows = connection.execute('''SELECT state_json FROM agent_tasks
                WHERE owner_id=? ORDER BY updated_at DESC, task_id LIMIT ?''', (owner_id, limit)).fetchall()
        return [json.loads(row['state_json']) for row in rows]

    def clear(self, owner_id):
        with self.connect() as connection:
            cursor = connection.execute('DELETE FROM agent_tasks WHERE owner_id=?', (owner_id,))
        return cursor.rowcount

    def conversation(self, owner_id, conversation_id):
        with self.connect() as connection:
            rows = connection.execute('''SELECT state_json FROM agent_tasks
                WHERE owner_id=? AND json_extract(state_json,'$.conversation_id')=?
                ORDER BY created_at,task_id''',(owner_id,conversation_id)).fetchall()
        return [json.loads(row['state_json']) for row in rows]

    def conversations(self, owner_id):
        with self.connect() as connection:
            rows = connection.execute('''SELECT state_json FROM agent_tasks
                WHERE owner_id=? AND json_extract(state_json,'$.conversation_id') IS NOT NULL
                ORDER BY created_at,task_id''',(owner_id,)).fetchall()
        grouped = {}
        for row in rows:
            task=json.loads(row['state_json'])
            key=task['conversation_id']
            if key not in grouped:
                grouped[key]=dict(conversation_id=key,title=task['query'][:100],
                                 updated_at=task['updated_at'],message_count=0)
            grouped[key]['message_count']+=1
            grouped[key]['updated_at']=max(grouped[key]['updated_at'],task['updated_at'])
        return sorted(grouped.values(),key=lambda item:item['updated_at'],reverse=True)[:30]

    def clear_conversations(self, owner_id):
        with self.connect() as connection:
            cursor=connection.execute('''DELETE FROM agent_tasks WHERE owner_id=?
                AND json_extract(state_json,'$.conversation_id') IS NOT NULL''',(owner_id,))
        return cursor.rowcount
