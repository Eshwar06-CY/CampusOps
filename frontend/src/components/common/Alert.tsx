import type { FC, ReactNode } from 'react';
import { IconCheckCircle, IconAlertTriangle, IconAlertCircle, IconInfo } from './Icons';

export type AlertVariant = 'info' | 'success' | 'warning' | 'danger';

export interface AlertProps {
  variant?: AlertVariant;
  title?: string;
  children: ReactNode;
  action?: ReactNode;
  className?: string;
}

export const Alert: FC<AlertProps> = ({
  variant = 'info',
  title,
  children,
  action,
  className = '',
}) => {
  const getIcon = () => {
    switch (variant) {
      case 'success':
        return <IconCheckCircle size={20} style={{ color: 'var(--co-success-600)' }} />;
      case 'warning':
        return <IconAlertTriangle size={20} style={{ color: 'var(--co-warning-600)' }} />;
      case 'danger':
        return <IconAlertCircle size={20} style={{ color: 'var(--co-danger-600)' }} />;
      default:
        return <IconInfo size={20} style={{ color: 'var(--co-primary-600)' }} />;
    }
  };

  return (
    <div
      className={`co-alert co-alert-${variant} ${className}`}
      role={variant === 'danger' ? 'alert' : 'region'}
      aria-live={variant === 'danger' ? 'assertive' : 'polite'}
    >
      <div style={{ flexShrink: 0, marginTop: 2 }}>{getIcon()}</div>
      <div style={{ flex: 1, minWidth: 0 }}>
        {title && <div style={{ fontWeight: 600, marginBottom: 4, letterSpacing: '-0.01em' }}>{title}</div>}
        <div style={{ fontSize: '0.875rem' }}>{children}</div>
      </div>
      {action && <div style={{ flexShrink: 0, marginLeft: 8 }}>{action}</div>}
    </div>
  );
};
