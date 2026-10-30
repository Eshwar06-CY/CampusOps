import { useState, type FC, type FormEvent } from 'react';
import type { PublicRegistrationLookupResponse } from '../../api/types';
import { lookupRegistration, cancelRegistration } from '../../api/publicRegistration';
import { ApiError } from '../../api/client';
import { Dialog } from '../common/Dialog';
import { TextInput, Textarea } from '../common/Input';
import { Button } from '../common/Button';
import { Alert } from '../common/Alert';
import { Badge } from '../common/Badge';
import { formatDate } from '../../utils/formatters';
import { IconSearch, IconCheckCircle } from '../common/Icons';

interface RegistrationLookupModalProps {
  isOpen: boolean;
  onClose: () => void;
  registrationKey: string;
}

export const RegistrationLookupModal: FC<RegistrationLookupModalProps> = ({
  isOpen,
  onClose,
  registrationKey,
}) => {
  const [confirmationCode, setConfirmationCode] = useState('');
  const [lookupResult, setLookupResult] = useState<PublicRegistrationLookupResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Cancellation State
  const [isCancelling, setIsCancelling] = useState(false);
  const [cancelEmail, setCancelEmail] = useState('');
  const [cancelReason, setCancelReason] = useState('');
  const [cancelSuccessMsg, setCancelSuccessMsg] = useState<string | null>(null);

  const handleLookup = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setCancelSuccessMsg(null);
    if (!confirmationCode.trim()) {
      setError('Please enter your confirmation code.');
      return;
    }

    setIsLoading(true);
    try {
      const result = await lookupRegistration(registrationKey, confirmationCode.trim().toUpperCase());
      setLookupResult(result);
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        setError('No registration found matching this confirmation code for this event.');
      } else if (err instanceof ApiError) {
        setError(err.detail);
      } else {
        setError('Failed to reach lookup service.');
      }
      setLookupResult(null);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCancel = async (e: FormEvent) => {
    e.preventDefault();
    if (!lookupResult) return;
    setError(null);

    if (!cancelEmail.trim()) {
      setError('Please provide the primary contact email used during registration.');
      return;
    }
    if (!cancelReason.trim()) {
      setError('Please provide a reason for cancellation.');
      return;
    }

    setIsLoading(true);
    try {
      const response = await cancelRegistration(registrationKey, {
        confirmation_code: lookupResult.confirmation_code,
        contact_email: cancelEmail.trim().toLowerCase(),
        cancellation_reason: cancelReason.trim(),
      });
      setCancelSuccessMsg(response.message);
      setIsCancelling(false);
      // Refresh lookup status
      setLookupResult((prev) => (prev ? { ...prev, registration_status: 'cancelled' } : null));
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.detail);
      } else {
        setError('Failed to cancel registration.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleModalClose = () => {
    setConfirmationCode('');
    setLookupResult(null);
    setError(null);
    setIsCancelling(false);
    setCancelSuccessMsg(null);
    onClose();
  };

  return (
    <Dialog
      isOpen={isOpen}
      onClose={handleModalClose}
      title="Look Up or Manage Registration"
      description="Enter your unguessable confirmation code to view your registration status or submit a cancellation."
    >
      {error && (
        <Alert variant="danger" title="Notice">
          {error}
        </Alert>
      )}
      {cancelSuccessMsg && (
        <Alert variant="success" title="Cancellation Complete">
          {cancelSuccessMsg}
        </Alert>
      )}

      {!lookupResult ? (
        <form onSubmit={handleLookup}>
          <TextInput
            id="lookup-code"
            label="Confirmation Code"
            placeholder="e.g. REG-8B1A2C3D"
            value={confirmationCode}
            onChange={(e) => setConfirmationCode(e.target.value)}
            helpText="Found on your confirmation screen or issuance receipt."
            required
            disabled={isLoading}
            leftAddon={<IconSearch size={16} />}
          />
          <div style={{ marginTop: 16, display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
            <Button type="button" variant="ghost" onClick={handleModalClose}>
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              isLoading={isLoading}
              loadingText="Looking up..."
              leftIcon={<IconSearch size={16} />}
            >
              Find Registration
            </Button>
          </div>
        </form>
      ) : (
        <div>
          <div
            style={{
              padding: 16,
              backgroundColor: 'var(--co-bg-subtle)',
              borderRadius: 'var(--co-radius-lg)',
              border: '1px solid var(--co-border-subtle)',
              marginBottom: 16,
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
              <span style={{ fontFamily: 'var(--co-font-mono)', fontWeight: 700, fontSize: '1.15rem', color: 'var(--co-primary-600)' }}>
                {lookupResult.confirmation_code}
              </span>
              <Badge
                variant={lookupResult.registration_status === 'confirmed' ? 'success' : 'neutral'}
                icon={lookupResult.registration_status === 'confirmed' ? <IconCheckCircle size={12} /> : undefined}
              >
                {lookupResult.registration_status}
              </Badge>
            </div>

            <div style={{ fontSize: '0.875rem', color: 'var(--co-text-muted)' }}>
              <div>Format: <strong>{lookupResult.registration_type === 'team' ? `Team (${lookupResult.team_name})` : 'Individual'}</strong></div>
              <div>Registered on: <strong>{formatDate(lookupResult.created_at)}</strong></div>
              <div>Total Participants: <strong>{lookupResult.participant_count}</strong></div>
            </div>
          </div>

          <h5 style={{ margin: '0 0 8px 0', fontSize: '0.95rem', fontWeight: 600 }}>Registered Attendees:</h5>
          <ul style={{ margin: '0 0 16px 0', paddingLeft: 20, fontSize: '0.875rem' }}>
            {lookupResult.participants.map((p, idx) => (
              <li key={idx} style={{ marginBottom: 4 }}>
                <strong>{p.full_name}</strong> {p.team_role ? `(${p.team_role})` : ''}{' '}
                {p.is_primary_contact ? '— Primary Contact' : ''} [{p.status}]
              </li>
            ))}
          </ul>

          {/* Cancellation section */}
          {lookupResult.registration_status === 'confirmed' && !isCancelling && (
            <div style={{ borderTop: '1px solid var(--co-border-subtle)', paddingTop: 16 }}>
              <Button
                type="button"
                variant="danger"
                size="sm"
                onClick={() => setIsCancelling(true)}
              >
                Cancel Registration
              </Button>
            </div>
          )}

          {isCancelling && (
            <form onSubmit={handleCancel} style={{ borderTop: '1px solid var(--co-border-subtle)', paddingTop: 16 }}>
              <Alert variant="warning" title="Confirm Cancellation">
                Cancelling your registration will permanently invalidate all issued admission passes and release capacity.
              </Alert>
              <TextInput
                id="cancel-email"
                type="email"
                label="Primary Contact Email"
                placeholder="The email address used to register"
                value={cancelEmail}
                onChange={(e) => setCancelEmail(e.target.value)}
                required
                disabled={isLoading}
              />
              <Textarea
                id="cancel-reason"
                label="Reason for Cancellation"
                placeholder="Please state why you are cancelling..."
                value={cancelReason}
                onChange={(e) => setCancelReason(e.target.value)}
                required
                disabled={isLoading}
              />
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 12 }}>
                <Button type="button" variant="ghost" size="sm" onClick={() => setIsCancelling(false)}>
                  Back
                </Button>
                <Button type="submit" variant="danger" size="sm" isLoading={isLoading} loadingText="Cancelling...">
                  Confirm & Invalidate Passes
                </Button>
              </div>
            </form>
          )}

          <div style={{ marginTop: 20, display: 'flex', justifyContent: 'flex-end' }}>
            <Button type="button" variant="secondary" onClick={() => setLookupResult(null)}>
              Check Another Code
            </Button>
          </div>
        </div>
      )}
    </Dialog>
  );
};
