import type { FC } from 'react';
import { IconShield, IconSearch, IconRefresh } from '../common/Icons';

export type AppMode = 'public' | 'workspace' | 'staff' | 'accept-invite';

interface NavbarProps {
  currentMode: AppMode;
  onModeChange: (mode: AppMode) => void;
  eventKey: string;
  onEventKeyChange: (key: string) => void;
  onRefreshEvent?: () => void;
}

export const Navbar: FC<NavbarProps> = ({
  currentMode,
  onModeChange,
  eventKey,
  onEventKeyChange,
  onRefreshEvent,
}) => {
  return (
    <header className="co-navbar" role="banner">
      <div className="co-navbar-brand-row">
        <div
          className="co-navbar-brand"
          onClick={() => onModeChange('public')}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') onModeChange('public');
          }}
          aria-label="CampusOps home"
        >
          <div
            style={{
              width: 32,
              height: 32,
              borderRadius: 'var(--co-radius-md)',
              background: 'linear-gradient(135deg, var(--co-primary-600), var(--co-primary-800))',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#ffffff',
              boxShadow: 'var(--co-shadow-sm)',
              flexShrink: 0,
            }}
          >
            <IconShield size={18} />
          </div>
          <span>CampusOps</span>
          <span className="co-navbar-badge">Slice 5D</span>
        </div>
      </div>

      {/* Mode Switcher */}
      <nav aria-label="Main application sections" className="co-nav-segmented">
        <button
          type="button"
          className={`co-nav-segment-btn ${currentMode === 'public' ? 'active' : ''}`}
          onClick={() => onModeChange('public')}
          aria-pressed={currentMode === 'public'}
        >
          Public Registration
        </button>
        <button
          type="button"
          className={`co-nav-segment-btn ${currentMode === 'workspace' ? 'active' : ''}`}
          onClick={() => onModeChange('workspace')}
          aria-pressed={currentMode === 'workspace'}
        >
          Workspace &amp; Team
        </button>
        <button
          type="button"
          className={`co-nav-segment-btn ${currentMode === 'staff' ? 'active' : ''}`}
          onClick={() => onModeChange('staff')}
          aria-pressed={currentMode === 'staff'}
        >
          Staff Event Desk
        </button>
      </nav>

      {/* Event Key or Event Selector */}
      {currentMode === 'public' && (
        <div className="co-navbar-key-bar">
          <label htmlFor="nav-event-key" style={{ fontSize: '0.8rem', color: 'var(--co-text-muted)', fontWeight: 500, whiteSpace: 'nowrap' }}>
            Key:
          </label>
          <div style={{ position: 'relative', display: 'flex', alignItems: 'center', flex: 1, minWidth: 0 }}>
            <span style={{ position: 'absolute', left: 8, color: 'var(--co-text-muted)', display: 'flex', alignItems: 'center', pointerEvents: 'none' }}>
              <IconSearch size={14} />
            </span>
            <input
              id="nav-event-key"
              type="text"
              className="co-input"
              style={{
                width: '100%',
                minWidth: 120,
                padding: '4px 8px 4px 26px',
                fontSize: '0.8rem',
                fontFamily: 'var(--co-font-mono)',
              }}
              placeholder="reg_..."
              value={eventKey}
              onChange={(e) => onEventKeyChange(e.target.value)}
              aria-label="Event public registration key"
            />
          </div>
          {onRefreshEvent && (
            <button
              type="button"
              className="co-btn co-btn-secondary co-btn-sm"
              onClick={onRefreshEvent}
              title="Reload event metadata"
              style={{ display: 'inline-flex', alignItems: 'center', gap: 4, flexShrink: 0 }}
            >
              <IconRefresh size={14} />
              <span>Load</span>
            </button>
          )}
        </div>
      )}
    </header>
  );
};
