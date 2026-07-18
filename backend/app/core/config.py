"""
Central application configuration, loaded from environment variables (.env).

Using pydantic-settings keeps every configurable value typed, validated,
and documented in one place instead of scattered os.environ[...] calls
throughout the codebase.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # General
    environment: str = "development"
    app_name: str = "Knpodly"
    app_url: str = "http://localhost:5173"
    log_level: str = "INFO"

    # Security
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # Database
    database_url: str

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # Virtualization
    libvirt_driver: str = "fake"  # "qemu" in production, "fake" for local dev/tests
    libvirt_uri: str = "qemu:///system"
    vm_images_path: str = "/srv/knpodly/VMImages"
    vm_icons_path: str = "/srv/knpodly/VMIcons"
    vm_overlay_path: str = "/srv/knpodly/overlays"
    vm_network_bridge: str = "knpodly-labnet"
    # Address the VM's VNC server listens on (set on the libvirt HOST, not
    # inside the backend container). Defaults to the Docker bridge gateway
    # IP, which is reachable from containers on the default bridge network
    # but not from outside the host — this lets the backend container reach
    # QEMU's VNC socket without needing host network mode. Lock this down
    # further with host firewall rules restricting the port range to the
    # Docker subnet only (see scripts/create-bridge.sh).
    vm_vnc_host: str = "172.17.0.1"
    vm_default_ram_mb: int = 2048
    vm_default_vcpus: int = 2
    vm_max_concurrent_total: int = 200

    # Session policy defaults (overridable per-policy in DB via vm_limit_policies)
    session_max_duration_minutes: int = 120
    session_expiry_warning_minutes: int = 15
    session_max_extension_minutes: int = 60
    session_max_extensions: int = 1
    idle_warning_minutes: int = 15
    idle_timeout_minutes: int = 20

    # noVNC
    novnc_ws_base_port: int = 6080
    novnc_public_base_url: str = "ws://localhost:8000/console"

    lab_internet_access_default: str = "restricted"

    # Max accepted size for a single base.qcow2 upload via
    # /operating-systems/{slug}/upload-image. Default 40GB; raise via
    # MAX_UPLOAD_BYTES for larger images, and make sure nginx's
    # client_max_body_size (infra/nginx/nginx.conf) is raised to match.
    max_upload_bytes: int = 40 * 1024 * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
