import { useState, type FC, type FormEvent } from 'react';
import { Dialog } from '../common/Dialog';
import { Alert } from '../common/Alert';
import { Spinner } from '../common/Spinner';
import { createOrganization } from '../../api/organizations';
import { ApiError } from '../../api/client';
import type { OrganizationResponse } from '../../api/types';

interface CreateOrgModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (newOrg: OrganizationResponse) => void;
  authToken?: string | null;
}

export const CreateOrgModal: FC<CreateOrgModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
  authToken,
}) => {
  const [collegeName, setCollegeName] = useState('');
  const [clubName, setClubName] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const college = collegeName.trim();
    const club = clubName.trim();

    if (college.length < 2) {
      setError('College or university name must be at least 2 characters.');
      return;
    }
    if (club.length < 2) {
      setError('Student club or organization name must be at least 2 characters.');
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      const created = await createOrganization(
        {
          college_name: college,
          club_name: club,
        },
        { authToken },
      );
      setCollegeName('');
      setClubName('');
      onSuccess(created);
      onClose();
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.detail);
      } else {
        setError('Failed to create workspace. Please check your network and try again.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog
      isOpen={isOpen}
      onClose={onClose}
      title="Create Organization Workspace"
      description="Establish a centralized operational workspace for your student club, chapter, or collegiate team."
      maxWidth="540px"
    >
      <form onSubmit={handleSubmit} noValidate>
        {error && (
          <div style={{ marginBottom: 16 }}>
            <Alert variant="danger" title="Creation Blocked">
              {error}
            </Alert>
          </div>
        )}

        <div
          style={{
            background: 'var(--co-bg-subtle)',
            border: '1px solid var(--co-border-subtle)',
            borderRadius: 'var(--co-radius-md)',
            padding: '12px 16px',
            fontSize: '0.825rem',
            color: 'var(--co-text-muted)',
            marginBottom: 20,
            lineHeight: 1.5,
          }}
        >
          <strong style={{ color: 'var(--co-text-main)', display: 'block', marginBottom: 4 }}>
            Governance Policy Note (FPC-02 / FPC-03):
          </strong>
          New workspaces are provisioned in <code style={{ color: 'var(--co-warning-700)' }}>pending_verification</code> status.
          You will be granted <strong style={{ color: 'var(--co-text-main)' }}>Primary Workspace Administrator</strong> rights.
          External publishing and team invitations unlock once a platform administrator verifies your academic affiliation.
        </div>

        <div className="co-form-group">
          <div className="co-label-row">
            <label htmlFor="modal-college-name" className="co-label co-label-required">
              College / University Name
            </label>
            <span className="co-char-count">{collegeName.length}/255</span>
          </div>
          <input
            id="modal-college-name"
            type="text"
            className="co-input"
            value={collegeName}
            onChange={(e) => setCollegeName(e.target.value)}
            placeholder="e.g. Stanford University"
            maxLength={255}
            required
            disabled={isSubmitting}
            autoFocus
          />
        </div>

        <div className="co-form-group">
          <div className="co-label-row">
            <label htmlFor="modal-club-name" className="co-label co-label-required">
              Student Club / Chapter Name
            </label>
            <span className="co-char-count">{clubName.length}/255</span>
          </div>
          <input
            id="modal-club-name"
            type="text"
            className="co-input"
            value={clubName}
            onChange={(e) => setClubName(e.target.value)}
            placeholder="e.g. AI Safety Student Group"
            maxLength={255}
            required
            disabled={isSubmitting}
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
            className="co-btn co-btn-primary"
            disabled={isSubmitting || collegeName.trim().length < 2 || clubName.trim().length < 2}
          >
            {isSubmitting ? (
              <>
                <Spinner size="sm" />
                <span>Creating Workspace...</span>
              </>
            ) : (
              <span>Create Workspace</span>
            )}
          </button>
        </div>
      </form>
    </Dialog>
  );
};
