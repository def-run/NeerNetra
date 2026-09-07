/**
 * NeerNetra -- Sidebar
 * ======================
 * Persistent left-hand section nav.
 */

import { NavLink } from 'react-router-dom';

const NAV_ITEMS = [
  { to: '/', label: 'Live Map', end: true },
  { to: '/explorer', label: 'Explorer' },
  { to: '/locations', label: 'Locations' },
  { to: '/history', label: 'History' },
  { to: '/demo', label: 'Demo replay' },
];

function Sidebar() {
  return (
    <nav className="sidebar" aria-label="Main navigation">
      {NAV_ITEMS.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          end={item.end}
          className={({ isActive }) => `sidebar-link${isActive ? ' sidebar-link-active' : ''}`}
        >
          {item.label}
        </NavLink>
      ))}
    </nav>
  );
}

export default Sidebar;
