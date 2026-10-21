import tempfile
import unittest
import sqlite3
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from storage import Store

class StorageTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.store=Store(Path(self.tmp.name)/'test.db')
        self.store.enroll('001','Demo Person','Engineering',[b'a',b'b',b'c'],True)
        self.pid=self.store.people()[0]['id']
        self.now=datetime(2026,10,21,9,tzinfo=ZoneInfo('Europe/Paris'))
    def tearDown(self): self.tmp.cleanup()
    def test_daily_deduplication_and_checkout(self):
        self.assertIn('before',self.store.mark(self.pid,'Check out',now=self.now))
        self.assertEqual('Check-in recorded.',self.store.mark(self.pid,'Check in',now=self.now))
        self.assertIn('Already',self.store.mark(self.pid,'Check in',now=self.now))
        self.assertEqual('Check-out recorded.',self.store.mark(self.pid,'Check out',now=self.now))
        self.assertIn('Already',self.store.mark(self.pid,'Check out',now=self.now))
        self.assertEqual(1,len(self.store.records('2026-10-21','2026-10-21')))
    def test_consent_and_unique_id(self):
        with self.assertRaises(ValueError): self.store.enroll('002','Name','',[b'a']*3,False)
        with self.assertRaises(sqlite3.IntegrityError): self.store.enroll('001','Other','',[b'a']*3,True)
        self.assertEqual(3,len(self.store.samples()))
    def test_deletion_cascades(self):
        self.store.mark(self.pid,'Check in',now=self.now)
        self.store.delete(self.pid)
        self.assertEqual([],self.store.people())
        self.assertEqual([],self.store.samples())
        self.assertEqual([],self.store.records('2026-01-01','2026-12-31'))
    def test_new_day(self):
        self.store.mark(self.pid,'Check in',now=self.now)
        next_day=datetime(2026,10,22,9,tzinfo=ZoneInfo('Europe/Paris'))
        self.assertEqual('Check-in recorded.',self.store.mark(self.pid,'Check in',now=next_day))

if __name__=='__main__': unittest.main()
