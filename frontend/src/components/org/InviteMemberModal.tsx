import { useState, type FC, type FormEvent } from 'react';
import { Dialog } from '../common/Dialog';
import { Alert } from '../common/Alert';
import { Spinner } from '../common/Spinner';
import { createInvitation } from '../../api/organizations';
import { ApiError } from '../../api/client';
import type { InvitationResponse, InvitableRole } from '../../api/types';

interface InviteMemberModalProps {
  isOpen: boolean;
  onClose: () => void;
  orgId: string;
  clubName: string;
  isVerified: boolean;
  onSuccess: (invitation: InvitationResponse) => void;
  authToken?: string | null;
}

const AVAILABLE_ROLES: { id: InvitableRole; label: string; description: string }[] = [
  {
    id: 'OFFICE_BEARER',
    label: 'Office Bearer',
    description: 'Full workspace authority: invite members, delegate leads, manage tasks, and configure events.',
  },
  {
    id: 'COORDINATOR',
    label: 'Coordinator',
    description: 'Operational team member: assigned tasks, submit proofs, and assist with event setup.',
  },
  {
    id: 'DEPARTMENT_LEAD',
    label: 'Department Lead',
    description: 'Leads a functional department (e.g. Design, Logistics) and manages department tasks.',
  },
  {
    id: 'EVENT_LEAD',
    label: 'Event Lead',
    description: 'Lead organizer for specific events, empowered to manage event tasks and check-in desks.',
  },
  {
    id: 'REGISTRATION_STAFF',
    label: 'Registration Staff',
    description: 'Event-day attendee check-in desk volunteer with privacy-masked roster access.',
  },
];

export const InviteMemberModal: FC<InviteMemberModalProps> = ({
  isOpen,
  onClose,
  orgId,
  clubName,
  isVerified,
  onSuccess,
  authToken,
}) => {
  const [email, setEmail] = useState('');
  const [roleName, setRoleName] = useState<InvitableRole>('COORDINATOR');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const trimmedEmail = email.trim().toLowerCase();

    if (!trimmedEmail || !trimmedEmail.includes('@') || !trimmedEmail.includes('.')) {
      setError('Please provide a valid institutional or personal email address.');
      return;
    }

    if (!isVerified) {
      setError('Cannot dispatch invitations while organization verification is pending (Policy FPC-02).');
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      const invitation = await createInvitation(
        orgId,
        {
          email: trimmedEmail,
          role_name: roleName,
          scope_type: 'organization',
        },
        { authToken },
      );
      setEmail('');
      setRoleName('COORDINATOR');
      onSuccess(invitation);
      onClose();
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 503) {
          setError(
            'Transactional email delivery is unconfigured on the server (Policy FPC-06). ' +
            'Invitations fail closed and are automatically rolled back to prevent orphan tokens.',
          );
        } else {
          setError(err.detail);
        }
      } else {
        setError('Failed to dispatch invitation. Please check your network and try again.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog
      isOpen={isOpen}
      onClose={onClose}
      title="Invite Team Member"
      description={`Send a single-use role invitation to join ${clubName}.`}
      maxWidth="560px"
    >
      <form onSubmit={handleSubmit} noValidate>
        {error && (
          <div style={{ marginBottom: 16 }}>
            <Alert variant="danger" title="Invitation Delivery Notice">
              {error}
            </Alert>
          </div>
        )}

        {!isVerified && (
          <div style={{ marginBottom: 16 }}>
            <Alert variant="warning" title="Verification Prerequisite">
              Invitations cannot be issued while this workspace is in <code>pending_verification</code> status.
              A platform administrator must review and verify this workspace before members can be invited.
            </Alert>
          </div>
        )}

        <div className="co-form-group">
          <label htmlFor="invite-email" className="co-label co-label-required">
            Recipient Email Address
          </label>
          <input
            id="invite-email"
            type="email"
            className="co-input"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="colleague@campus.edu"
            required
            disabled={isSubmitting || !isVerified}
            autoFocus
          />
          <span style={{ fontSize: '0.75rem', color: 'var(--co-text-muted)', marginTop: 4, display: 'block' }}>
            The recipient will receive a single-use invitation valid for 7 days.
          </span>
        </div>

        <div className="co-form-group">
          <label htmlFor="invite-role" className="co-label co-label-required">
            Assigned Workspace Role
          </label>
          <select
            id="invite-role"
            className="co-input"
            value={roleName}
            onChange={(e) => setRoleName(e.target.value as InvitableRole)}
            disabled={isSubmitting || !isVerified}
          >
            {AVAILABLE_ROLES.map((r) => (
              <option key={r.id} value={r.id}>
                {r.label}
              </option>
            ))}
          </select>
          <div
            style={{
              marginTop: 8,
              padding: '8px 12px',
              borderRadius: 'var(--co-radius-sm)',
              background: 'var(--co-bg-subtle)',
              border: '1px solid var(--co-border-subtle)',
              fontSize: '0.8rem',
              color: 'var(--co-text-muted)',
            }}
          >
            <strong>Role Scope:</strong>{' '}
            {AVAILABLE_ROLES.find((r) => r.id === roleName)?.description}
          </div>
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
            className="co-btn co-btn-primary"
            disabled={isSubmitting || !isVerified || !email.trim()}
          >
            {isSubmitting ? (
              <>
                <Spinner size="sm" />
                <span>Sending Invitation...</span>
              </>
            ) : (
              <span>Send Invitation</span>
            )}
          </button>
        </div>
      </form>
    </Dialog>
  );
};
