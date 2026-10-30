import { useState, type FC, type FormEvent } from 'react';
import { Dialog } from '../common/Dialog';
import { Alert } from '../common/Alert';
import { Spinner } from '../common/Spinner';
import { verifyOrganization } from '../../api/organizations';
import { ApiError } from '../../api/client';
import type { OrganizationDetailResponse } from '../../api/types';

interface PlatformVerifyModalProps {
  isOpen: boolean;
  onClose: () => void;
  orgId: string;
  clubName: string;
  collegeName: string;
  onSuccess: (updated: OrganizationDetailResponse) => void;
  authToken?: string | null;
}

export const PlatformVerifyModal: FC<PlatformVerifyModalProps> = ({
  isOpen,
  onClose,
  orgId,
  clubName,
  collegeName,
  onSuccess,
  authToken,
}) => {
  const [decision, setDecision] = useState<'verified' | 'rejected'>('verified');
  const [note, setNote] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const trimmedNote = note.trim();

    if (decision === 'rejected' && !trimmedNote) {
      setError('A documented explanation is required when rejecting workspace verification.');
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      const updated = await verifyOrganization(
        orgId,
        {
          decision,
          note: trimmedNote || null,
        },
        { authToken },
      );
      onSuccess(updated);
      onClose();
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.detail);
      } else {
        setError('Failed to submit verification decision. Please try again.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog
      isOpen={isOpen}
      onClose={onClose}
      title="Platform Administrator Verification Review"
      description={`Review affiliation and status for "${clubName}" at ${collegeName}.`}
      maxWidth="560px"
    >
      <form onSubmit={handleSubmit} noValidate>
        {error && (
          <div style={{ marginBottom: 16 }}>
            <Alert variant="danger" title="Review Submission Error">
              {error}
            </Alert>
          </div>
        )}

        <div
          style={{
            background: 'var(--co-info-50)',
            border: '1px solid var(--co-info-200)',
            borderRadius: 'var(--co-radius-md)',
            padding: '12px 16px',
            fontSize: '0.825rem',
            color: 'var(--co-info-900)',
            marginBottom: 20,
            lineHeight: 1.5,
          }}
        >
          <strong>Platform Authority Notice:</strong> You are evaluating this workspace as an authorized platform administrator.
          Approving marks the workspace as verified and unblocks team invitations, role delegations, and event publishing.
          Rejection revokes privileged workspace capabilities and records your reason into the audit ledger.
        </div>

        <div className="co-form-group">
          <label className="co-label co-label-required" style={{ marginBottom: 8 }}>
            Verification Decision
          </label>
          <div style={{ display: 'flex', gap: 12 }}>
            <label
              style={{
                flex: 1,
                padding: '12px 16px',
                border: `2px solid ${decision === 'verified' ? 'var(--co-success-600)' : 'var(--co-border-subtle)'}`,
                borderRadius: 'var(--co-radius-md)',
                background: decision === 'verified' ? 'var(--co-success-50)' : 'var(--co-bg-surface)',
                cursor: 'pointer',
                display: 'flex',
                flexDirection: 'column',
                gap: 4,
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <input
                  type="radio"
                  name="verification_decision"
                  value="verified"
                  checked={decision === 'verified'}
                  onChange={() => setDecision('verified')}
                  disabled={isSubmitting}
                />
                <strong style={{ color: 'var(--co-success-800)', fontSize: '0.9rem' }}>Approve (Verified)</strong>
              </div>
              <span style={{ fontSize: '0.75rem', color: 'var(--co-text-muted)', marginLeft: 22 }}>
                Confirm legitimate collegiate chapter and unblock all operational features.
              </span>
            </label>

            <label
              style={{
                flex: 1,
                padding: '12px 16px',
                border: `2px solid ${decision === 'rejected' ? 'var(--co-danger-600)' : 'var(--co-border-subtle)'}`,
                borderRadius: 'var(--co-radius-md)',
                background: decision === 'rejected' ? 'var(--co-danger-50)' : 'var(--co-bg-surface)',
                cursor: 'pointer',
                display: 'flex',
                flexDirection: 'column',
                gap: 4,
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <input
                  type="radio"
                  name="verification_decision"
                  value="rejected"
                  checked={decision === 'rejected'}
                  onChange={() => setDecision('rejected')}
                  disabled={isSubmitting}
                />
                <strong style={{ color: 'var(--co-danger-800)', fontSize: '0.9rem' }}>Reject</strong>
              </div>
              <span style={{ fontSize: '0.75rem', color: 'var(--co-text-muted)', marginLeft: 22 }}>
                Reject affiliation. Mandatory audit reason required.
              </span>
            </label>
          </div>
        </div>

        <div className="co-form-group">
          <div className="co-label-row">
            <label htmlFor="review-note" className={`co-label ${decision === 'rejected' ? 'co-label-required' : ''}`}>
              Review Note & Explanation
            </label>
            <span className="co-char-count">{note.length}/1000</span>
          </div>
          <textarea
            id="review-note"
            className="co-input"
            rows={4}
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder={
              decision === 'rejected'
                ? 'Document the reason for rejection (e.g. invalid collegiate domain or unrecognized chapter)...'
                : 'Optional reviewer remarks or approval notes...'
            }
            maxLength={1000}
            required={decision === 'rejected'}
            disabled={isSubmitting}
            style={{ width: '100%', resize: 'vertical' }}
          />
        </div>

        <div
          style={{
            display: 'flex',
            justifyContent: 'flex-end',
            gap: 12,
            marginTop: 24,
            paddingTop: 16,
            borderTop: '1px solid var(--co-border-subtle)',
          }}
        >
          <button
            type="button"
            className="co-btn co-btn-secondary"
            onClick={onClose}
            disabled={isSubmitting}
          >
            Cancel
          </button>
          <button
            type="submit"
            className={`co-btn ${decision === 'verified' ? 'co-btn-primary' : 'co-btn-danger'}`}
            disabled={isSubmitting || (decision === 'rejected' && note.trim().length === 0)}
          >
            {isSubmitting ? (
              <>
                <Spinner size="sm" />
                <span>Recording Decision...</span>
              </>
            ) : decision === 'verified' ? (
              <span>Confirm Verification</span>
            ) : (
              <span>Confirm Rejection</span>
            )}
          </button>
        </div>
      </form>
    </Dialog>
  );
};
