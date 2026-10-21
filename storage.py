"""SQLite persistence. Biometric samples never belong in source control."""
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

class Store:
    def __init__(self, path='private/attendance.db'):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.path = str(path)
        with self.connect() as db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS people (
                id INTEGER PRIMARY KEY, code TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL, department TEXT NOT NULL,
                consent_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS samples (
                person_id INTEGER REFERENCES people(id) ON DELETE CASCADE,
                image BLOB NOT NULL);
            CREATE TABLE IF NOT EXISTS attendance (
                person_id INTEGER REFERENCES people(id) ON DELETE CASCADE,
                day TEXT NOT NULL, arrival TEXT NOT NULL, departure TEXT,
                method TEXT NOT NULL, UNIQUE(person_id, day));
            ''')
    @contextmanager
    def connect(self):
        with sqlite3.connect(self.path, timeout=15) as db:
            db.row_factory = sqlite3.Row
            db.execute('PRAGMA foreign_keys=ON')
            yield db
    def people(self):
        with self.connect() as db:
            return [dict(r) for r in db.execute('SELECT p.*, COUNT(s.person_id) samples FROM people p LEFT JOIN samples s ON s.person_id=p.id GROUP BY p.id ORDER BY p.name')]
    def enroll(self, code, name, department, samples, consent):
        if not consent or not code.strip() or not name.strip() or len(samples) < 3:
            raise ValueError('Provide an ID, name, consent, and at least three face samples.')
        with self.connect() as db:
            cur = db.execute('INSERT INTO people(code,name,department,consent_at) VALUES(?,?,?,?)',
                             (code.strip(), name.strip(), department.strip(), datetime.now().astimezone().isoformat()))
            db.executemany('INSERT INTO samples VALUES(?,?)', [(cur.lastrowid, s) for s in samples])
    def samples(self):
        with self.connect() as db:
            return [(r[0], r[1]) for r in db.execute('SELECT person_id,image FROM samples')]
    def mark(self, person_id, action, timezone='Europe/Paris', method='face', now=None):
        if action not in ('Check in', 'Check out'):
            raise ValueError('Invalid action')
        now = now or datetime.now(ZoneInfo(timezone))
        day, stamp = now.date().isoformat(), now.isoformat(timespec='seconds')
        with self.connect() as db:
            row = db.execute('SELECT * FROM attendance WHERE person_id=? AND day=?', (person_id, day)).fetchone()
            if action == 'Check in':
                if row: return 'Already checked in today.'
                db.execute('INSERT INTO attendance VALUES(?,?,?,?,?)', (person_id, day, stamp, None, method))
                return 'Check-in recorded.'
            if not row: return 'Check in before checking out.'
            if row['departure']: return 'Already checked out today.'
            db.execute('UPDATE attendance SET departure=? WHERE person_id=? AND day=?', (stamp, person_id, day))
            return 'Check-out recorded.'
    def records(self, start, end):
        with self.connect() as db:
            return [dict(r) for r in db.execute('SELECT p.code,p.name,p.department,a.day,a.arrival,a.departure,a.method FROM attendance a JOIN people p ON p.id=a.person_id WHERE a.day BETWEEN ? AND ? ORDER BY a.arrival DESC', (str(start), str(end)))]
    def delete(self, person_id):
        with self.connect() as db:
            db.execute('DELETE FROM people WHERE id=?', (person_id,))
