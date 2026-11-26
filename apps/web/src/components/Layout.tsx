import { NavLink, Outlet } from 'react-router-dom';
import { useSession } from '../api/context';

const LINKS = [
  { to: '/', label: 'Overview', end: true },
  { to: '/modules', label: 'Modules' },
  { to: '/adapters', label: 'Adapters' },
  { to: '/connections', label: 'Connections' },
  { to: '/audit', label: 'Audit log' },
];

export function Layout() {
  const { logout } = useSession();
  return (
    <div className="shell">
      <a href="#main" className="skip-link">
        Skip to content
      </a>
      <header className="topbar">
        <span className="brand">NEXORA</span>
        <nav aria-label="Primary">
          <ul>
            {LINKS.map((l) => (
              <li key={l.to}>
                <NavLink to={l.to} end={l.end ?? false}>
                  {l.label}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>
        <button type="button" onClick={logout}>
          Sign out
        </button>
      </header>
      <main id="main" tabIndex={-1}>
        <Outlet />
      </main>
    </div>
  );
}
