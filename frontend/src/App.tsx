import { useState, useEffect, useCallback, type FC } from 'react';
import type {
  PublicEventDetails,
  PublicRegistrationResponse,
  EventRegistrationSettingsResponse,
  StaffParticipantRosterItemResponse,
  AttendanceSummaryResponse,
  CurrentUserResponse,
  OrganizationResponse,
  OrganizationDetailResponse,
  InvitationResponse,
  InvitationAcceptResponse,
} from './api/types';
import { getPublicEventDetails } from './api/publicRegistration';
import {
  getRegistrationSettings,
  listParticipants,
  getAttendanceSummary,
} from './api/staffOperations';
import {
  getCurrentUser,
  listOrganizations,
  getOrganizationDetails,
  revokeInvitation,
} from './api/organizations';
import { ApiError } from './api/client';

import { Navbar, type AppMode } from './components/layout/Navbar';
import { Footer } from './components/layout/Footer';
import { EventOverview } from './components/public/EventOverview';
import { IndividualRegForm } from './components/public/IndividualRegForm';
import { TeamRegForm } from './components/public/TeamRegForm';
import { RegistrationConfirmation } from './components/public/RegistrationConfirmation';
import { RegistrationLookupModal } from './components/public/RegistrationLookupModal';

import { Tabs, type TabItem } from './components/common/Tabs';
import { CheckInDesk } from './components/staff/CheckInDesk';
import { ParticipantRoster } from './components/staff/ParticipantRoster';
import { AttendanceSummaryCard } from './components/staff/AttendanceSummaryCard';
import { RegistrationSettingsCard } from './components/staff/RegistrationSettingsCard';
import { AuthUnavailableNotice } from './components/staff/AuthUnavailableNotice';
import { CheckInCorrectionModal } from './components/staff/CheckInCorrectionModal';
import { ParticipantDetailModal } from './components/staff/ParticipantDetailModal';
import { WorkspaceOverview } from './components/org/WorkspaceOverview';
import { InvitationAcceptView } from './components/org/InvitationAcceptView';

import { Alert } from './components/common/Alert';
import { Badge } from './components/common/Badge';
import { CardSkeleton } from './components/common/Skeleton';
import { ToastProvider, useToast } from './components/common/Toast';
import { IconSearch } from './components/common/Icons';

/**
 * Extracts single-use invitation tokens according to secure fragment routing.
 * - Extracts fragment tokens (#token=... or #invite_token=...) into ephemeral state
 *   and immediately scrubs the fragment via history.replaceState before any network call.
 * - Detects legacy query parameters (?token=... or ?invite_token=...), scrubs them from URL,
 *   and flags legacyQueryRejected=true so the UI alerts the user and falls back to manual entry.
 * - Tokens are NEVER written to localStorage, sessionStorage, or cookies.
 */
export function parseInitialInvitationState(): {
  initialToken: string;
  legacyQueryRejected: boolean;
  initialMode: AppMode;
} {
  let initialToken = '';
  let legacyQueryRejected = false;
  let initialMode: AppMode = 'public';

  if (typeof window === 'undefined') {
    return { initialToken, legacyQueryRejected, initialMode };
  }

  // 1. Check URL fragment (#token=... or #invite_token=...)
  const hash = window.location.hash;
  if (hash && hash.length > 1) {
    const rawFragment = hash.startsWith('#') ? hash.slice(1) : hash;
    const fragmentParams = new URLSearchParams(rawFragment);
    const token = fragmentParams.get('token') || fragmentParams.get('invite_token');
    if (token) {
      initialToken = token;
      initialMode = 'accept-invite';
    }
    // Immediately scrub fragment from address bar and history
    window.history.replaceState(
      null,
      '',
      window.location.pathname + window.location.search,
    );
  }

  // 2. Check URL query parameters (?token=... or ?invite_token=...)
  const searchParams = new URLSearchParams(window.location.search);
  if (searchParams.has('token') || searchParams.has('invite_token')) {
    legacyQueryRejected = true;
    initialMode = 'accept-invite';
    // Reject legacy query parameter and scrub immediately from URL
    searchParams.delete('token');
    searchParams.delete('invite_token');
    const newSearch = searchParams.toString() ? `?${searchParams.toString()}` : '';
    window.history.replaceState(
      null,
      '',
      window.location.pathname + newSearch,
    );
  }

  if (initialMode === 'public') {
    if (searchParams.get('mode') === 'workspace') {
      initialMode = 'workspace';
    } else if (searchParams.get('mode') === 'staff') {
      initialMode = 'staff';
    }
  }

  return { initialToken, legacyQueryRejected, initialMode };
}

export const AppContent: FC = () => {
  const { showToast } = useToast();

  const [initialInvState] = useState(() => parseInitialInvitationState());
  const [mode, setMode] = useState<AppMode>(initialInvState.initialMode);
  const [inviteTokenParam] = useState<string>(initialInvState.initialToken);
  const [legacyQueryRejected] = useState<boolean>(initialInvState.legacyQueryRejected);

  // Public State
  const [registrationKey, setRegistrationKey] = useState<string>(() => {
    if (typeof window !== 'undefined') {
      const params = new URLSearchParams(window.location.search);
      return params.get('key') || 'reg_demo_key';
    }
    return 'reg_demo_key';
  });
  const [publicEvent, setPublicEvent] = useState<PublicEventDetails | null>(null);
  const [isPublicLoading, setIsPublicLoading] = useState(false);
  const [publicError, setPublicError] = useState<string | null>(null);
  const [selectedFormat, setSelectedFormat] = useState<'solo' | 'team'>('solo');
  const [confirmedRegistration, setConfirmedRegistration] = useState<PublicRegistrationResponse | null>(null);
  const [isLookupOpen, setIsLookupOpen] = useState(false);

  // Shared Auth & Session State
  const [staffAuthToken, setStaffAuthToken] = useState<string>('');

  // Workspace & Organization State (Phase 1)
  const [currentUser, setCurrentUser] = useState<CurrentUserResponse | null>(null);
  const [organizations, setOrganizations] = useState<OrganizationResponse[]>([]);
  const [activeOrgId, setActiveOrgId] = useState<string | null>(null);
  const [activeOrg, setActiveOrg] = useState<OrganizationDetailResponse | null>(null);
  const [invitations, setInvitations] = useState<InvitationResponse[]>([]);
  const [isWorkspaceLoading, setIsWorkspaceLoading] = useState(false);
  const [workspaceError, setWorkspaceError] = useState<string | null>(null);
  const [isWorkspaceAuthUnavailable, setIsWorkspaceAuthUnavailable] = useState(false);

  // Staff State
  const [staffOrgId] = useState('demo-org-id');
  const [staffEventId] = useState('demo-event-id');
  const [staffActiveTab, setStaffActiveTab] = useState('desk');
  const [isAuthUnavailable, setIsAuthUnavailable] = useState(false);

  // Staff Data
  const [settings, setSettings] = useState<EventRegistrationSettingsResponse | null>(null);
  const [roster, setRoster] = useState<StaffParticipantRosterItemResponse[]>([]);
  const [isRosterLoading, setIsRosterLoading] = useState(false);
  const [rosterError, setRosterError] = useState<string | null>(null);
  const [rosterSearch, setRosterSearch] = useState('');
  const [rosterStatusFilter, setRosterStatusFilter] = useState('');

  const [summary, setSummary] = useState<AttendanceSummaryResponse | null>(null);
  const [isSummaryLoading, setIsSummaryLoading] = useState(false);

  // Staff Modals
  const [voidParticipant, setVoidParticipant] = useState<StaffParticipantRosterItemResponse | null>(null);
  const [reissueParticipant, setReissueParticipant] = useState<StaffParticipantRosterItemResponse | null>(null);

  // Load workspace data
  const loadWorkspaceData = useCallback(async () => {
    setIsWorkspaceLoading(true);
    setWorkspaceError(null);
    setIsWorkspaceAuthUnavailable(false);

    try {
      const user = await getCurrentUser({ authToken: staffAuthToken });
      setCurrentUser(user);

      const orgs = await listOrganizations({ authToken: staffAuthToken });
      setOrganizations(orgs);

      const targetOrgId = activeOrgId && orgs.some((o) => o.id === activeOrgId)
        ? activeOrgId
        : orgs.length > 0
        ? orgs[0].id
        : null;

      if (targetOrgId) {
        setActiveOrgId(targetOrgId);
        const details = await getOrganizationDetails(targetOrgId, { authToken: staffAuthToken });
        setActiveOrg(details);
      } else {
        setActiveOrg(null);
      }
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setIsWorkspaceAuthUnavailable(true);
      } else if (err instanceof ApiError) {
        setWorkspaceError(err.detail);
      } else {
        setWorkspaceError('Failed to load workspace data. Please verify your connection.');
      }
    } finally {
      setIsWorkspaceLoading(false);
    }
  }, [staffAuthToken, activeOrgId]);

  useEffect(() => {
    if (mode === 'workspace') {
      loadWorkspaceData();
    }
  }, [mode, loadWorkspaceData]);

  const handleSelectOrg = useCallback(async (orgId: string) => {
    setActiveOrgId(orgId);
    setIsWorkspaceLoading(true);
    try {
      const details = await getOrganizationDetails(orgId, { authToken: staffAuthToken });
      setActiveOrg(details);
    } catch (err) {
      if (err instanceof ApiError) {
        setWorkspaceError(err.detail);
      }
    } finally {
      setIsWorkspaceLoading(false);
    }
  }, [staffAuthToken]);

  const handleCreateOrg = useCallback(async (newOrg: OrganizationResponse) => {
    setOrganizations((prev) => [newOrg, ...prev]);
    setActiveOrgId(newOrg.id);
    showToast('success', 'Workspace Created', `Workspace "${newOrg.club_name}" established.`);
    try {
      const details = await getOrganizationDetails(newOrg.id, { authToken: staffAuthToken });
      setActiveOrg(details);
    } catch {
      // Retain basic response if details fetch fails
    }
  }, [showToast, staffAuthToken]);

  const handleUpdateOrg = useCallback((updatedOrg: OrganizationDetailResponse) => {
    setActiveOrg(updatedOrg);
    setOrganizations((prev) =>
      prev.map((o) => (o.id === updatedOrg.id ? { ...o, verification_status: updatedOrg.verification_status } : o)),
    );
    showToast(
      'success',
      'Verification Updated',
      `Workspace is now ${updatedOrg.verification_status === 'verified' ? 'Verified' : 'Rejected'}.`,
    );
  }, [showToast]);

  const handleAddInvitation = useCallback((invitation: InvitationResponse) => {
    setInvitations((prev) => [invitation, ...prev]);
    showToast('success', 'Invitation Dispatched', `Invitation sent to ${invitation.email}.`);
  }, [showToast]);

  const handleRevokeInvitation = useCallback(async (invitationId: string) => {
    if (!activeOrgId) return;
    try {
      const revoked = await revokeInvitation(activeOrgId, invitationId, { authToken: staffAuthToken });
      setInvitations((prev) =>
        prev.map((i) => (i.id === invitationId ? { ...i, status: 'revoked' } : i)),
      );
      showToast('info', 'Invitation Revoked', `Invitation for ${revoked.email} has been revoked.`);
    } catch (err) {
      if (err instanceof ApiError) {
        showToast('error', 'Revocation Failed', err.detail);
      } else {
        showToast('error', 'Revocation Failed', 'Failed to revoke invitation.');
      }
    }
  }, [activeOrgId, staffAuthToken, showToast]);

  const handleAcceptSuccess = useCallback((resp: InvitationAcceptResponse) => {
    showToast('success', 'Welcome to the Team', `Joined organization with ${resp.role_name} role.`);
    setMode('workspace');
    loadWorkspaceData();
  }, [showToast, loadWorkspaceData]);

  // Load public event details
  const loadPublicEvent = useCallback(async (key: string) => {
    if (!key.trim()) return;
    setIsPublicLoading(true);
    setPublicError(null);
    try {
      const details = await getPublicEventDetails(key.trim());
      setPublicEvent(details);
      // Synchronize format selector
      if (details.registration_format === 'team') {
        setSelectedFormat('team');
      } else {
        setSelectedFormat('solo');
      }
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        setPublicError('Event not found or invalid registration key. Please check the link provided by event organizers.');
      } else if (err instanceof ApiError) {
        setPublicError(err.detail);
      } else {
        setPublicError('Failed to load event details. Please verify your connection.');
      }
      setPublicEvent(null);
    } finally {
      setIsPublicLoading(false);
    }
  }, []);

  useEffect(() => {
    if (mode === 'public' && registrationKey) {
      loadPublicEvent(registrationKey);
    }
  }, [mode, registrationKey, loadPublicEvent]);

  // Load staff data
  const loadStaffData = useCallback(async () => {
    if (!staffOrgId || !staffEventId) return;
    setIsAuthUnavailable(false);
    setRosterError(null);

    // Load Settings
    try {
      const s = await getRegistrationSettings(staffOrgId, staffEventId, { authToken: staffAuthToken });
      setSettings(s);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setIsAuthUnavailable(true);
        return;
      }
    }

    // Load Summary
    setIsSummaryLoading(true);
    try {
      const sum = await getAttendanceSummary(staffOrgId, staffEventId, { authToken: staffAuthToken });
      setSummary(sum);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setIsAuthUnavailable(true);
      }
    } finally {
      setIsSummaryLoading(false);
    }

    // Load Roster
    setIsRosterLoading(true);
    try {
      const items = await listParticipants(
        staffOrgId,
        staffEventId,
        {
          search: rosterSearch.trim() || undefined,
          status: rosterStatusFilter.trim() || undefined,
          limit: 100,
        },
        { authToken: staffAuthToken },
      );
      setRoster(items);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setIsAuthUnavailable(true);
      } else if (err instanceof ApiError) {
        setRosterError(err.detail);
      }
    } finally {
      setIsRosterLoading(false);
    }
  }, [staffOrgId, staffEventId, staffAuthToken, rosterSearch, rosterStatusFilter]);

  useEffect(() => {
    if (mode === 'staff') {
      loadStaffData();
    }
  }, [mode, loadStaffData]);

  const staffTabs: TabItem[] = [
    { id: 'desk', label: 'Check-In Desk' },
    { id: 'roster', label: 'Attendee Roster', badge: roster.length },
    { id: 'summary', label: 'Attendance KPIs' },
    { id: 'settings', label: 'Registration Settings' },
  ];

  return (
    <div className="co-app-layout">
      <Navbar
        currentMode={mode}
        onModeChange={(newMode) => {
          setMode(newMode);
          setConfirmedRegistration(null);
        }}
        eventKey={registrationKey}
        onEventKeyChange={setRegistrationKey}
        onRefreshEvent={() => loadPublicEvent(registrationKey)}
      />

      <main className="co-main-content">
        {mode === 'public' ? (
          <div>
            {isPublicLoading && !publicEvent && (
              <div>
                <CardSkeleton lines={4} />
              </div>
            )}

            {publicError && (
              <div>
                <Alert variant="danger" title="Registration Portal Notice">
                  {publicError}
                </Alert>
                <div style={{ textAlign: 'center', marginTop: 24 }}>
                  <button
                    type="button"
                    className="co-btn co-btn-secondary"
                    onClick={() => setIsLookupOpen(true)}
                    style={{ display: 'inline-flex', alignItems: 'center', gap: 6, maxWidth: '100%', whiteSpace: 'normal', textAlign: 'center' }}
                  >
                    <IconSearch size={16} />
                    <span>Look Up Registration by Confirmation Code</span>
                  </button>
                </div>
              </div>
            )}

            {publicEvent && !confirmedRegistration && (
              <div>
                <EventOverview
                  event={publicEvent}
                  onOpenLookup={() => setIsLookupOpen(true)}
                />

                {/* Format selection if event supports both */}
                {publicEvent.registration_format === 'both' && (
                  <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 24 }}>
                    <div
                      style={{
                        display: 'inline-flex',
                        background: 'var(--co-bg-surface)',
                        border: '1px solid var(--co-border-subtle)',
                        padding: 4,
                        borderRadius: 'var(--co-radius-md)',
                        boxShadow: 'var(--co-shadow-xs)',
                      }}
                    >
                      <button
                        type="button"
                        className={`co-btn co-btn-sm ${selectedFormat === 'solo' ? 'co-btn-primary' : 'co-btn-ghost'}`}
                        onClick={() => setSelectedFormat('solo')}
                        aria-pressed={selectedFormat === 'solo'}
                      >
                        Individual Registration
                      </button>
                      <button
                        type="button"
                        className={`co-btn co-btn-sm ${selectedFormat === 'team' ? 'co-btn-primary' : 'co-btn-ghost'}`}
                        onClick={() => setSelectedFormat('team')}
                        aria-pressed={selectedFormat === 'team'}
                      >
                        Team Registration ({publicEvent.team_size_min}–{publicEvent.team_size_max} Members)
                      </button>
                    </div>
                  </div>
                )}

                {/* Active Form */}
                {selectedFormat === 'solo' && publicEvent.registration_format !== 'team' && (
                  <IndividualRegForm
                    event={publicEvent}
                    onSuccess={(resp) => setConfirmedRegistration(resp)}
                  />
                )}

                {selectedFormat === 'team' && publicEvent.registration_format !== 'solo' && (
                  <TeamRegForm
                    event={publicEvent}
                    onSuccess={(resp) => setConfirmedRegistration(resp)}
                  />
                )}
              </div>
            )}

            {/* Confirmed Passes Display */}
            {confirmedRegistration && publicEvent && (
              <RegistrationConfirmation
                registration={confirmedRegistration}
                event={publicEvent}
                onReset={() => setConfirmedRegistration(null)}
              />
            )}

            {/* Lookup Modal */}
            <RegistrationLookupModal
              isOpen={isLookupOpen}
              onClose={() => setIsLookupOpen(false)}
              registrationKey={registrationKey}
            />
          </div>
        ) : mode === 'workspace' ? (
          /* Workspace & Organization Hub (Phase 1) */
          <div>
            {/* Developer Test Token Input (keeps production fail-closed without hardcoding fake tokens) */}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                flexWrap: 'wrap',
                gap: 12,
                padding: '12px 18px',
                backgroundColor: 'var(--co-bg-surface)',
                border: '1px solid var(--co-border-subtle)',
                borderRadius: 'var(--co-radius-lg)',
                marginBottom: 24,
                boxShadow: 'var(--co-shadow-xs)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 16, flexWrap: 'wrap' }}>
                <div style={{ fontSize: '0.85rem' }}>
                  <span style={{ color: 'var(--co-text-muted)' }}>Workspace: </span>
                  <strong style={{ fontFamily: 'var(--co-font-mono)' }}>
                    {activeOrg?.club_name || activeOrgId || 'None'}
                  </strong>
                </div>
                {currentUser && (
                  <div style={{ fontSize: '0.85rem' }}>
                    <span style={{ color: 'var(--co-text-muted)' }}>Signed In As: </span>
                    <strong>{currentUser.display_name}</strong> ({currentUser.email})
                    {currentUser.is_platform_admin && (
                      <span style={{ marginLeft: 6 }}>
                        <Badge variant="primary">Platform Admin</Badge>
                      </span>
                    )}
                  </div>
                )}
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <label htmlFor="workspace-test-token" style={{ fontSize: '0.75rem', color: 'var(--co-text-muted)', fontWeight: 500 }}>
                  Session/Test Token:
                </label>
                <input
                  id="workspace-test-token"
                  type="password"
                  className="co-input"
                  style={{ width: 140, padding: '3px 8px', fontSize: '0.75rem', fontFamily: 'var(--co-font-mono)' }}
                  placeholder="Bearer token..."
                  value={staffAuthToken}
                  onChange={(e) => setStaffAuthToken(e.target.value)}
                  onBlur={() => loadWorkspaceData()}
                />
              </div>
            </div>

            {isWorkspaceAuthUnavailable ? (
              <AuthUnavailableNotice />
            ) : (
              <WorkspaceOverview
                currentUser={currentUser}
                organizations={organizations}
                activeOrg={activeOrg}
                activeOrgId={activeOrgId}
                onSelectOrg={handleSelectOrg}
                onRefreshOrg={loadWorkspaceData}
                onCreateOrg={handleCreateOrg}
                onUpdateOrg={handleUpdateOrg}
                invitations={invitations}
                onAddInvitation={handleAddInvitation}
                onRevokeInvitation={handleRevokeInvitation}
                isLoading={isWorkspaceLoading}
                error={workspaceError}
                authToken={staffAuthToken}
              />
            )}
          </div>
        ) : mode === 'accept-invite' ? (
          /* Public / Authorized Invitation Acceptance View */
          <div>
            <InvitationAcceptView
              initialToken={inviteTokenParam}
              legacyQueryRejected={legacyQueryRejected}
              onAcceptSuccess={handleAcceptSuccess}
              authToken={staffAuthToken}
            />
          </div>
        ) : (
          /* Staff Operations Hub */
          <div>
            {/* Context Switcher / Dev Bar */}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                flexWrap: 'wrap',
                gap: 12,
                padding: '12px 18px',
                backgroundColor: 'var(--co-bg-surface)',
                border: '1px solid var(--co-border-subtle)',
                borderRadius: 'var(--co-radius-lg)',
                marginBottom: 24,
                boxShadow: 'var(--co-shadow-xs)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 16, flexWrap: 'wrap' }}>
                <div style={{ fontSize: '0.85rem' }}>
                  <span style={{ color: 'var(--co-text-muted)' }}>Workspace: </span>
                  <strong style={{ fontFamily: 'var(--co-font-mono)' }}>{staffOrgId}</strong>
                </div>
                <div style={{ fontSize: '0.85rem' }}>
                  <span style={{ color: 'var(--co-text-muted)' }}>Event ID: </span>
                  <strong style={{ fontFamily: 'var(--co-font-mono)' }}>{staffEventId}</strong>
                </div>
              </div>

              {/* Developer Test Token Input (keeps production fail-closed without hardcoding fake tokens) */}
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <label htmlFor="staff-test-token" style={{ fontSize: '0.75rem', color: 'var(--co-text-muted)', fontWeight: 500 }}>
                  Session/Test Token:
                </label>
                <input
                  id="staff-test-token"
                  type="password"
                  className="co-input"
                  style={{ width: 140, padding: '3px 8px', fontSize: '0.75rem', fontFamily: 'var(--co-font-mono)' }}
                  placeholder="Bearer token..."
                  value={staffAuthToken}
                  onChange={(e) => setStaffAuthToken(e.target.value)}
                  onBlur={() => loadStaffData()}
                />
              </div>
            </div>

            {isAuthUnavailable ? (
              <AuthUnavailableNotice />
            ) : (
              <div>
                <Tabs
                  tabs={staffTabs}
                  activeTab={staffActiveTab}
                  onChange={setStaffActiveTab}
                />

                {staffActiveTab === 'desk' && (
                  <CheckInDesk
                    orgId={staffOrgId}
                    eventId={staffEventId}
                    authToken={staffAuthToken}
                    onCheckInSuccess={loadStaffData}
                  />
                )}

                {staffActiveTab === 'roster' && (
                  <ParticipantRoster
                    orgId={staffOrgId}
                    eventId={staffEventId}
                    roster={roster}
                    isLoading={isRosterLoading}
                    error={rosterError}
                    authToken={staffAuthToken}
                    searchTerm={rosterSearch}
                    onSearchChange={setRosterSearch}
                    statusFilter={rosterStatusFilter}
                    onStatusFilterChange={setRosterStatusFilter}
                    onRefresh={loadStaffData}
                    onOpenVoidModal={(p) => setVoidParticipant(p)}
                    onOpenReissueModal={(p) => setReissueParticipant(p)}
                  />
                )}

                {staffActiveTab === 'summary' && (
                  <AttendanceSummaryCard
                    summary={summary}
                    isLoading={isSummaryLoading}
                    onRefresh={loadStaffData}
                  />
                )}

                {staffActiveTab === 'settings' && (
                  <RegistrationSettingsCard
                    orgId={staffOrgId}
                    eventId={staffEventId}
                    settings={settings}
                    authToken={staffAuthToken}
                    onUpdateSuccess={(upd) => setSettings(upd)}
                  />
                )}

                {/* Staff Action Modals */}
                <CheckInCorrectionModal
                  isOpen={Boolean(voidParticipant)}
                  onClose={() => setVoidParticipant(null)}
                  orgId={staffOrgId}
                  eventId={staffEventId}
                  participant={voidParticipant}
                  authToken={staffAuthToken}
                  onSuccess={loadStaffData}
                />

                <ParticipantDetailModal
                  isOpen={Boolean(reissueParticipant)}
                  onClose={() => setReissueParticipant(null)}
                  orgId={staffOrgId}
                  eventId={staffEventId}
                  eventName={publicEvent?.event_name || 'Event Operations'}
                  participant={reissueParticipant}
                  authToken={staffAuthToken}
                  onReissueSuccess={loadStaffData}
                />
              </div>
            )}
          </div>
        )}
      </main>

      <Footer />
    </div>
  );
};

export const App: FC = () => {
  return (
    <ToastProvider>
      <AppContent />
    </ToastProvider>
  );
};

export default App;
