import { useState, useRef, useEffect, type FC, type FormEvent } from 'react';
import type { CheckInResponse, CheckInLookupItemResponse } from '../../api/types';
import { performCheckIn, lookupCheckInCandidates } from '../../api/staffOperations';
import { ApiError } from '../../api/client';
import { generateIdempotencyKey } from '../../utils/idempotency';
import { Card, CardHeader, CardBody } from '../common/Card';
import { TextInput } from '../common/Input';
import { Button } from '../common/Button';
import { Alert } from '../common/Alert';
import { Badge } from '../common/Badge';
import { IconQrCode, IconSearch, IconCheckCircle, IconAlertTriangle } from '../common/Icons';
import { useToast } from '../common/Toast';

interface CheckInDeskProps {
  orgId: string;
  eventId: string;
  authToken?: string | null;
  onCheckInSuccess: () => void;
}

export const CheckInDesk: FC<CheckInDeskProps> = ({
  orgId,
  eventId,
  authToken,
  onCheckInSuccess,
}) => {
  // Pass Code input
  const [passCodeInput, setPassCodeInput] = useState('');
  const [isCheckingIn, setIsCheckingIn] = useState(false);
  const [checkInResult, setCheckInResult] = useState<CheckInResponse | null>(null);
  const [deskError, setDeskError] = useState<string | null>(null);

  // Manual Candidate Search Lookup
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<CheckInLookupItemResponse[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState<number>(-1);

  const searchTimeoutRef = useRef<number | null>(null);
  const passCodeInputRef = useRef<HTMLInputElement>(null);
  const { showToast } = useToast();

  // Keyboard shortcut: Press '/' to focus passCodeInput
  useEffect(() => {
    const handleGlobalKeyDown = (e: KeyboardEvent) => {
      if (e.key === '/' && document.activeElement !== passCodeInputRef.current && !(document.activeElement instanceof HTMLInputElement || document.activeElement instanceof HTMLTextAreaElement)) {
        e.preventDefault();
        passCodeInputRef.current?.focus();
      }
    };
    window.addEventListener('keydown', handleGlobalKeyDown);
    return () => window.removeEventListener('keydown', handleGlobalKeyDown);
  }, []);

  const handlePassCodeSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const code = passCodeInput.trim();
    if (!code) return;

    setDeskError(null);
    setCheckInResult(null);
    setIsCheckingIn(true);

    const idempotencyKey = generateIdempotencyKey('chk');

    try {
      const response = await performCheckIn(
        orgId,
        eventId,
        {
          pass_code: code,
          method: 'manual_code',
          station_id: 'DESK-FRONT',
          idempotency_key: idempotencyKey,
        },
        { authToken },
      );
      setCheckInResult(response);
      setPassCodeInput('');

      if (response.status === 'verified') {
        showToast('success', 'Verified Check-In', `${response.participant_name} admitted successfully.`);
      } else if (response.status === 'already_checked_in') {
        showToast('info', 'Already Checked In', `${response.participant_name} is already present.`);
      }

      onCheckInSuccess();
    } catch (err) {
      if (err instanceof ApiError) {
        setDeskError(err.detail);
        showToast('error', 'Check-In Rejected', err.detail);
      } else {
        setDeskError('Check-in failed due to network connectivity.');
      }
    } finally {
      setIsCheckingIn(false);
      passCodeInputRef.current?.focus();
    }
  };

  const handleSearchChange = (value: string) => {
    setSearchQuery(value);
    setDeskError(null);
    setSelectedIndex(-1);

    if (searchTimeoutRef.current) {
      clearTimeout(searchTimeoutRef.current);
    }

    if (!value.trim()) {
      setSearchResults([]);
      return;
    }

    searchTimeoutRef.current = window.setTimeout(async () => {
      setIsSearching(true);
      try {
        const results = await lookupCheckInCandidates(orgId, eventId, value.trim(), { authToken });
        setSearchResults(results);
      } catch (err) {
        if (err instanceof ApiError && err.status === 404) {
          setSearchResults([]);
        } else if (err instanceof ApiError) {
          setDeskError(err.detail);
        }
      } finally {
        setIsSearching(false);
      }
    }, 250);
  };

  const handleParticipantCheckIn = async (participantId: string) => {
    setDeskError(null);
    setCheckInResult(null);
    setIsCheckingIn(true);

    const idempotencyKey = generateIdempotencyKey('chk_part');

    try {
      const response = await performCheckIn(
        orgId,
        eventId,
        {
          participant_id: participantId,
          method: 'manual_search',
          station_id: 'DESK-LOOKUP',
          idempotency_key: idempotencyKey,
        },
        { authToken },
      );
      setCheckInResult(response);
      setSearchQuery('');
      setSearchResults([]);

      if (response.status === 'verified') {
        showToast('success', 'Verified Check-In', `${response.participant_name} admitted.`);
      }

      onCheckInSuccess();
    } catch (err) {
      if (err instanceof ApiError) {
        setDeskError(err.detail);
      } else {
        setDeskError('Check-in failed.');
      }
    } finally {
      setIsCheckingIn(false);
    }
  };

  // Keyboard navigation for search results
  const handleSearchKeyDown = (e: React.KeyboardEvent) => {
    if (searchResults.length === 0) return;

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev < searchResults.length - 1 ? prev + 1 : 0));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev > 0 ? prev - 1 : searchResults.length - 1));
    } else if (e.key === 'Enter' && selectedIndex >= 0 && selectedIndex < searchResults.length) {
      e.preventDefault();
      const cand = searchResults[selectedIndex];
      if (cand.can_check_in) {
        handleParticipantCheckIn(cand.participant_id);
      }
    }
  };

  return (
    <div>
      <Card>
        <CardHeader
          title="Event Desk Arrival Station"
          subtitle="Process attendee arrivals via pass code or candidate search. Admission is strictly verified individually."
          action={
            <span
              style={{
                fontSize: '0.75rem',
                fontFamily: 'var(--co-font-mono)',
                color: 'var(--co-text-muted)',
                backgroundColor: 'var(--co-bg-subtle)',
                padding: '3px 8px',
                borderRadius: 'var(--co-radius-sm)',
                border: '1px solid var(--co-border-subtle)',
              }}
            >
              Tip: Press <kbd style={{ fontWeight: 700 }}>/</kbd> to focus scanner
            </span>
          }
        />
        <CardBody>
          {/* Status feedback */}
          {checkInResult && checkInResult.status === 'verified' && (
            <Alert variant="success" title="Check-In Verified">
              <div style={{ fontSize: '1.05rem', fontWeight: 600 }}>
                {checkInResult.participant_name}
                {checkInResult.team_name ? ` (${checkInResult.team_name})` : ''} checked in successfully.
              </div>
              <div style={{ fontSize: '0.85rem', marginTop: 4, color: 'var(--co-success-700)' }}>
                {checkInResult.message}
              </div>
            </Alert>
          )}

          {checkInResult && checkInResult.status === 'already_checked_in' && (
            <Alert variant="warning" title="Attendee Already Present">
              <div style={{ fontSize: '1.05rem', fontWeight: 600 }}>
                {checkInResult.participant_name} was already checked in.
              </div>
              <div style={{ fontSize: '0.85rem', marginTop: 4 }}>
                {checkInResult.message} No duplicate attendance recorded.
              </div>
            </Alert>
          )}

          {deskError && (
            <Alert variant="danger" title="Check-In Rejection">
              {deskError}
            </Alert>
          )}

          {/* Code Scan / Input */}
          <form onSubmit={handlePassCodeSubmit} style={{ marginBottom: 24 }}>
            <div style={{ display: 'flex', gap: 12, alignItems: 'flex-end', flexWrap: 'wrap' }}>
              <div style={{ flex: 1, minWidth: 280 }}>
                <TextInput
                  id="desk-pass-code"
                  ref={passCodeInputRef}
                  label="Scan or Enter Admission Pass Code"
                  placeholder="e.g. CO-PASS-8B1A2C3D... or Ticket Ref"
                  value={passCodeInput}
                  onChange={(e) => setPassCodeInput(e.target.value)}
                  disabled={isCheckingIn}
                  helpText="Supports 128-bit high-entropy pass code tokens or 8-char ticket references."
                  leftAddon={<IconQrCode size={18} />}
                  autoFocus
                />
              </div>
              <div style={{ marginBottom: 16 }}>
                <Button
                  type="submit"
                  variant="primary"
                  size="md"
                  isLoading={isCheckingIn}
                  loadingText="Verifying..."
                  disabled={isCheckingIn || !passCodeInput.trim()}
                  leftIcon={<IconCheckCircle size={16} />}
                >
                  Verify & Check In
                </Button>
              </div>
            </div>
          </form>

          {/* Quick Search Lookup */}
          <div style={{ borderTop: '1px solid var(--co-border-subtle)', paddingTop: 20 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
              <h4 style={{ margin: 0, fontSize: '1rem', fontWeight: 600 }}>
                Manual Attendee Search Lookup
              </h4>
              <span style={{ fontSize: '0.75rem', color: 'var(--co-text-muted)' }}>
                Use <kbd>↑</kbd> <kbd>↓</kbd> and <kbd>Enter</kbd> to select
              </span>
            </div>

            <TextInput
              id="desk-search-input"
              label="Search by Name, Student ID, or Reference"
              placeholder="e.g. Aarav, APEX-2026, or TKT-A1B2..."
              value={searchQuery}
              onChange={(e) => handleSearchChange(e.target.value)}
              onKeyDown={handleSearchKeyDown}
              disabled={isCheckingIn}
              leftAddon={<IconSearch size={16} />}
            />

            {isSearching && (
              <div style={{ padding: '8px 0', fontSize: '0.85rem', color: 'var(--co-text-muted)' }}>
                Searching attendee roster...
              </div>
            )}

            {searchResults.length > 0 && (
              <div
                style={{
                  border: '1px solid var(--co-border-subtle)',
                  borderRadius: 'var(--co-radius-lg)',
                  overflow: 'hidden',
                  marginTop: 8,
                  boxShadow: 'var(--co-shadow-sm)',
                }}
              >
                {searchResults.map((item, idx) => {
                  const isSelected = idx === selectedIndex;
                  return (
                    <div
                      key={item.participant_id}
                      style={{
                        padding: '12px 16px',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        borderBottom: '1px solid var(--co-border-subtle)',
                        backgroundColor: isSelected ? 'var(--co-primary-50)' : 'var(--co-bg-surface)',
                        transition: 'background-color var(--co-transition-fast)',
                      }}
                    >
                      <div>
                        <strong>{item.full_name}</strong>
                        {item.team_name && (
                          <span style={{ marginLeft: 8, fontSize: '0.85rem', color: 'var(--co-text-muted)' }}>
                            Team: {item.team_name}
                          </span>
                        )}
                        <div style={{ fontSize: '0.8rem', color: 'var(--co-text-muted)', marginTop: 2, fontFamily: 'var(--co-font-mono)' }}>
                          Ref: {item.ticket_reference || '—'} · ID: {item.student_id || '—'} · {item.email_masked}
                        </div>
                      </div>
                      <div>
                        {item.can_check_in ? (
                          <Button
                            type="button"
                            variant="primary"
                            size="sm"
                            onClick={() => handleParticipantCheckIn(item.participant_id)}
                            disabled={isCheckingIn}
                            leftIcon={<IconCheckCircle size={14} />}
                          >
                            Check In
                          </Button>
                        ) : (
                          <Badge
                            variant={item.attendance_status === 'checked_in' ? 'success' : 'neutral'}
                            icon={item.attendance_status === 'checked_in' ? <IconCheckCircle size={12} /> : undefined}
                          >
                            {item.attendance_status === 'checked_in' ? 'Present' : item.attendance_status}
                          </Badge>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}

            {searchQuery.trim().length > 0 && !isSearching && searchResults.length === 0 && (
              <p style={{ fontSize: '0.85rem', color: 'var(--co-text-muted)', margin: '8px 0 0 0' }}>
                No eligible candidates found matching &ldquo;{searchQuery}&rdquo;.
              </p>
            )}
          </div>

          <div
            style={{
              marginTop: 24,
              padding: 14,
              backgroundColor: 'var(--co-bg-subtle)',
              borderRadius: 'var(--co-radius-md)',
              fontSize: '0.8rem',
              color: 'var(--co-text-muted)',
              display: 'flex',
              alignItems: 'flex-start',
              gap: 8,
            }}
          >
            <span style={{ color: 'var(--co-primary-600)', marginTop: 2 }}>
              <IconAlertTriangle size={16} />
            </span>
            <div>
              <strong>Operational Note:</strong> Hardware barcode/QR scanners operating in HID keyboard wedge mode stream text directly into the pass code field and send an Enter key, triggering instant check-in.
            </div>
          </div>
        </CardBody>
      </Card>
    </div>
  );
};
