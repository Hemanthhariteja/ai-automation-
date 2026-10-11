import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { IconAI, IconAnalytics, IconBuilding, IconChannel, IconDashboard, IconLeads, IconLogout, IconWorkflow } from "./Icons";

const NAV_ITEMS = [
  { to: "/dashboard", label: "Dashboard", Icon: IconDashboard },
  { to: "/leads", label: "Leads", Icon: IconLeads },
  { to: "/workflows", label: "Workflows", Icon: IconWorkflow },
  { to: "/channels", label: "Channels", Icon: IconChannel },
  { to: "/analytics", label: "Analytics", Icon: IconAnalytics },
  { to: "/settings/ai", label: "AI Provider", Icon: IconAI },
  { to: "/settings/business", label: "Business Profile", Icon: IconBuilding },
];

function navClass({ isActive }) {
  return isActive ? "nav-link active" : "nav-link";
}

function initials(name) {
  if (!name) return "?";
  return name.trim().charAt(0).toUpperCase();
}

export default function Layout() {
  const { user, logout } = useAuth();

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <span className="brand-mark">TF</span>
          <span className="brand-name">TechFix Automation</span>
        </div>

        <nav className="sidebar-nav">
          {NAV_ITEMS.map(({ to, label, Icon }) => (
            <NavLink key={to} to={to} className={navClass}>
              <Icon className="nav-icon" />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="sidebar-footer">
          <div className="user-chip">
            <span className="user-avatar">{initials(user?.full_name || user?.email)}</span>
            <span className="user-email">{user?.email}</span>
          </div>
          <button onClick={logout} className="btn btn-ghost btn-sm logout-btn">
            <IconLogout className="nav-icon" />
            Log out
          </button>
        </div>
      </aside>

      <main className="app-main">
        <Outlet />
      </main>
    </div>
  );
}
