-- requirements_schema.sql
-- SQL schema for hierarchical requirements storage with 5 levels.
-- Level-0: Features
-- Level-1: User Stories
-- Level-2: System Requirements
-- Level-3: Sub-System & Interface Requirements
-- Level-4: Software and Hardware Requirements

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TYPE lifecycle_state AS ENUM ('DRAFT', 'IN-REVIEW', 'APPROVED', 'DEPRECATED');

CREATE TABLE requirements (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    level INTEGER NOT NULL CHECK (level BETWEEN 0 AND 4),
    summary TEXT NOT NULL,
    description TEXT,
    parent_requirement_id UUID NULL REFERENCES requirements (id) ON DELETE SET NULL,
    primary_child_requirement_id UUID NULL REFERENCES requirements (id) ON DELETE SET NULL,
    custom_field_1 TEXT,
    custom_field_2 TEXT,
    custom_field_3 TEXT,
    lifecycle lifecycle_state,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_requirements_level ON requirements (level);
CREATE INDEX idx_requirements_parent ON requirements (parent_requirement_id);
CREATE INDEX idx_requirements_primary_child ON requirements (primary_child_requirement_id);

-- Optional explicit parent/child mapping for support of multiple children per requirement.
CREATE TABLE requirement_links (
    parent_id UUID NOT NULL REFERENCES requirements (id) ON DELETE CASCADE,
    child_id UUID NOT NULL REFERENCES requirements (id) ON DELETE CASCADE,
    relationship_type TEXT DEFAULT 'hierarchy',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (parent_id, child_id)
);

CREATE INDEX idx_requirement_links_parent ON requirement_links (parent_id);
CREATE INDEX idx_requirement_links_child ON requirement_links (child_id);

-- Sample data for one complete hierarchy set.
INSERT INTO requirements (id, level, summary, description, custom_field_1, custom_field_2, custom_field_3, lifecycle)
VALUES
    ('00000000-0000-0000-0000-000000000001', 0, 'Product Search Feature', 'Supports product search across catalog.', 'Priority:High', 'Release:1.0', 'Owner:Product', 'DRAFT'),
    ('00000000-0000-0000-0000-000000000002', 1, 'Search by keyword', 'Users can search products using keywords.', 'Persona:Customer', 'Story Points:8', 'Epic:Search', 'DRAFT'),
    ('00000000-0000-0000-0000-000000000003', 2, 'Search engine integration', 'The system shall integrate with the search engine API.', 'Subsystem:Search', 'Performance:500ms', 'Test:Search API', 'DRAFT'),
    ('00000000-0000-0000-0000-000000000004', 3, 'API response handling', 'Handle search API responses and map to UI models.', 'Interface:REST', 'Tech:JSON', 'Team:Backend', 'DRAFT'),
    ('00000000-0000-0000-0000-000000000005', 4, 'Search engine client library', 'Use the search client library for hardware and software search components.', 'Platform:Linux', 'Tool:Java', 'Memory:512MB', 'DRAFT');

UPDATE requirements
SET parent_requirement_id = CASE id
    WHEN '00000000-0000-0000-0000-000000000002' THEN '00000000-0000-0000-0000-000000000001'
    WHEN '00000000-0000-0000-0000-000000000003' THEN '00000000-0000-0000-0000-000000000002'
    WHEN '00000000-0000-0000-0000-000000000004' THEN '00000000-0000-0000-0000-000000000003'
    WHEN '00000000-0000-0000-0000-000000000005' THEN '00000000-0000-0000-0000-000000000004'
    ELSE parent_requirement_id
END,
primary_child_requirement_id = CASE id
    WHEN '00000000-0000-0000-0000-000000000001' THEN '00000000-0000-0000-0000-000000000002'
    WHEN '00000000-0000-0000-0000-000000000002' THEN '00000000-0000-0000-0000-000000000003'
    WHEN '00000000-0000-0000-0000-000000000003' THEN '00000000-0000-0000-0000-000000000004'
    WHEN '00000000-0000-0000-0000-000000000004' THEN '00000000-0000-0000-0000-000000000005'
    ELSE primary_child_requirement_id
END
WHERE id IN (
    '00000000-0000-0000-0000-000000000001',
    '00000000-0000-0000-0000-000000000002',
    '00000000-0000-0000-0000-000000000003',
    '00000000-0000-0000-0000-000000000004',
    '00000000-0000-0000-0000-000000000005'
);

INSERT INTO requirement_links (parent_id, child_id)
VALUES
    ('00000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000002'),
    ('00000000-0000-0000-0000-000000000002', '00000000-0000-0000-0000-000000000003'),
    ('00000000-0000-0000-0000-000000000003', '00000000-0000-0000-0000-000000000004'),
    ('00000000-0000-0000-0000-000000000004', '00000000-0000-0000-0000-000000000005');
