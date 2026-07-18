-- Knpodly initial database schema
-- Applied automatically on first container start via docker-entrypoint-initdb.d
-- For subsequent changes, use Alembic migrations in backend/app/db/migrations

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ========== Users & Roles ==========

CREATE TYPE user_role AS ENUM ('admin', 'lecturer', 'student');
CREATE TYPE user_status AS ENUM ('active', 'disabled');

CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username        VARCHAR(64) UNIQUE NOT NULL,
    email           VARCHAR(255) UNIQUE,
    full_name       VARCHAR(255) NOT NULL,
    password_hash   VARCHAR(255) NOT NULL,
    role            user_role NOT NULL DEFAULT 'student',
    status          user_status NOT NULL DEFAULT 'active',
    created_by      UUID REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_login_at   TIMESTAMPTZ
);

CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_status ON users(status);

-- ========== Operating System Catalogue ==========

CREATE TYPE os_status AS ENUM ('available', 'coming_soon', 'disabled', 'validating');

CREATE TABLE operating_systems (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    slug                VARCHAR(100) UNIQUE NOT NULL,   -- matches VMImages/<slug>/
    name                VARCHAR(255) NOT NULL,
    family              VARCHAR(100) NOT NULL,
    package_manager     VARCHAR(50),
    architecture        VARCHAR(20) NOT NULL DEFAULT 'x86_64',
    description         TEXT,
    icon_path           VARCHAR(500),
    default_ram_mb      INTEGER NOT NULL DEFAULT 2048,
    default_vcpus       INTEGER NOT NULL DEFAULT 2,
    base_image_path     VARCHAR(500),
    estimated_boot_secs INTEGER NOT NULL DEFAULT 30,
    status              os_status NOT NULL DEFAULT 'validating',
    checksum_sha256     VARCHAR(64),
    discovered_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ========== VM Sessions ==========

CREATE TYPE vm_state AS ENUM (
    'queued', 'provisioning', 'running', 'stopping',
    'stopped', 'expired', 'failed', 'destroyed'
);

CREATE TABLE vm_sessions (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id             UUID NOT NULL REFERENCES users(id),
    operating_system_id UUID NOT NULL REFERENCES operating_systems(id),
    libvirt_domain_name VARCHAR(255) UNIQUE,
    overlay_disk_path   VARCHAR(500),
    state               vm_state NOT NULL DEFAULT 'queued',
    vnc_port            INTEGER,
    websocket_token     VARCHAR(255),
    ram_mb              INTEGER NOT NULL,
    vcpus               INTEGER NOT NULL,
    network_policy      VARCHAR(20) NOT NULL DEFAULT 'restricted', -- enabled|disabled|restricted
    started_at          TIMESTAMPTZ,
    expires_at          TIMESTAMPTZ,
    extension_count     INTEGER NOT NULL DEFAULT 0,
    max_extensions      INTEGER NOT NULL DEFAULT 1,
    last_activity_at     TIMESTAMPTZ,
    idle_warning_sent_at TIMESTAMPTZ,
    stopped_at          TIMESTAMPTZ,
    stop_reason         VARCHAR(50),  -- user_stop | expired | idle_timeout | force_stop | error
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_vm_sessions_user ON vm_sessions(user_id);
CREATE INDEX idx_vm_sessions_state ON vm_sessions(state);
CREATE INDEX idx_vm_sessions_expires ON vm_sessions(expires_at);

-- Enforce "one running VM per student" at the DB level as a defense-in-depth
-- measure (application logic also enforces this before provisioning).
CREATE UNIQUE INDEX uniq_one_active_session_per_student
    ON vm_sessions(user_id)
    WHERE state IN ('queued', 'provisioning', 'running', 'stopping');

-- ========== Audit Log ==========

CREATE TABLE audit_logs (
    id           BIGSERIAL PRIMARY KEY,
    actor_id     UUID REFERENCES users(id),
    actor_role   user_role,
    action       VARCHAR(100) NOT NULL,      -- e.g. vm.launch, vm.force_stop, user.disable
    target_type  VARCHAR(50),                -- vm_session | user | operating_system | system
    target_id    VARCHAR(255),
    metadata     JSONB,
    ip_address   INET,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_audit_logs_actor ON audit_logs(actor_id);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_created ON audit_logs(created_at);

-- ========== System Event Log (crashes, errors, auth failures) ==========

CREATE TABLE system_logs (
    id           BIGSERIAL PRIMARY KEY,
    level        VARCHAR(20) NOT NULL,   -- INFO | WARNING | ERROR | CRITICAL
    source       VARCHAR(100) NOT NULL,  -- api | vm-worker | scheduler | libvirt
    message      TEXT NOT NULL,
    metadata     JSONB,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_system_logs_level ON system_logs(level);
CREATE INDEX idx_system_logs_created ON system_logs(created_at);

-- ========== Maintenance Mode & Announcements ==========

CREATE TABLE maintenance_windows (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    enabled_by   UUID REFERENCES users(id),
    message      TEXT,
    is_active    BOOLEAN NOT NULL DEFAULT true,
    started_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    ended_at     TIMESTAMPTZ
);

-- ========== VM Resource Limit Policies (configurable by lecturers) ==========

CREATE TABLE vm_limit_policies (
    id                       UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name                     VARCHAR(100) NOT NULL DEFAULT 'default',
    max_session_minutes      INTEGER NOT NULL DEFAULT 120,
    max_extension_minutes    INTEGER NOT NULL DEFAULT 60,
    max_extensions           INTEGER NOT NULL DEFAULT 1,
    idle_warning_minutes     INTEGER NOT NULL DEFAULT 15,
    idle_timeout_minutes     INTEGER NOT NULL DEFAULT 20,
    max_concurrent_vms_total INTEGER NOT NULL DEFAULT 200,
    is_active                BOOLEAN NOT NULL DEFAULT true,
    updated_by               UUID REFERENCES users(id),
    updated_at               TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO vm_limit_policies (name) VALUES ('default');

-- ========== Seed: default admin (password must be changed on first login) ==========
-- Password hash below corresponds to a random one-time setup password printed
-- by scripts/create-admin.py during install; do NOT rely on a hardcoded value
-- in real deployments. Left as a placeholder / documentation reference only.
-- INSERT INTO users (username, full_name, password_hash, role)
-- VALUES ('admin', 'System Administrator', '<generated-by-setup-script>', 'admin');
