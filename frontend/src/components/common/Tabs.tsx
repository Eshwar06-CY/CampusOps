import type { FC, ReactNode } from 'react';

export interface TabItem {
  id: string;
  label: string;
  icon?: ReactNode;
  badge?: string | number;
}

interface TabsProps {
  tabs: TabItem[];
  activeTab: string;
  onChange: (tabId: string) => void;
  className?: string;
}

export const Tabs: FC<TabsProps> = ({ tabs, activeTab, onChange, className = '' }) => {
  return (
    <div className={`co-tabs-list ${className}`} role="tablist">
      {tabs.map((tab) => {
        const isSelected = tab.id === activeTab;
        return (
          <button
            key={tab.id}
            type="button"
            role="tab"
            aria-selected={isSelected}
            aria-controls={`tab-panel-${tab.id}`}
            id={`tab-btn-${tab.id}`}
            className="co-tab-trigger"
            onClick={() => onChange(tab.id)}
          >
            {tab.icon && <span style={{ marginRight: 6 }}>{tab.icon}</span>}
            <span>{tab.label}</span>
            {tab.badge !== undefined && (
              <span
                style={{
                  marginLeft: 8,
                  padding: '1px 6px',
                  borderRadius: '9999px',
                  fontSize: '0.75rem',
                  backgroundColor: isSelected ? 'var(--co-primary-100)' : 'var(--co-slate-200)',
                  color: isSelected ? 'var(--co-primary-800)' : 'var(--co-slate-700)',
                }}
              >
                {tab.badge}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
};

