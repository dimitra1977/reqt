-- requirements_schema.sql
-- SQL schema for hierarchical requirements storage with 5 levels.
-- Level-0: Features
-- Level-1: User Stories
-- Level-2: System Requirements
-- Level-3: Sub-System & Interface Requirements
-- Level-4: Software and Hardware Requirements

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TYPE lifecycle_state AS ENUM ('DRAFT', 'IN-REVIEW', 'APPROVED', 'DEPRECATED');
CREATE TYPE level_of_maturity AS ENUM ('LM-0', 'LM-1', 'LM-2', 'LM-3', 'LM-4', 'LM-5');

CREATE TABLE requirements (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    level INTEGER NOT NULL CHECK (level BETWEEN 0 AND 4),
    summary TEXT NOT NULL,
    description TEXT,
    parent_requirement_id UUID NULL REFERENCES requirements (id) ON DELETE SET NULL,
    primary_child_requirement_id UUID NULL REFERENCES requirements (id) ON DELETE SET NULL,
    maturity  level_of_maturity,
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
INSERT INTO requirements (id, level, summary, description, maturity, lifecycle)
VALUES
    ('00000000-0000-0000-0000-000000000001', 0, 'Climate Control', 'The vehicle shall support HVAC (Heating, Ventilation & Air Conditoning) with settings for driver and passenger zone temperature, fan speed, re-circulation and an auto mode where the system controls fan speeed based on set temperature.', 'LM-0', 'DRAFT'),
    ('00000000-0000-0000-0000-000000000002', 1, 'Setting temperature in auto mode', 'As a driver, I want to change the temperature,  so that I set a cabin environment I am comfortable with.', 'LM-0', 'DRAFT'),
    ('00000000-0000-0000-0000-000000000003', 2, 'Climate Controller auto mode', 'The Climate Control ECU shall be resonsible for setting HVAC compressor, blower motor and vent functions when it is instructed to go into auto mode.', 'LM-0', 'DRAFT'),
    ('00000000-0000-0000-0000-000000000004', 3, 'Signal definition: Climate Control Auto Mode', 'Signal Name: ICC_HVACAutoMode_Req \n Signal Length: 2 bits\nPeriodicity: 100 msec\nValue Table:\n    0x00 : No Request\n    0x01 : Auto On\n    0x02 : Auto Off\n    0x03 : Invalid \n Value Table:\n 0x00 : No Request \n 0x01 : Auto On \n0x02 : Auto Off\n 0x03 : Invalid \nSender: Infotainment \nReceivers: Climate Control, Telematics', 'LM-0', 'DRAFT'),
    ('00000000-0000-0000-0000-000000000005', 4, 'Infotainment: Auto Mode On', 'When the user presses the Auto Mode button to "On" state, ICC shall send the signal ICC_HVACAutoMode_Req with the value 0x01: Auto On.', 'LM-0', 'DRAFT');

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
