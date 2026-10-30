import { createContext, useContext, useState, useCallback, type FC, type ReactNode } from 'react';
import { IconCheckCircle, IconAlertCircle, IconInfo, IconX } from './Icons';

export type ToastVariant = 'success' | 'error' | 'info';

export interface ToastMessage {
  id: string;
  variant: ToastVariant;
  title: string;
  description?: string;
}

interface ToastContextValue {
  showToast: (variant: ToastVariant, title: string, description?: string) => void;
  removeToast: (id: string) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

export const ToastProvider: FC<{ children: ReactNode }> = ({ children }) => {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const showToast = useCallback(
    (variant: ToastVariant, title: string, description?: string) => {
      const id = `toast-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
      setToasts((prev) => [...prev, { id, variant, title, description }]);

      setTimeout(() => {
        removeToast(id);
      }, 4000);
    },
    [removeToast],
  );

  return (
    <ToastContext.Provider value={{ showToast, removeToast }}>
      {children}
      <div className="co-toast-container" aria-live="polite" aria-atomic="true">
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className="co-toast"
            role="status"
            style={{
              borderLeft: `4px solid ${
                toast.variant === 'success'
                  ? 'var(--co-success-500)'
                  : toast.variant === 'error'
                  ? 'var(--co-danger-500)'
                  : 'var(--co-primary-400)'
              }`,
            }}
          >
            <div style={{ flexShrink: 0 }}>
              {toast.variant === 'success' && (
                <IconCheckCircle size={20} style={{ color: 'var(--co-success-500)' }} />
              )}
              {toast.variant === 'error' && (
                <IconAlertCircle size={20} style={{ color: 'var(--co-danger-500)' }} />
              )}
              {toast.variant === 'info' && (
                <IconInfo size={20} style={{ color: 'var(--co-primary-400)' }} />
              )}
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontWeight: 600, fontSize: '0.875rem' }}>{toast.title}</div>
              {toast.description && (
                <div style={{ fontSize: '0.8rem', color: '#cbd5e1', marginTop: 2 }}>
                  {toast.description}
                </div>
              )}
            </div>
            <button
              type="button"
              onClick={() => removeToast(toast.id)}
              className="co-btn co-btn-ghost co-btn-sm"
              style={{ color: '#94a3b8', padding: '2px 4px' }}
              aria-label="Dismiss notification"
            >
              <IconX size={14} />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
};

export function useToast(): ToastContextValue {
  const context = useContext(ToastContext);
  if (!context) {
    // Graceful fallback if invoked outside ToastProvider
    return {
      showToast: () => {},
      removeToast: () => {},
    };
  }
  return context;
}

