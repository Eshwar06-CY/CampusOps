import { useState, type FC, type FormEvent } from 'react';
import type { StaffParticipantRosterItemResponse, IssuedPass } from '../../api/types';
import { reissueParticipantPass } from '../../api/staffOperations';
import { ApiError } from '../../api/client';
import { Dialog } from '../common/Dialog';
import { TextInput } from '../common/Input';
import { Button } from '../common/Button';
import { Alert } from '../common/Alert';
import { PublicPassDisplay } from '../public/PublicPassDisplay';
import { IconTicket } from '../common/Icons';
import { useToast } from '../common/Toast';

interface ParticipantDetailModalProps {
  isOpen: boolean;
  onClose: () => void;
  orgId: string;
  eventId: string;
  eventName: string;
  participant: StaffParticipantRosterItemResponse | null;
  authToken?: string | null;
  onReissueSuccess: () => void;
}

export const ParticipantDetailModal: FC<ParticipantDetailModalProps> = ({
  isOpen,
  onClose,
  orgId,
  eventId,
  eventName,
  participant,
  authToken,
  onReissueSuccess,
}) => {
  const [reason, setReason] = useState('');
  const [isReissuing, setIsReissuing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [newPass, setNewPass] = useState<IssuedPass | null>(null);
  const { showToast } = useToast();

  if (!participant) return null;

  const handleReissue = async (e: FormEvent) => {
    e.preventDefault();
    if (!reason.trim()) {
      setError('Please provide a reason for pass reissuance.');
      return;
    }

    setError(null);
    setIsReissuing(true);
    try {
      const issued = await reissueParticipantPass(orgId, eventId, participant.participant_id, reason.trim(), {
        authToken,
      });
      setNewPass(issued);
      showToast('success', 'Pass Reissued', `Fresh admission pass generated for ${participant.full_name}.`);
      onReissueSuccess();
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.detail);
      } else {
        setError('Failed to reissue admission pass.');
      }
    } finally {
      setIsReissuing(false);
    }
  };

  const handleModalClose = () => {
    setReason('');
    setError(null);
    setNewPass(null);
    onClose();
  };

  return (
    <Dialog
      isOpen={isOpen}
      onClose={handleModalClose}
      title="Attendee Pass Management"
      description={`Manage admission pass credentials for ${participant.full_name}.`}
    >
      {error && (
        <Alert variant="danger" title="Error">
          {error}
        </Alert>
      )}

      {newPass ? (
        <div>
          <Alert variant="success" title="New Admission Pass Issued">
            Prior tickets for this attendee were atomically revoked. The fresh admission pass below is now active.
          </Alert>
          <PublicPassDisplay
            pass={newPass}
            eventName={eventName}
            isTeam={Boolean(participant.team_name)}
            teamName={participant.team_name}
          />
          <div style={{ marginTop: 16, textAlign: 'right' }}>
            <Button variant="primary" onClick={handleModalClose}>
              Done
            </Button>
          </div>
        </div>
      ) : (
        <div>
          <div
            style={{
              padding: 16,
              backgroundColor: 'var(--co-bg-subtle)',
              borderRadius: 'var(--co-radius-lg)',
              border: '1px solid var(--co-border-subtle)',
              marginBottom: 16,
              fontSize: '0.875rem',
            }}
          >
            <div><strong>Attendee:</strong> {participant.full_name}</div>
            <div><strong>Email (Masked):</strong> {participant.email}</div>
            {participant.phone_number && <div><strong>Phone (Masked):</strong> {participant.phone_number}</div>}
            {participant.team_name && <div><strong>Team:</strong> {participant.team_name} ({participant.role_in_team})</div>}
            <div><strong>Current Ticket Ref:</strong> {participant.ticket_reference || 'None'}</div>
            <div><strong>Ticket Status:</strong> {participant.ticket_status || 'No active ticket'}</div>
            <div><strong>Attendance:</strong> {participant.attendance_status}</div>
          </div>

          <form onSubmit={handleReissue}>
            <Alert variant="info" title="Pass Reissuance Invariant">
              Reissuing a pass revokes any existing active or used tickets for this participant and issues a new cryptographically secure token.
            </Alert>

            <TextInput
              id="reissue-reason"
              label="Manager Reissuance Reason"
              placeholder="e.g. Phone battery died, lost ticket receipt at registration desk..."
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              required
              disabled={isReissuing}
            />

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 16 }}>
              <Button type="button" variant="ghost" onClick={handleModalClose} disabled={isReissuing}>
                Cancel
              </Button>
              <Button
                type="submit"
                variant="primary"
                isLoading={isReissuing}
                loadingText="Reissuing..."
                disabled={isReissuing || !reason.trim()}
                leftIcon={<IconTicket size={16} />}
              >
                Reissue Fresh Admission Pass
              </Button>
            </div>
          </form>
        </div>
      )}
    </Dialog>
  );
};
