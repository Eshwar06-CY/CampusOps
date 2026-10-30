import type { FC, ReactNode } from 'react';

export type BadgeVariant = 'success' | 'warning' | 'danger' | 'neutral' | 'primary';

export interface BadgeProps {
  variant?: BadgeVariant;
  children: ReactNode;
  icon?: ReactNode;
  dot?: boolean;
  className?: string;
}

export const Badge: FC<BadgeProps> = ({
  variant = 'neutral',
  children,
  icon,
  dot = false,
  className = '',
}) => {
  return (
    <span className={`co-badge co-badge-${variant} ${className}`}>
      {dot && <span className="co-badge-dot" aria-hidden="true" />}
      {icon && <span style={{ display: 'inline-flex', alignItems: 'center' }}>{icon}</span>}
      <span>{children}</span>
    </span>
  );
};
