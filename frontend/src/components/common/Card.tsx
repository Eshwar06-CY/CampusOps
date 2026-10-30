import type { FC, ReactNode } from 'react';

interface CardProps {
  children: ReactNode;
  className?: string;
}

export const Card: FC<CardProps> = ({ children, className = '' }) => {
  return <div className={`co-card ${className}`}>{children}</div>;
};

interface CardHeaderProps {
  title: ReactNode;
  subtitle?: ReactNode;
  action?: ReactNode;
  className?: string;
}

export const CardHeader: FC<CardHeaderProps> = ({ title, subtitle, action, className = '' }) => {
  return (
    <div className={`co-card-header ${className}`}>
      <div>
        <h3 className="co-card-title">{title}</h3>
        {subtitle && <p className="co-card-subtitle">{subtitle}</p>}
      </div>
      {action && <div>{action}</div>}
    </div>
  );
};

export const CardBody: FC<{ children: ReactNode; className?: string }> = ({ children, className = '' }) => {
  return <div className={`co-card-body ${className}`}>{children}</div>;
};

export const CardFooter: FC<{ children: ReactNode; className?: string }> = ({ children, className = '' }) => {
  return <div className={`co-card-footer ${className}`}>{children}</div>;
};

