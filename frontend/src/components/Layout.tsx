import { useQueryClient } from "@tanstack/react-query";
import { NavLink, Outlet, useNavigate } from "react-router";
import { logout } from "../api/auth";
import { ME_QUERY_KEY, useMe } from "../auth/AuthProvider";

export function Layout() {
  const { data: me } = useMe();
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  async function onSignOut() {
    await logout();
    queryClient.setQueryData(ME_QUERY_KEY, null);
    navigate("/login", { replace: true });
  }

  return (
    <div className="shell">
      <header className="topbar">
        <span className="brand">ForgeOps</span>
        <nav aria-label="Main">
          <NavLink to="/" end>War Room</NavLink>
          <NavLink to="/investigations">History</NavLink>
        </nav>
        <span className="muted">{me?.workspace.name} · {me?.user.email}</span>
        <button className="secondary" onClick={onSignOut}>Sign out</button>
      </header>
      <main className="content">
        <Outlet />
      </main>
    </div>
  );
}
