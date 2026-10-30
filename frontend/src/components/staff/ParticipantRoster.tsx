import { useState, type FC } from 'react';
import type { StaffParticipantRosterItemResponse } from '../../api/types';
import { performCheckIn, getRosterExportUrl } from '../../api/staffOperations';
import { ApiError } from '../../api/client';
import { generateIdempotencyKey } from '../../utils/idempotency';
import { Card, CardHeader, CardBody } from '../common/Card';
import { Button } from '../common/Button';
import { Badge } from '../common/Badge';
import { Alert } from '../common/Alert';
import { TableSkeleton } from '../common/Skeleton';
import { formatDateTime } from '../../utils/formatters';
import { IconDownload, IconRefresh, IconSearch, IconCheckCircle, IconCrown } from '../common/Icons';
import { useToast } from '../common/Toast';

interface ParticipantRosterProps {
  orgId: string;
  eventId: string;
  roster: StaffParticipantRosterItemResponse[];
  isLoading: boolean;
  error: string | null;
  authToken?: string | null;
  searchTerm: string;
  onSearchChange: (value: string) => void;
  statusFilter: string;
  onStatusFilterChange: (value: string) => void;
  onRefresh: () => void;
  onOpenVoidModal: (participant: StaffParticipantRosterItemResponse) => void;
  onOpenReissueModal: (participant: StaffParticipantRosterItemResponse) => void;
}

export const ParticipantRoster: FC<ParticipantRosterProps> = ({
  orgId,
  eventId,
  roster,
  isLoading,
  error,
  authToken,
  searchTerm,
  onSearchChange,
  statusFilter,
  onStatusFilterChange,
  onRefresh,
  onOpenVoidModal,
  onOpenReissueModal,
}) => {
  const [actionError, setActionError] = useState<string | null>(null);
  const [checkingInId, setCheckingInId] = useState<string | null>(null);
  const { showToast } = useToast();

  const handleQuickCheckIn = async (participantId: string, participantName?: string) => {
    setActionError(null);
    setCheckingInId(participantId);
    try {
      await performCheckIn(
        orgId,
        eventId,
        {
          participant_id: participantId,
          method: 'manual_roster',
          station_id: 'DESK-ROSTER',
          idempotency_key: generateIdempotencyKey('chk_roster'),
        },
        { authToken },
      );
      showToast('success', 'Check-In Verified', `${participantName || 'Attendee'} checked in.`);
      onRefresh();
    } catch (err) {
      if (err instanceof ApiError) {
        setActionError(err.detail);
        showToast('error', 'Check-In Failed', err.detail);
      } else {
        setActionError('Check-in failed.');
      }
    } finally {
      setCheckingInId(null);
    }
  };

  const getAttendanceBadge = (status: string) => {
    switch (status) {
      case 'checked_in':
        return (
          <Badge variant="success" icon={<IconCheckCircle size={12} />}>
            Present
          </Badge>
        );
      case 'registered':
        return <Badge variant="primary">Registered</Badge>;
      case 'cancelled':
        return <Badge variant="neutral">Cancelled</Badge>;
      default:
        return <Badge variant="neutral">{status}</Badge>;
    }
  };

  const handleExportCsv = () => {
    const url = getRosterExportUrl(orgId, eventId);
    window.open(url, '_blank');
    showToast('info', 'Export Started', 'Attendee CSV roster download initialized.');
  };

  return (
    <Card>
      <CardHeader
        title="Event Attendee Roster"
        subtitle="Search and view registered participants with tiered contact privacy masking."
        action={
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <Button
              variant="secondary"
              size="sm"
              onClick={handleExportCsv}
              leftIcon={<IconDownload size={14} />}
              title="Download CSV roster"
            >
              Export CSV
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={onRefresh}
              isLoading={isLoading}
              leftIcon={<IconRefresh size={14} />}
            >
              Refresh Roster
            </Button>
          </div>
        }
      />
      <CardBody>
        {actionError && (
          <Alert variant="danger" title="Roster Action Notice">
            {actionError}
          </Alert>
        )}

        {error && (
          <Alert variant="danger" title="Roster Retrieval Error">
            {error}
          </Alert>
        )}

        {/* Filter controls */}
        <div style={{ display: 'flex', gap: 12, marginBottom: 16, flexWrap: 'wrap' }}>
          <div style={{ flex: 1, minWidth: 240, position: 'relative', display: 'flex', alignItems: 'center' }}>
            <span style={{ position: 'absolute', left: 12, color: 'var(--co-text-muted)', display: 'flex', alignItems: 'center' }}>
              <IconSearch size={16} />
            </span>
            <input
              type="text"
              className="co-input"
              style={{ paddingLeft: '2.5rem' }}
              placeholder="Search by name, student ID, or college..."
              value={searchTerm}
              onChange={(e) => onSearchChange(e.target.value)}
              aria-label="Filter attendee roster by name or ID"
            />
          </div>
          <div style={{ width: 180 }}>
            <select
              className="co-select"
              value={statusFilter}
              onChange={(e) => onStatusFilterChange(e.target.value)}
              aria-label="Filter by attendance status"
            >
              <option value="">All Statuses</option>
              <option value="registered">Registered</option>
              <option value="checked_in">Checked In</option>
              <option value="cancelled">Cancelled</option>
            </select>
          </div>
        </div>

        {/* Roster content */}
        {isLoading && roster.length === 0 ? (
          <TableSkeleton rows={5} columns={6} />
        ) : roster.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '48px 16px', color: 'var(--co-text-muted)' }}>
            <p style={{ margin: 0, fontSize: '1.05rem', fontWeight: 600, color: 'var(--co-text-main)' }}>
              No attendee records found.
            </p>
            <p style={{ margin: '6px 0 0 0', fontSize: '0.875rem' }}>
              {searchTerm || statusFilter ? 'Try clearing your search filters or status criteria.' : 'No participants registered for this event yet.'}
            </p>
          </div>
        ) : (
          <div className="co-table-container">
            <table className="co-table" aria-label="Attendee Roster Table">
              <thead>
                <tr>
                  <th scope="col">Attendee & Role</th>
                  <th scope="col">Team</th>
                  <th scope="col">Contact (Masked)</th>
                  <th scope="col">College / Student ID</th>
                  <th scope="col">Ticket Ref</th>
                  <th scope="col">Attendance Status</th>
                  <th scope="col" style={{ textAlign: 'right' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {roster.map((p) => (
                  <tr key={p.participant_id}>
                    <td>
                      <strong style={{ display: 'block', fontSize: '0.95rem' }}>{p.full_name}</strong>
                      {p.role_in_team && (
                        <span style={{ fontSize: '0.75rem', color: 'var(--co-text-muted)', display: 'inline-flex', alignItems: 'center', gap: 4, marginTop: 2 }}>
                          {p.role_in_team === 'leader' ? (
                            <>
                              <IconCrown size={12} style={{ color: 'var(--co-primary-600)' }} />
                              <span>Leader</span>
                            </>
                          ) : (
                            'Member'
                          )}
                        </span>
                      )}
                    </td>
                    <td>{p.team_name || '—'}</td>
                    <td>
                      <div style={{ fontFamily: 'var(--co-font-mono)', fontSize: '0.8rem' }}>{p.email}</div>
                      {p.phone_number && (
                        <div style={{ fontSize: '0.75rem', color: 'var(--co-text-muted)', fontFamily: 'var(--co-font-mono)' }}>
                          {p.phone_number}
                        </div>
                      )}
                    </td>
                    <td>
                      <div>{p.college_name || '—'}</div>
                      {p.student_id && (
                        <div style={{ fontSize: '0.75rem', color: 'var(--co-text-muted)', fontFamily: 'var(--co-font-mono)' }}>
                          ID: {p.student_id}
                        </div>
                      )}
                    </td>
                    <td>
                      <span style={{ fontFamily: 'var(--co-font-mono)', fontSize: '0.85rem', fontWeight: 600, color: 'var(--co-primary-600)' }}>
                        {p.ticket_reference || '—'}
                      </span>
                    </td>
                    <td>
                      <div>{getAttendanceBadge(p.attendance_status)}</div>
                      {p.checked_in_at && (
                        <div style={{ fontSize: '0.7rem', color: 'var(--co-text-muted)', marginTop: 2 }}>
                          {formatDateTime(p.checked_in_at)}
                        </div>
                      )}
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      <div style={{ display: 'inline-flex', gap: 6, justifyContent: 'flex-end', flexWrap: 'wrap' }}>
                        {p.attendance_status === 'registered' && (
                          <Button
                            variant="primary"
                            size="sm"
                            isLoading={checkingInId === p.participant_id}
                            onClick={() => handleQuickCheckIn(p.participant_id, p.full_name)}
                          >
                            Check In
                          </Button>
                        )}

                        {p.attendance_status === 'checked_in' && (
                          <Button
                            variant="danger"
                            size="sm"
                            onClick={() => onOpenVoidModal(p)}
                          >
                            Void Check-In
                          </Button>
                        )}

                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => onOpenReissueModal(p)}
                          title="Reissue admission pass"
                        >
                          Reissue Pass
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardBody>
    </Card>
  );
};
