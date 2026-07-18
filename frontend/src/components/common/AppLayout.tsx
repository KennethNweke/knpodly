import { Outlet, Link } from "react-router-dom";
import { Moon, Sun, LogOut, LayoutDashboard, ShieldCheck } from "lucide-react";
import { useTheme } from "@/context/ThemeContext";
import { useAuth } from "@/context/AuthContext";

/**
 * Shared shell (top nav + theme toggle) for every authenticated page.
 * Deliberately minimal here — the polished visual design (spacing rhythm,
 * iconography, animated transitions) should follow the frontend-design
 * skill guidance when this is fleshed out beyond scaffolding.
 */
export default function AppLayout() {
  const { theme, toggleTheme } = useTheme();
  const { user, logout } = useAuth();

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-surface-dark">
      <header className="border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900/60 backdrop-blur">
        <div className="mx-auto max-w-7xl px-4 h-14 flex items-center justify-between">
          <Link to="/" className="font-semibold text-lg text-primary-600 dark:text-primary-400">
            Knpodly
          </Link>
          <nav className="flex items-center gap-3 text-sm">
            {user?.role !== "student" && (
              <Link to="/lecturer" className="flex items-center gap-1 hover:text-primary-600">
                <LayoutDashboard size={16} /> Lecturer
              </Link>
            )}
            {user?.role === "admin" && (
              <Link to="/admin" className="flex items-center gap-1 hover:text-primary-600">
                <ShieldCheck size={16} /> Admin
              </Link>
            )}
            <button onClick={toggleTheme} aria-label="Toggle theme" className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800">
              {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
            </button>
            <button onClick={logout} className="flex items-center gap-1 hover:text-red-600">
              <LogOut size={16} /> Logout
            </button>
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-6">
        <Outlet />
      </main>
    </div>
  );
}
