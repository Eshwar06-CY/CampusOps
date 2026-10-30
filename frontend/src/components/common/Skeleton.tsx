import type { FC, HTMLAttributes } from 'react';

export interface SkeletonProps extends HTMLAttributes<HTMLDivElement> {
  width?: string | number;
  height?: string | number;
  borderRadius?: string | number;
  className?: string;
}

export const Skeleton: FC<SkeletonProps> = ({
  width = '100%',
  height = '1rem',
  borderRadius = 'var(--co-radius-sm)',
  className = '',
  style,
  ...props
}) => {
  return (
    <div
      className={`co-skeleton ${className}`}
      style={{
        width,
        height,
        borderRadius,
        ...style,
      }}
      aria-hidden="true"
      {...props}
    />
  );
};

export const CardSkeleton: FC<{ lines?: number }> = ({ lines = 3 }) => (
  <div className="co-card" aria-busy="true" aria-label="Loading content...">
    <div className="co-card-header">
      <Skeleton width="40%" height="1.5rem" />
      <Skeleton width="20%" height="1.25rem" />
    </div>
    <div className="co-card-body">
      <Skeleton width="75%" height="1rem" style={{ marginBottom: 12 }} />
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton key={i} width={`${90 - i * 15}%`} height="0.875rem" style={{ marginBottom: 8 }} />
      ))}
    </div>
  </div>
);

export const TableSkeleton: FC<{ rows?: number; columns?: number }> = ({ rows = 4, columns = 5 }) => (
  <div className="co-table-container" aria-busy="true" aria-label="Loading table records...">
    <table className="co-table">
      <thead>
        <tr>
          {Array.from({ length: columns }).map((_, i) => (
            <th key={i}>
              <Skeleton width="70%" height="0.875rem" />
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {Array.from({ length: rows }).map((_, r) => (
          <tr key={r}>
            {Array.from({ length: columns }).map((_, c) => (
              <td key={c}>
                <Skeleton width={c === 0 ? '80%' : '60%'} height="1rem" />
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  </div>
);

