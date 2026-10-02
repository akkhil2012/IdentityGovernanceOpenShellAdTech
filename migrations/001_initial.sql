CREATE TABLE IF NOT EXISTS consents (
 id bigserial PRIMARY KEY, customer_id varchar(40) NOT NULL, purpose varchar(80) NOT NULL,
 channel varchar(40) NOT NULL, destination varchar(80) NOT NULL, granted boolean NOT NULL,
 version integer NOT NULL, recorded_at timestamptz NOT NULL,
 UNIQUE(customer_id,purpose,channel,destination,version));
CREATE INDEX IF NOT EXISTS ix_consents_customer ON consents(customer_id);
CREATE TABLE IF NOT EXISTS workflows (
 id varchar(40) PRIMARY KEY, state varchar(30) NOT NULL, scenario varchar(80) NOT NULL,
 brief_json text NOT NULL, result_json text NOT NULL DEFAULT '{}', audience_json text NOT NULL DEFAULT '[]',
 audience_digest varchar(64) NOT NULL DEFAULT '', approval_digest varchar(64) NOT NULL DEFAULT '', created_at timestamptz NOT NULL);
CREATE TABLE IF NOT EXISTS grant_state (
 grant_id varchar(50) PRIMARY KEY, revoked boolean NOT NULL DEFAULT false,
 consumed_records integer NOT NULL DEFAULT 0, seen_nonces_json text NOT NULL DEFAULT '[]');
CREATE TABLE IF NOT EXISTS activation_intents (
 id bigserial PRIMARY KEY, workflow_id varchar(40) NOT NULL, idempotency_key varchar(100) UNIQUE NOT NULL,
 binding_digest varchar(64) NOT NULL, status varchar(30) NOT NULL, receipt_json text NOT NULL DEFAULT '{}', created_at timestamptz NOT NULL);
CREATE TABLE IF NOT EXISTS audit_events (
 id bigserial PRIMARY KEY, workflow_id varchar(40) NOT NULL, event varchar(80) NOT NULL,
 detail_json text NOT NULL, created_at timestamptz NOT NULL);
