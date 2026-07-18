export type UserRole = "admin" | "lecturer" | "student";
export type UserStatus = "active" | "disabled";

export interface User {
  id: string;
  username: string;
  full_name: string;
  email: string | null;
  role: UserRole;
  status: UserStatus;
}

export type OSStatus = "available" | "coming_soon" | "disabled" | "validating";

export interface OperatingSystem {
  id: string;
  slug: string;
  name: string;
  family: string;
  package_manager: string | null;
  architecture: string;
  description: string | null;
  icon_path: string | null;
  default_ram_mb: number;
  default_vcpus: number;
  estimated_boot_secs: number;
  status: OSStatus;
}

export type VMState =
  | "queued"
  | "provisioning"
  | "running"
  | "stopping"
  | "stopped"
  | "expired"
  | "failed"
  | "destroyed";

export interface VMSession {
  id: string;
  user_id: string;
  operating_system_id: string;
  state: VMState;
  ram_mb: number;
  vcpus: number;
  network_policy: "enabled" | "disabled" | "restricted";
  started_at: string | null;
  expires_at: string | null;
  extension_count: number;
  max_extensions: number;
  console_url: string | null;
}

export interface MaintenanceStatus {
  is_active: boolean;
  message: string | null;
  started_at: string | null;
}

export interface VMLimitPolicy {
  name: string;
  max_session_minutes: number;
  max_extension_minutes: number;
  max_extensions: number;
  idle_warning_minutes: number;
  idle_timeout_minutes: number;
  max_concurrent_vms_total: number;
  updated_at: string;
}

export interface HostStats {
  host: { cpu_count: number; memory_total_mb: number; free_memory_mb: number };
  running_vms: number;
  queued_vms: number;
}

export interface AuditLogEntry {
  id: number;
  actor_id: string | null;
  actor_role: string | null;
  action: string;
  target_type: string | null;
  target_id: string | null;
  created_at: string;
}
