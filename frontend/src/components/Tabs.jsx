/**
 * NeerNetra -- Tabs
 * ===================
 * Minimal underline-tab switcher. Controlled component.
 */

function Tabs({ tabs, active, onChange }) {
  return (
    <div className="tabs-bar" role="tablist">
      {tabs.map((t) => (
        <button
          key={t.id}
          role="tab"
          type="button"
          aria-selected={active === t.id}
          className={`tab-btn${active === t.id ? ' tab-btn-active' : ''}`}
          onClick={() => onChange(t.id)}
        >
          {t.label}
          {t.badge != null && <span className="tab-badge">{t.badge}</span>}
        </button>
      ))}
    </div>
  );
}

export default Tabs;
