import type { FC } from 'react';
import { IconShield, IconTicket, IconCheckCircle } from '../common/Icons';

export const Footer: FC = () => {
  return (
    <footer
      style={{
        borderTop: '1px solid var(--co-border-subtle)',
        padding: '24px 16px',
        fontSize: '0.8rem',
        color: 'var(--co-text-muted)',
        backgroundColor: 'var(--co-bg-surface)',
      }}
      role="contentinfo"
    >
      <div
        style={{
          maxWidth: 1200,
          margin: '0 auto',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: 16,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '4px 8px', flexWrap: 'wrap' }}>
          <strong style={{ color: 'var(--co-text-main)' }}>CampusOps</strong>
          <span>·</span>
          <span>Modular Monolith Event Operations Platform</span>
        </div>
        <div style={{ display: 'flex', gap: 20, flexWrap: 'wrap' }}>
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
            <IconCheckCircle size={14} style={{ color: 'var(--co-success-600)' }} />
            <span>Online-First Check-In</span>
          </span>
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
            <IconTicket size={14} style={{ color: 'var(--co-primary-600)' }} />
            <span>Zero-PII Digital Passes</span>
          </span>
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
            <IconShield size={14} style={{ color: 'var(--co-info-600)' }} />
            <span>Role-Gated Audit Ledger</span>
          </span>
        </div>
      </div>
    </footer>
  );
};
