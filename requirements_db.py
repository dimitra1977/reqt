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
INSERT OR IGNORE INTO requirements (id, level, summary, description, custom_field_1, custom_field_2, custom_field_3, custom_field_4)
VALUES
    ('00000000-0000-0000-0000-000000000001', 0, 'Product Search Feature', 'Supports product search across catalog.', 'Priority:High', 'Release:1.0', 'Owner:Product', 'Status:Draft'),
    ('00000000-0000-0000-0000-000000000002', 1, 'Search by keyword', 'Users can search products using keywords.', 'Persona:Customer', 'Story Points:8', 'Epic:Search', 'Status:Draft'),
    ('00000000-0000-0000-0000-000000000003', 2, 'Search engine integration', 'The system shall integrate with the search engine API.', 'Subsystem:Search', 'Performance:500ms', 'Test:Search API', 'Status:Draft'),
    ('00000000-0000-0000-0000-000000000004', 3, 'API response handling', 'Handle search API responses and map to UI models.', 'Interface:REST', 'Tech:JSON', 'Team:Backend', 'Status:Draft'),
    ('00000000-0000-0000-0000-000000000005', 4, 'Search engine client library', 'Use the search client library for hardware and software search components.', 'Platform:Linux', 'Tool:Java', 'Memory:512MB', 'Status:Draft');

INSERT OR IGNORE INTO requirement_links (parent_id, child_id)
VALUES
    ('00000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000002'),
    ('00000000-0000-0000-0000-000000000002', '00000000-0000-0000-0000-000000000003'),
    ('00000000-0000-0000-0000-000000000003', '00000000-0000-0000-0000-000000000004'),
    ('00000000-0000-0000-0000-000000000004', '00000000-0000-0000-0000-000000000005');
'''


class RequirementDatabase:
    def __init__(self, db_path: str = 'requirements.db'):
        self.db_path = Path(db_path)
        self.connection = sqlite3.connect(str(self.db_path))
        self.connection.row_factory = sqlite3.Row
        self.connection.execute('PRAGMA foreign_keys = ON;')
        self.initialize()

    def initialize(self) -> None:
        self.connection.executescript(DB_SCHEMA)
        self.connection.commit()
        if not self.get_all_requirements():
            self._insert_sample_data()

    def _insert_sample_data(self) -> None:
        self.connection.executescript(INSERT_SAMPLE_SQL)
        self.connection.commit()
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
        sql = 'SELECT * FROM requirements'
        params = ()
        if search:
            sql += ' WHERE summary LIKE ? OR description LIKE ? OR custom_field_1 LIKE ? OR custom_field_2 LIKE ? OR custom_field_3 LIKE ? OR custom_field_4 LIKE ?'
            term = f'%{search}%'
            params = (term, term, term, term, term, term)
        sql += ' ORDER BY level, summary'
        return self.connection.execute(sql, params).fetchall()

    def get_requirement(self, requirement_id: str) -> Optional[sqlite3.Row]:
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
        custom_field_1: Optional[str] = None,
        custom_field_2: Optional[str] = None,
        custom_field_3: Optional[str] = None,
        custom_field_4: Optional[str] = None,
    ) -> str:
        requirement_id = self._generate_id()
        self.connection.execute(
            '''
            INSERT INTO requirements (
                id, level, summary, description,
                parent_requirement_id, custom_field_1, custom_field_2,
                custom_field_3, custom_field_4
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                requirement_id,
                level,
                summary,
                description,
                parent_requirement_id,
                custom_field_1,
                custom_field_2,
                custom_field_3,
                custom_field_4,
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
        custom_field_1: Optional[str] = None,
        custom_field_2: Optional[str] = None,
        custom_field_3: Optional[str] = None,
        custom_field_4: Optional[str] = None,
    ) -> None:
        row = self.get_requirement(requirement_id)
        if row is None:
            return
        summary = summary if summary is not None else row['summary']
        description = description if description is not None else row['description']
        level = level if level is not None else row['level']
        custom_field_1 = custom_field_1 if custom_field_1 is not None else row['custom_field_1']
        custom_field_2 = custom_field_2 if custom_field_2 is not None else row['custom_field_2']
        custom_field_3 = custom_field_3 if custom_field_3 is not None else row['custom_field_3']
        custom_field_4 = custom_field_4 if custom_field_4 is not None else row['custom_field_4']

        self.connection.execute(
            '''
            UPDATE requirements
            SET summary = ?, description = ?, level = ?, parent_requirement_id = ?,
                custom_field_1 = ?, custom_field_2 = ?, custom_field_3 = ?, custom_field_4 = ?,
                updated_at = datetime('now')
            WHERE id = ?
            ''',
            (
                summary,
                description,
                level,
                parent_requirement_id,
                custom_field_1,
                custom_field_2,
                custom_field_3,
                custom_field_4,
                requirement_id,
            ),
        )
        self._sync_parent_links_for(requirement_id, parent_requirement_id)
        self.connection.commit()

    def delete_requirement(self, requirement_id: str) -> None:
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
