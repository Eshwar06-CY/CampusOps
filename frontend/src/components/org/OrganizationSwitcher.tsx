import { useState, useRef, useEffect, type FC } from 'react';
import type { OrganizationResponse } from '../../api/types';
import { Badge } from '../common/Badge';
import { IconBuilding, IconPlus } from '../common/Icons';

interface OrganizationSwitcherProps {
  organizations: OrganizationResponse[];
  activeOrgId: string | null;
  onSelectOrg: (orgId: string) => void;
  onCreateOrgClick: () => void;
  isLoading?: boolean;
}

export const OrganizationSwitcher: FC<OrganizationSwitcherProps> = ({
  organizations,
  activeOrgId,
  onSelectOrg,
  onCreateOrgClick,
  isLoading = false,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const activeOrg = organizations.find((o) => o.id === activeOrgId) || organizations[0] || null;

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen]);

  const renderBadge = (status: string) => {
    switch (status) {
      case 'verified':
        return <Badge variant="success">Verified</Badge>;
      case 'rejected':
        return <Badge variant="danger">Rejected</Badge>;
      default:
        return <Badge variant="warning">Pending Review</Badge>;
    }
  };

  return (
    <div className="co-org-switcher" ref={dropdownRef} style={{ position: 'relative' }}>
      <button
        type="button"
        className="co-btn co-btn-secondary"
        onClick={() => setIsOpen((prev) => !prev)}
        aria-expanded={isOpen}
        aria-haspopup="listbox"
        aria-label="Select organization workspace"
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 10,
          padding: '6px 12px',
          maxWidth: 320,
          textAlign: 'left',
          fontSize: '0.85rem',
        }}
        disabled={isLoading}
      >
        <span style={{ color: 'var(--co-primary-600)', display: 'flex', alignItems: 'center' }}>
          <IconBuilding size={16} />
        </span>
        <span style={{ flex: 1, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {activeOrg ? (
            <span style={{ fontWeight: 600 }}>{activeOrg.club_name}</span>
          ) : (
            <span style={{ color: 'var(--co-text-muted)' }}>No Workspace Selected</span>
          )}
        </span>
        {activeOrg && renderBadge(activeOrg.verification_status)}
        <span style={{ fontSize: '0.7rem', color: 'var(--co-text-muted)', marginLeft: 4 }}>▼</span>
      </button>

      {isOpen && (
        <div
          role="listbox"
          aria-label="Available workspaces"
          style={{
            position: 'absolute',
            top: 'calc(100% + 4px)',
            left: 0,
            width: 320,
            maxHeight: 360,
            overflowY: 'auto',
            background: 'var(--co-bg-surface)',
            border: '1px solid var(--co-border-subtle)',
            borderRadius: 'var(--co-radius-md)',
            boxShadow: 'var(--co-shadow-md)',
            zIndex: 50,
            padding: 4,
          }}
        >
          <div
            style={{
              padding: '6px 10px',
              fontSize: '0.75rem',
              fontWeight: 600,
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
              color: 'var(--co-text-muted)',
              borderBottom: '1px solid var(--co-border-subtle)',
            }}
          >
            My Workspaces ({organizations.length})
          </div>

          {organizations.length === 0 ? (
            <div style={{ padding: '16px 12px', textAlign: 'center', color: 'var(--co-text-muted)', fontSize: '0.85rem' }}>
              You don&apos;t have any active organization workspaces yet.
            </div>
          ) : (
            organizations.map((org) => {
              const isSelected = org.id === activeOrgId;
              return (
                <div
                  key={org.id}
                  role="option"
                  aria-selected={isSelected}
                  tabIndex={0}
                  onClick={() => {
                    onSelectOrg(org.id);
                    setIsOpen(false);
                  }}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      onSelectOrg(org.id);
                      setIsOpen(false);
                    }
                  }}
                  style={{
                    padding: '8px 10px',
                    borderRadius: 'var(--co-radius-sm)',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    gap: 8,
                    background: isSelected ? 'var(--co-bg-subtle)' : 'transparent',
                    transition: 'background var(--co-transition-fast)',
                  }}
                >
                  <div style={{ minWidth: 0, flex: 1 }}>
                    <div style={{ fontWeight: 600, fontSize: '0.85rem', color: 'var(--co-text-main)' }}>
                      {org.club_name}
                    </div>
                    <div
                      style={{
                        fontSize: '0.75rem',
                        color: 'var(--co-text-muted)',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                      }}
                    >
                      {org.college_name}
                    </div>
                  </div>
                  {renderBadge(org.verification_status)}
                </div>
              );
            })
          )}

          <div style={{ borderTop: '1px solid var(--co-border-subtle)', marginTop: 4, paddingTop: 4 }}>
            <button
              type="button"
              className="co-btn co-btn-ghost"
              onClick={() => {
                setIsOpen(false);
                onCreateOrgClick();
              }}
              style={{
                width: '100%',
                justifyContent: 'flex-start',
                padding: '8px 10px',
                fontSize: '0.85rem',
                color: 'var(--co-primary-600)',
                display: 'inline-flex',
                alignItems: 'center',
                gap: 8,
              }}
            >
              <IconPlus size={16} />
              <span>Create New Workspace</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

