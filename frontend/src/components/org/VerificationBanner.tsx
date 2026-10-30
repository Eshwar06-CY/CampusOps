import type { FC } from 'react';
import { Alert } from '../common/Alert';
import { IconShield, IconCheckCircle } from '../common/Icons';
import { formatDateTime } from '../../utils/formatters';
import type { OrganizationDetailResponse } from '../../api/types';

interface VerificationBannerProps {
  organization: OrganizationDetailResponse;
  isPlatformAdmin: boolean;
  onOpenVerifyModal: () => void;
}

export const VerificationBanner: FC<VerificationBannerProps> = ({
  organization,
  isPlatformAdmin,
  onOpenVerifyModal,
}) => {
  const { verification_status, verification_note, verification_reviewed_at } = organization;

  if (verification_status === 'pending_verification') {
    return (
      <div className="co-verification-banner" style={{ marginBottom: 20 }}>
        <Alert
          variant="warning"
          title="Workspace Verification Pending (Policy FPC-02)"
          action={
            isPlatformAdmin ? (
              <button
                type="button"
                className="co-btn co-btn-secondary"
                onClick={onOpenVerifyModal}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 6,
                  borderColor: 'var(--co-warning-600)',
                  color: 'var(--co-warning-800)',
                  backgroundColor: '#ffffff',
                }}
              >
                <IconShield size={14} />
                <span>Review As Admin</span>
              </button>
            ) : null
          }
        >
          <div style={{ lineHeight: 1.5 }}>
            <p style={{ margin: 0 }}>
              This organization is awaiting identity verification by a platform administrator.
              While pending, <strong>member invitations</strong>, <strong>event publishing</strong>, and <strong>ticket issuance</strong> remain gated to preserve institutional boundary integrity.
            </p>
            {verification_note && (
              <div
                style={{
                  marginTop: 8,
                  padding: '6px 10px',
                  background: 'rgba(255, 255, 255, 0.6)',
                  borderRadius: 'var(--co-radius-sm)',
                  fontSize: '0.8rem',
                  fontFamily: 'var(--co-font-mono)',
                }}
              >
                Note: {verification_note}
              </div>
            )}
          </div>
        </Alert>
      </div>
    );
  }

  if (verification_status === 'rejected') {
    return (
      <div className="co-verification-banner" style={{ marginBottom: 20 }}>
        <Alert
          variant="danger"
          title="Workspace Verification Rejected"
          action={
            isPlatformAdmin ? (
              <button
                type="button"
                className="co-btn co-btn-secondary"
                onClick={onOpenVerifyModal}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 6,
                  borderColor: 'var(--co-danger-600)',
                  color: 'var(--co-danger-800)',
                  backgroundColor: '#ffffff',
                }}
              >
                <IconShield size={14} />
                <span>Re-evaluate Verification</span>
              </button>
            ) : null
          }
        >
          <div style={{ lineHeight: 1.5 }}>
            <p style={{ margin: 0 }}>
              Platform review for <strong>{organization.club_name}</strong> was rejected.
              Workspace operations are locked.
            </p>
            {verification_note && (
              <div
                style={{
                  marginTop: 8,
                  padding: '8px 12px',
                  background: 'rgba(255, 255, 255, 0.8)',
                  borderRadius: 'var(--co-radius-sm)',
                  fontSize: '0.825rem',
                  border: '1px solid var(--co-danger-200)',
                }}
              >
                <strong>Reviewer Reason:</strong> {verification_note}
                {verification_reviewed_at && (
                  <span style={{ display: 'block', fontSize: '0.75rem', color: 'var(--co-text-muted)', marginTop: 4 }}>
                    Reviewed on {formatDateTime(verification_reviewed_at)}
                  </span>
                )}
              </div>
            )}
          </div>
        </Alert>
      </div>
    );
  }

  // Verified
  return (
    <div
      className="co-verification-banner"
      style={{
        marginBottom: 20,
        padding: '12px 16px',
        background: 'var(--co-success-50)',
        border: '1px solid var(--co-success-200)',
        borderRadius: 'var(--co-radius-md)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: 12,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <IconCheckCircle size={20} style={{ color: 'var(--co-success-600)', flexShrink: 0 }} />
        <div>
          <strong style={{ color: 'var(--co-success-900)', fontSize: '0.875rem' }}>
            Institution Affiliation Verified
          </strong>
          <span
            style={{
              display: 'block',
              fontSize: '0.8rem',
              color: 'var(--co-success-700)',
              marginTop: 2,
            }}
          >
            All operational capabilities, team invitations, and event lifecycles are active.
            {verification_reviewed_at && ` Verified on ${formatDateTime(verification_reviewed_at)}.`}
          </span>
        </div>
      </div>

      {isPlatformAdmin && (
        <button
          type="button"
          className="co-btn co-btn-ghost"
          onClick={onOpenVerifyModal}
          style={{ fontSize: '0.775rem', color: 'var(--co-success-800)' }}
        >
          Change Status
        </button>
      )}
    </div>
  );
};
