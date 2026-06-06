"""Small SQLite-backed persistence layer for requirements.

This module exposes `RequirementDatabase` — a thin wrapper around SQLite
that provides CRUD helpers for requirement records and a simple
parent/child linkage table. The class is intentionally lightweight so
it can be used from both the Tkinter desktop UI and the Flask web API.
"""

import sqlite3
import uuid
from pathlib import Path
from typing import List, Optional, Tuple

DB_SCHEMA = '''
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS requirements (
    id TEXT PRIMARY KEY,
    level INTEGER NOT NULL CHECK (level BETWEEN 0 AND 4),
    summary TEXT NOT NULL,
    description TEXT,
    parent_requirement_id TEXT REFERENCES requirements (id) ON DELETE SET NULL,
    primary_child_requirement_id TEXT REFERENCES requirements (id) ON DELETE SET NULL,
    maturity TEXT,
    lifecycle TEXT,
    custom_field_1 TEXT,
    custom_field_2 TEXT,
    custom_field_3 TEXT,
    custom_field_4 TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_requirements_level ON requirements (level);
CREATE INDEX IF NOT EXISTS idx_requirements_parent ON requirements (parent_requirement_id);
CREATE INDEX IF NOT EXISTS idx_requirements_primary_child ON requirements (primary_child_requirement_id);

CREATE TABLE IF NOT EXISTS requirement_links (
    parent_id TEXT NOT NULL REFERENCES requirements (id) ON DELETE CASCADE,
    child_id TEXT NOT NULL REFERENCES requirements (id) ON DELETE CASCADE,
    relationship_type TEXT NOT NULL DEFAULT 'hierarchy',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (parent_id, child_id)
);

CREATE INDEX IF NOT EXISTS idx_requirement_links_parent ON requirement_links (parent_id);
CREATE INDEX IF NOT EXISTS idx_requirement_links_child ON requirement_links (child_id);
'''

INSERT_SAMPLE_SQL = '''
INSERT OR IGNORE INTO requirements (id, level, summary, description, maturity, lifecycle)
VALUES
    ('00000000-0000-0000-0000-000000000001', 0, 'Climate Control', 'The vehicle shall support HVAC (Heating, Ventilation & Air Conditioning) with settings for driver and passenger zone temperature, fan speed, re-circulation and an auto mode where the system controls fan speed based on set temperature.', 'LM-0', 'DRAFT'),
    ('00000000-0000-0000-0000-000000000002', 1, 'Setting temperature in auto mode', 'As a driver, I want to change the temperature,  so that I set a cabin environment I am comfortable with.', 'LM-0', 'DRAFT'),
    ('00000000-0000-0000-0000-000000000003', 2, 'Climate Control Auto Mode Signal', 'Signal Name: ICC_HVACAutoMode_Req \n Signal Length: 2 bits\nPeriodicity: 1００ msec\nValue Table:\n    ０x００ : No Request\n    ０x０１ : Auto On\n    ０x０２ : Auto Off\n    ０x０３ : Invalid \n Sender: Infotainment \n Receivers: Climate Control, Telematics', 'LM-０', 'DRAFT'),
    ('00000000-0000-0000-0000-000000000004', 3, 'Signal definition: Climate Control Auto Mode', 'Signal Name: ICC_HVACAutoMode_Req \n Signal Length: ２ bits\nPeriodicity: １００ msec\nValue Table:\n    ０x００ : No Request\n    ９x９１ : Auto On\n    ９x９２ : Auto Off\n    ９x９３ : Invalid \n Value Table:\n ９x９₀ : No Request \n ９x９１ : Auto On \n９x９２ : Auto Off\n ９x９３ : Invalid \nSender: Infotainment \nReceivers: Climate Control, Telematics', 'LM-Ｏ', 'DRAFT'),
    ('00000000-0000-0000-0000-000000000005', 4, 'Infotainment: Auto Mode On', 'When the user presses the Auto Mode button to "On" state, ICC shall send the signal ICC_HVACAutoMode_Req with the value ｃｘｃ１: Auto On.', 'LM-Ｏ', 'DRAFT');

INSERT OR IGNORE INTO requirement_links (parent_id, child_id)
VALUES
    ('00000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000002'),
    ('00000000-0000-0000-0000-000000000002', '00000000-0000-0000-0000-000000000003'),
    ('00000000-0000-0000-0000-000000000003', '00000000-0000-0000-0000-000000000004'),
    ('00000000-0000-0000-0000-000000000004', '00000000-0000-0000-0000-000000000005');
'''


class RequirementDatabase:
    """Encapsulates SQLite operations for requirement objects.

    The class opens a single SQLite connection per instance and exposes
    convenience methods for querying and mutating requirement rows.
    """

    def __init__(self, db_path: str = 'requirements.db'):
        self.db_path = Path(db_path)
        # open a connection for this instance; callers are responsible for
        # closing the connection via `close()` when appropriate
        self.connection = sqlite3.connect(str(self.db_path))
        self.connection.row_factory = sqlite3.Row
        # ensure foreign keys are enforced for link integrity
        self.connection.execute('PRAGMA foreign_keys = ON;')
        self.initialize()

    def initialize(self) -> None:
        """Create schema if missing and seed sample data when empty."""
        self.connection.executescript(DB_SCHEMA)
        self._migrate_schema()
        self.connection.commit()
        # seed data only when DB is empty to make first-run experience
        if not self.get_all_requirements():
            self._insert_sample_data()

    def _migrate_schema(self) -> None:
        columns = {row['name'] for row in self.connection.execute("PRAGMA table_info(requirements)").fetchall()}
        if 'maturity' not in columns:
            self.connection.execute('ALTER TABLE requirements ADD COLUMN maturity TEXT')
        if 'lifecycle' not in columns:
            self.connection.execute('ALTER TABLE requirements ADD COLUMN lifecycle TEXT')

    def _insert_sample_data(self) -> None:
        self.connection.executescript(INSERT_SAMPLE_SQL)
        self.connection.commit()
        # requirement_links are populated via _sync_parent_links which
        # keeps the denormalized parent fields in sync
        self._sync_parent_links()

    def _sync_parent_links(self) -> None:
        mapping = {
            '00000000-0000-0000-0000-000000000002': '00000000-0000-0000-0000-000000000001',
            '00000000-0000-0000-0000-000000000003': '00000000-0000-0000-0000-000000000002',
            '00000000-0000-0000-0000-000000000004': '00000000-0000-0000-0000-000000000003',
            '00000000-0000-0000-0000-000000000005': '00000000-0000-0000-0000-000000000004',
        }
        for child_id, parent_id in mapping.items():
            self.update_requirement(child_id, parent_requirement_id=parent_id)

    def _generate_id(self) -> str:
        return str(uuid.uuid4())

    def get_all_requirements(self, search: str = '') -> List[sqlite3.Row]:
        """Return all requirements, optionally filtered by `search` term.

        The `search` term is matched against summary, description and
        the custom fields. An empty string returns all rows ordered by
        level then summary.
        """
        sql = 'SELECT * FROM requirements'
        params = ()
        if search:
            sql += (
                ' WHERE summary LIKE ? OR description LIKE ? OR custom_field_1 LIKE ? OR '
                'custom_field_2 LIKE ? OR custom_field_3 LIKE ? OR custom_field_4 LIKE ?'
            )
            term = f'%{search}%'
            params = (term, term, term, term, term, term)
        sql += ' ORDER BY level, summary'
        return self.connection.execute(sql, params).fetchall()

    def get_requirement(self, requirement_id: str) -> Optional[sqlite3.Row]:
        """Lookup a single requirement by `id`.

        Returns `None` when the requirement does not exist.
        """
        return self.connection.execute('SELECT * FROM requirements WHERE id = ?', (requirement_id,)).fetchone()

    def get_children(self, parent_id: str) -> List[sqlite3.Row]:
        return self.connection.execute('SELECT * FROM requirements WHERE parent_requirement_id = ? ORDER BY level, summary', (parent_id,)).fetchall()

    def get_root_requirements(self) -> List[sqlite3.Row]:
        return self.connection.execute('SELECT * FROM requirements WHERE parent_requirement_id IS NULL ORDER BY level, summary').fetchall()

    def insert_requirement(
        self,
        summary: str,
        description: str,
        level: int,
        parent_requirement_id: Optional[str] = None,
        maturity: Optional[str] = None,
        lifecycle: Optional[str] = None,
      
    ) -> str:
        requirement_id = self._generate_id()
        # perform the insert and ensure the link table contains the
        # appropriate parent->child relationship when a parent is
        # provided
        self.connection.execute(
            '''
            INSERT INTO requirements (
                id, level, summary, description,
                parent_requirement_id, maturity, lifecycle
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                requirement_id,
                level,
                summary,
                description,
                parent_requirement_id,
                maturity,
                lifecycle,
            ),
        )
        if parent_requirement_id:
            self._ensure_link(parent_requirement_id, requirement_id)
        self.connection.commit()
        return requirement_id

    def update_requirement(
        self,
        requirement_id: str,
        summary: Optional[str] = None,
        description: Optional[str] = None,
        level: Optional[int] = None,
        parent_requirement_id: Optional[str] = None,
        maturity: Optional[str] = None,
        lifecycle: Optional[str] = None,
    ) -> None:
        row = self.get_requirement(requirement_id)
        if row is None:
            # silently ignore updates to non-existent rows to keep
            # the API idempotent; callers can check existence first
            return
        summary = summary if summary is not None else row['summary']
        description = description if description is not None else row['description']
        level = level if level is not None else row['level']
        maturity = maturity if maturity is not None else row['maturity']
        lifecycle = lifecycle if lifecycle is not None else row['lifecycle']


        # update the denormalized parent id and maturity/lifecycle fields
        self.connection.execute(
            '''
            UPDATE requirements
            SET summary = ?, description = ?, level = ?, parent_requirement_id = ?,
                maturity = ?, lifecycle = ?,
                updated_at = datetime('now')
            WHERE id = ?
            ''',
            (
                summary,
                description,
                level,
                parent_requirement_id,
                maturity,
                lifecycle,
                requirement_id,
            ),
        )
        self._sync_parent_links_for(requirement_id, parent_requirement_id)
        self.connection.commit()

    def delete_requirement(self, requirement_id: str) -> None:
        """Delete a requirement. Foreign key constraints cascade to links."""
        self.connection.execute('DELETE FROM requirements WHERE id = ?', (requirement_id,))
        self.connection.commit()

    def _ensure_link(self, parent_id: str, child_id: str) -> None:
        self.connection.execute(
            'INSERT OR IGNORE INTO requirement_links (parent_id, child_id) VALUES (?, ?)',
            (parent_id, child_id),
        )

    def _sync_parent_links_for(self, requirement_id: str, parent_requirement_id: Optional[str]) -> None:
        self.connection.execute('DELETE FROM requirement_links WHERE child_id = ?', (requirement_id,))
        if parent_requirement_id:
            self._ensure_link(parent_requirement_id, requirement_id)

    def get_parent_options(self) -> List[Tuple[str, str]]:
        rows = self.connection.execute('SELECT id, summary FROM requirements ORDER BY level, summary').fetchall()
        return [(row['id'], f"{row['summary']} ({row['id'][:8]})") for row in rows]

    def close(self) -> None:
        self.connection.close()
