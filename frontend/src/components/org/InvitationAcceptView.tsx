import { useState, type FC, type FormEvent } from 'react';
import { acceptInvitation } from '../../api/organizations';
import { ApiError } from '../../api/client';
import type { InvitationAcceptResponse } from '../../api/types';
import { Alert } from '../common/Alert';
import { Spinner } from '../common/Spinner';
import { IconMail, IconCheckCircle, IconArrowRight } from '../common/Icons';

interface InvitationAcceptViewProps {
  initialToken?: string;
  legacyQueryRejected?: boolean;
  onAcceptSuccess: (response: InvitationAcceptResponse) => void;
  authToken?: string | null;
}

export const InvitationAcceptView: FC<InvitationAcceptViewProps> = ({
  initialToken = '',
  legacyQueryRejected = false,
  onAcceptSuccess,
  authToken,
}) => {
  const [token, setToken] = useState(initialToken);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [acceptedResult, setAcceptedResult] = useState<InvitationAcceptResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const cleanToken = token.trim();
    if (!cleanToken) {
      setError('Please provide your invitation token.');
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      const result = await acceptInvitation({ token: cleanToken }, { authToken });
      setAcceptedResult(result);
      onAcceptSuccess(result);
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 401) {
          setError(
            'Authentication is required to accept an invitation. ' +
            'Your invitation must be bound to your authenticated user identity.',
          );
        } else if (err.status === 403) {
          setError(
            'Email mismatch: This invitation was issued for a different email address than your current authenticated account.',
          );
        } else if (err.status === 404) {
          setError('Invitation token is invalid, unrecognized, or does not exist.');
        } else if (err.status === 409) {
          setError('You are already an active member of this organization workspace.');
        } else if (err.status === 400) {
          setError(err.detail || 'This invitation has expired or has already been accepted/revoked.');
        } else {
          setError(err.detail);
        }
      } else {
        setError('Failed to process invitation acceptance. Please check your connection and try again.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  if (acceptedResult) {
    return (
      <div className="co-card" style={{ maxWidth: 540, margin: '40px auto' }}>
        <div className="co-card-body" style={{ textAlign: 'center', padding: '36px 24px' }}>
          <div
            style={{
              width: 56,
              height: 56,
              borderRadius: 'var(--co-radius-full)',
              background: 'var(--co-success-50)',
              color: 'var(--co-success-600)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 16px',
            }}
          >
            <IconCheckCircle size={32} />
          </div>

          <h2 style={{ fontSize: 'var(--co-text-2xl)', fontWeight: 700, margin: '0 0 8px' }}>
            Invitation Accepted!
          </h2>
          <p style={{ color: 'var(--co-text-muted)', fontSize: '0.9rem', marginBottom: 24 }}>
            You have successfully joined the organization workspace.
          </p>

          <div
            style={{
              background: 'var(--co-bg-subtle)',
              border: '1px solid var(--co-border-subtle)',
              borderRadius: 'var(--co-radius-md)',
              padding: '16px',
              textAlign: 'left',
              fontSize: '0.85rem',
              marginBottom: 24,
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
              <span style={{ color: 'var(--co-text-muted)' }}>Assigned Role:</span>
              <strong style={{ color: 'var(--co-text-main)' }}>{acceptedResult.role_name}</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
              <span style={{ color: 'var(--co-text-muted)' }}>Role Scope:</span>
              <span style={{ textTransform: 'capitalize' }}>{acceptedResult.scope_type}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--co-text-muted)' }}>Membership Status:</span>
              <span style={{ color: 'var(--co-success-600)', fontWeight: 600 }}>Active</span>
            </div>
          </div>

          <button
            type="button"
            className="co-btn co-btn-primary"
            onClick={() => onAcceptSuccess(acceptedResult)}
            style={{ display: 'inline-flex', alignItems: 'center', gap: 8, width: '100%', justifyContent: 'center' }}
          >
            <span>Proceed to Workspace</span>
            <IconArrowRight size={16} />
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="co-card" style={{ maxWidth: 540, margin: '40px auto' }}>
      <div className="co-card-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div
            style={{
              width: 36,
              height: 36,
              borderRadius: 'var(--co-radius-md)',
              background: 'var(--co-primary-50)',
              color: 'var(--co-primary-600)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <IconMail size={20} />
          </div>
          <div>
            <h3 className="co-card-title">Accept Workspace Invitation</h3>
            <p className="co-card-subtitle">
              Join an organization workspace with your verified collegiate account.
            </p>
          </div>
        </div>
      </div>

      <div className="co-card-body">
        {legacyQueryRejected && (
          <div style={{ marginBottom: 16 }}>
            <Alert variant="warning" title="Legacy Link Format Rejected">
              Legacy query-parameter invitation links are no longer supported for security. For your protection, invitation credentials cannot be accepted from URL query strings. Please enter or paste your invitation token manually below.
            </Alert>
          </div>
        )}

        {error && (
          <div style={{ marginBottom: 16 }}>
            <Alert variant="danger" title="Acceptance Blocked">
              {error}
            </Alert>
          </div>
        )}

        <form onSubmit={handleSubmit} noValidate>
          <div className="co-form-group">
            <label htmlFor="invitation-token" className="co-label co-label-required">
              Single-Use Invitation Token
            </label>
            <input
              id="invitation-token"
              type="text"
              className="co-input"
              value={token}
              onChange={(e) => setToken(e.target.value)}
              placeholder="Paste raw invitation token..."
              required
              disabled={isSubmitting}
              autoFocus
              style={{ fontFamily: 'var(--co-font-mono)', fontSize: '0.85rem' }}
            />
            <span style={{ fontSize: '0.75rem', color: 'var(--co-text-muted)', marginTop: 4, display: 'block' }}>
              Tokens are provided via official email invitation and expire after 7 days.
            </span>
          </div>

          <div
            style={{
              background: 'var(--co-bg-subtle)',
              border: '1px solid var(--co-border-subtle)',
              borderRadius: 'var(--co-radius-sm)',
              padding: '10px 14px',
              fontSize: '0.8rem',
              color: 'var(--co-text-muted)',
              marginBottom: 20,
              lineHeight: 1.5,
            }}
          >
            <strong>Security Boundary:</strong> Invitations are transmitted securely via JSON POST body. Tokens are never stored in browser history or web storage.
          </div>

          <button
            type="submit"
            className="co-btn co-btn-primary"
            disabled={isSubmitting || !token.trim()}
            style={{ width: '100%', justifyContent: 'center' }}
          >
            {isSubmitting ? (
              <>
                <Spinner size="sm" />
                <span>Validating &amp; Accepting...</span>
              </>
            ) : (
              <span>Accept Invitation</span>
            )}
          </button>
        </form>
      </div>
    </div>
  );
};
