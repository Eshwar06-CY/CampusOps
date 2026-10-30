import { useState, type FC, type FormEvent } from 'react';
import type { StaffParticipantRosterItemResponse } from '../../api/types';
import { voidCheckIn } from '../../api/staffOperations';
import { ApiError } from '../../api/client';
import { Dialog } from '../common/Dialog';
import { Textarea } from '../common/Input';
import { Button } from '../common/Button';
import { Alert } from '../common/Alert';
import { useToast } from '../common/Toast';

interface CheckInCorrectionModalProps {
  isOpen: boolean;
  onClose: () => void;
  orgId: string;
  eventId: string;
  participant: StaffParticipantRosterItemResponse | null;
  authToken?: string | null;
  onSuccess: () => void;
}

export const CheckInCorrectionModal: FC<CheckInCorrectionModalProps> = ({
  isOpen,
  onClose,
  orgId,
  eventId,
  participant,
  authToken,
  onSuccess,
}) => {
  const [reason, setReason] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { showToast } = useToast();

  if (!participant) return null;

  const minReasonLength = 10;
  const isReasonValid = reason.trim().length >= minReasonLength;

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!participant.check_in_id) {
      setError('No active check-in record associated with this attendee.');
      return;
    }

    if (!isReasonValid) {
      setError(`Correction explanation must be at least ${minReasonLength} characters.`);
      return;
    }

    setError(null);
    setIsSubmitting(true);
    try {
      await voidCheckIn(orgId, eventId, participant.check_in_id, reason.trim(), { authToken });
      showToast('success', 'Check-In Voided', `${participant.full_name}'s arrival status has been corrected.`);
      setReason('');
      onSuccess();
      onClose();
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 403) {
          setError('Permission Denied: Only Event Managers (Lead, Primary Admin, Office Bearer) may void check-ins.');
        } else {
          setError(err.detail);
        }
      } else {
        setError('Failed to void check-in.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog
      isOpen={isOpen}
      onClose={onClose}
      title="Manager Check-In Correction (Void)"
      description="Revert an accidental check-in record with an immutable audit entry."
    >
      {error && (
        <Alert variant="danger" title="Correction Rejection">
          {error}
        </Alert>
      )}

      <Alert variant="warning" title="Operational Impact">
        <ul style={{ margin: 0, paddingLeft: 18 }}>
          <li>Reverts <strong>{participant.full_name}</strong> to &ldquo;registered&rdquo; status.</li>
          <li>Restores their ticket admission pass to &ldquo;issued&rdquo;.</li>
          <li>Decrements the live event attendance counter by 1.</li>
          <li>Appends an immutable audit entry into the check-in corrections ledger.</li>
        </ul>
      </Alert>

      <form onSubmit={handleSubmit} style={{ marginTop: 16 }}>
        <Textarea
          id="void-reason"
          label="Mandatory Audit Reason"
          placeholder="State the operational reason for voiding this check-in (e.g. Accidental check-in of wrong attendee; verified not present at desk)..."
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          required
          rows={3}
          disabled={isSubmitting}
          showCount={true}
          minCount={minReasonLength}
          helpText="Minimum 10 characters required for database audit constraint."
        />

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 16 }}>
          <Button type="button" variant="ghost" onClick={onClose} disabled={isSubmitting}>
            Cancel
          </Button>
          <Button
            type="submit"
            variant="danger"
            isLoading={isSubmitting}
            loadingText="Voiding Check-In..."
            disabled={isSubmitting || !isReasonValid}
          >
            Confirm & Void Attendance
          </Button>
        </div>
      </form>
    </Dialog>
  );
};
