import { useState, type ChangeEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { UploadCloud, UserPlus, Ban, CheckCircle } from "lucide-react";
import { usersApi } from "@/api/users";
import { operatingSystemsApi } from "@/api/operatingSystems";
import { adminApi } from "@/api/admin";
import { useToast } from "@/context/ToastContext";
import type { UserRole } from "@/types";

/**
 * System administration: user management (create/disable/reset lecturers
 * and students), OS image uploads, and the audit trail. Server config
 * (.env, storage paths, TLS) is intentionally left to the deployment docs
 * (docs/INSTALL_UBUNTU.md) rather than a web UI, since changing it usually
 * requires a container restart anyway.
 */
export default function AdminPage() {
  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-semibold">System Administration</h1>
      <UserManagementCard />
      <ImageUploadCard />
      <AuditLogCard />
    </div>
  );
}

function UserManagementCard() {
  const qc = useQueryClient();
  const { showToast } = useToast();
  const [role, setRole] = useState<UserRole>("student");

  const { data: users = [] } = useQuery({ queryKey: ["users"], queryFn: () => usersApi.list() });

  const createMutation = useMutation({
    mutationFn: usersApi.create,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["users"] });
      showToast("User created.", "success");
    },
    onError: (err: any) => showToast(err?.response?.data?.detail ?? "Could not create user.", "error"),
  });

  const disableMutation = useMutation({
    mutationFn: usersApi.disable,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["users"] }),
  });
  const enableMutation = useMutation({
    mutationFn: usersApi.enable,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["users"] }),
  });

  return (
    <div className="card p-4 flex flex-col gap-4">
      <h2 className="font-semibold flex items-center gap-2">
        <UserPlus size={16} /> Users
      </h2>

      <form
        className="flex flex-wrap items-end gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          const fd = new FormData(e.currentTarget);
          createMutation.mutate({
            username: String(fd.get("username")),
            full_name: String(fd.get("full_name")),
            password: String(fd.get("password")),
            role,
          });
          e.currentTarget.reset();
        }}
      >
        <Field name="username" label="Username" />
        <Field name="full_name" label="Full name" />
        <Field name="password" label="Password" type="password" />
        <label className="flex flex-col gap-1">
          <span className="text-xs text-gray-500">Role</span>
          <select
            value={role}
            onChange={(e) => setRole(e.target.value as UserRole)}
            className="rounded-lg border border-gray-300 dark:border-gray-700 bg-transparent px-2 py-1.5 text-sm"
          >
            <option value="student">Student</option>
            <option value="lecturer">Lecturer</option>
            <option value="admin">Admin</option>
          </select>
        </label>
        <button type="submit" className="btn-primary">
          Create
        </button>
      </form>

      <table className="w-full text-sm">
        <thead className="text-left text-gray-500 border-b border-gray-200 dark:border-gray-800">
          <tr>
            <th className="py-2">Username</th>
            <th>Full name</th>
            <th>Role</th>
            <th>Status</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {users.map((u) => (
            <tr key={u.id} className="border-b border-gray-100 dark:border-gray-800/60">
              <td className="py-2">{u.username}</td>
              <td>{u.full_name}</td>
              <td>{u.role}</td>
              <td>{u.status}</td>
              <td>
                {u.status === "active" ? (
                  <button onClick={() => disableMutation.mutate(u.id)} className="text-red-600 flex items-center gap-1 text-xs">
                    <Ban size={12} /> Disable
                  </button>
                ) : (
                  <button onClick={() => enableMutation.mutate(u.id)} className="text-green-600 flex items-center gap-1 text-xs">
                    <CheckCircle size={12} /> Enable
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ImageUploadCard() {
  const { showToast } = useToast();
  const [slug, setSlug] = useState("");
  const [progress, setProgress] = useState<number | null>(null);

  const uploadMutation = useMutation({
    mutationFn: ({ file }: { file: File }) =>
      operatingSystemsApi.uploadImage(slug, file, setProgress),
    onSuccess: () => {
      showToast("Image uploaded. Add/update metadata.json on the server, then rescan.", "success");
      setProgress(null);
    },
    onError: () => {
      showToast("Upload failed.", "error");
      setProgress(null);
    },
  });

  return (
    <div className="card p-4 flex flex-col gap-3">
      <h2 className="font-semibold flex items-center gap-2">
        <UploadCloud size={16} /> Upload OS Image
      </h2>
      <p className="text-xs text-gray-500">
        Uploads directly into <code>VMImages/&lt;slug&gt;/base.qcow2</code>. You'll still need to add
        a matching <code>metadata.json</code> on the server (see VMImages/README.md) before it appears
        as launchable.
      </p>
      <div className="flex flex-wrap items-end gap-2">
        <Field
          name="slug"
          label="Slug (e.g. ubuntu-24.04)"
          value={slug}
          onChange={(e) => setSlug(e.target.value)}
        />
        <label className="btn-secondary cursor-pointer">
          Choose .qcow2 file
          <input
            type="file"
            accept=".qcow2"
            className="hidden"
            disabled={!slug}
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) uploadMutation.mutate({ file });
            }}
          />
        </label>
      </div>
      {progress !== null && (
        <div className="w-full h-2 bg-gray-200 dark:bg-gray-800 rounded-full overflow-hidden">
          <div className="h-full bg-primary-600" style={{ width: `${progress}%` }} />
        </div>
      )}
    </div>
  );
}

function AuditLogCard() {
  const { data: logs = [] } = useQuery({ queryKey: ["admin", "audit-logs"], queryFn: () => adminApi.auditLogs(50) });

  return (
    <div className="card p-4">
      <h2 className="font-semibold mb-3">Recent Audit Trail</h2>
      <table className="w-full text-sm">
        <thead className="text-left text-gray-500 border-b border-gray-200 dark:border-gray-800">
          <tr>
            <th className="py-2">Action</th>
            <th>Target</th>
            <th>When</th>
          </tr>
        </thead>
        <tbody>
          {logs.map((log) => (
            <tr key={log.id} className="border-b border-gray-100 dark:border-gray-800/60">
              <td className="py-2 font-mono text-xs">{log.action}</td>
              <td className="text-xs text-gray-500">
                {log.target_type ? `${log.target_type}:${log.target_id?.slice(0, 8)}` : "—"}
              </td>
              <td className="text-xs text-gray-500">{new Date(log.created_at).toLocaleString()}</td>
            </tr>
          ))}
          {logs.length === 0 && (
            <tr>
              <td colSpan={3} className="py-6 text-center text-gray-400">
                No audit events yet.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

function Field({
  name,
  label,
  type = "text",
  value,
  onChange,
}: {
  name: string;
  label: string;
  type?: string;
  value?: string;
  onChange?: (e: ChangeEvent<HTMLInputElement>) => void;
}) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-xs text-gray-500">{label}</span>
      <input
        name={name}
        type={type}
        value={value}
        onChange={onChange}
        required
        className="rounded-lg border border-gray-300 dark:border-gray-700 bg-transparent px-2 py-1.5 text-sm"
      />
    </label>
  );
}
