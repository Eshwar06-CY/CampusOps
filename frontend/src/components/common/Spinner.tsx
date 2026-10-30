import type { FC } from 'react';

interface SpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  className?: string;
  label?: string;
}

export const Spinner: FC<SpinnerProps> = ({ size = 'md', className = '', label = 'Loading...' }) => {
  const pixelSize = size === 'sm' ? 16 : size === 'lg' ? 32 : 20;

  return (
    <svg
      className={`co-spinner ${className}`}
      width={pixelSize}
      height={pixelSize}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      role="status"
      aria-label={label}
    >
      <circle cx="12" cy="12" r="10" strokeOpacity="0.25" />
      <path d="M12 2a10 10 0 0 1 10 10" />
    </svg>
  );
};

