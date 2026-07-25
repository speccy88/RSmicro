SCHEMA_VERSION=1
MIGRATION_1="""
CREATE TABLE IF NOT EXISTS schema_migrations(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS controllers(controller_uuid TEXT PRIMARY KEY, name TEXT);
CREATE TABLE IF NOT EXISTS tags(tag_uuid TEXT NOT NULL, controller_uuid TEXT NOT NULL, qualified_name TEXT, data_type TEXT NOT NULL, PRIMARY KEY(tag_uuid,controller_uuid));
CREATE TABLE IF NOT EXISTS samples(sample_id INTEGER PRIMARY KEY,tag_uuid TEXT NOT NULL,controller_uuid TEXT NOT NULL,program_hash TEXT,data_type TEXT NOT NULL,bool_value INTEGER,dint_value INTEGER,real_value REAL,text_value TEXT,quality TEXT NOT NULL,quality_reason TEXT NOT NULL,forced INTEGER NOT NULL,source_timestamp TEXT,receive_timestamp TEXT NOT NULL,broker_sequence INTEGER,scan_number INTEGER);
CREATE INDEX IF NOT EXISTS samples_tag_time ON samples(tag_uuid,receive_timestamp);
CREATE TABLE IF NOT EXISTS events(event_id INTEGER PRIMARY KEY,event_type TEXT NOT NULL,event_time TEXT NOT NULL,payload TEXT);
CREATE TABLE IF NOT EXISTS alarm_definitions(alarm_uuid TEXT PRIMARY KEY,definition TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS alarm_transitions(id INTEGER PRIMARY KEY,alarm_uuid TEXT NOT NULL,state TEXT NOT NULL,state_version INTEGER NOT NULL,event_time TEXT NOT NULL,source_value TEXT,source_quality TEXT);
CREATE TABLE IF NOT EXISTS alarm_acknowledgements(id INTEGER PRIMARY KEY,alarm_uuid TEXT NOT NULL,requester TEXT NOT NULL,comment TEXT,event_time TEXT NOT NULL,state_version INTEGER NOT NULL,UNIQUE(alarm_uuid,state_version));
CREATE TABLE IF NOT EXISTS commands(command_uuid TEXT PRIMARY KEY,requester TEXT,requested_value TEXT,request_time TEXT,completion_time TEXT,success INTEGER,details TEXT);
CREATE TABLE IF NOT EXISTS service_runs(run_uuid TEXT PRIMARY KEY,started_at TEXT NOT NULL,stopped_at TEXT);
"""
