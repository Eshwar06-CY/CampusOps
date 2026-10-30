import { useState, type FC } from 'react';
import type {
  CurrentUserResponse,
  OrganizationResponse,
  OrganizationDetailResponse,
  InvitationResponse,
} from '../../api/types';
import { OrganizationSwitcher } from './OrganizationSwitcher';
import { VerificationBanner } from './VerificationBanner';
import { MemberDirectoryTable } from './MemberDirectoryTable';
import { CreateOrgModal } from './CreateOrgModal';
import { PlatformVerifyModal } from './PlatformVerifyModal';
import { InviteMemberModal } from './InviteMemberModal';
import { CardSkeleton } from '../common/Skeleton';
import { Alert } from '../common/Alert';
import { Badge } from '../common/Badge';
import { IconBuilding, IconCheckCircle, IconClock, IconUsers, IconCalendar } from '../common/Icons';
import { formatDateTime } from '../../utils/formatters';

interface WorkspaceOverviewProps {
  currentUser: CurrentUserResponse | null;
  organizations: OrganizationResponse[];
  activeOrg: OrganizationDetailResponse | null;
  activeOrgId: string | null;
  onSelectOrg: (id: string) => void;
  onRefreshOrg: () => Promise<void>;
  onCreateOrg: (newOrg: OrganizationResponse) => void;
  onUpdateOrg: (updatedOrg: OrganizationDetailResponse) => void;
  invitations: InvitationResponse[];
  onAddInvitation: (invitation: InvitationResponse) => void;
  onRevokeInvitation: (invitationId: string) => Promise<void>;
  isLoading: boolean;
  error: string | null;
  authToken?: string | null;
}

export const WorkspaceOverview: FC<WorkspaceOverviewProps> = ({
  currentUser,
  organizations,
  activeOrg,
  activeOrgId,
  onSelectOrg,
  onRefreshOrg,
  onCreateOrg,
  onUpdateOrg,
  invitations,
  onAddInvitation,
  onRevokeInvitation,
  isLoading,
  error,
  authToken,
}) => {
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isVerifyModalOpen, setIsVerifyModalOpen] = useState(false);
  const [isInviteModalOpen, setIsInviteModalOpen] = useState(false);

  // Authority & permission calculation
  const isPlatformAdmin = Boolean(currentUser?.is_platform_admin);
  const currentMembership = currentUser?.memberships.find((m) => m.organization_id === activeOrgId);
  const isPrimaryAdmin = Boolean(currentMembership?.roles.some((r) => r.role_name === 'PRIMARY_ADMIN'));
  const isOfficeBearer = Boolean(currentMembership?.roles.some((r) => r.role_name === 'OFFICE_BEARER'));
  const isVerified = activeOrg?.verification_status === 'verified';
  const canManageRoles = (isPrimaryAdmin || isOfficeBearer) && isVerified;

  if (isLoading && !activeOrg) {
    return (
      <div style={{ maxWidth: 1200, margin: '0 auto' }}>
        <CardSkeleton lines={5} />
      </div>
    );
  }

  if (error && !activeOrg) {
    return (
      <div style={{ maxWidth: 800, margin: '40px auto' }}>
        <Alert variant="danger" title="Workspace Data Unavailable">
          {error}
        </Alert>
        <div style={{ textAlign: 'center', marginTop: 20 }}>
          <button
            type="button"
            className="co-btn co-btn-secondary"
            onClick={onRefreshOrg}
          >
            Retry Loading Workspace
          </button>
        </div>
      </div>
    );
  }

  if (!activeOrg && organizations.length === 0) {
    return (
      <div className="co-card" style={{ maxWidth: 600, margin: '40px auto', textAlign: 'center', padding: 32 }}>
        <div
          style={{
            width: 56,
            height: 56,
            borderRadius: 'var(--co-radius-full)',
            background: 'var(--co-primary-50)',
            color: 'var(--co-primary-600)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            margin: '0 auto 16px',
          }}
        >
          <IconBuilding size={28} />
        </div>
        <h2 style={{ fontSize: 'var(--co-text-xl)', fontWeight: 700, margin: '0 0 8px' }}>
          No Workspaces Found
        </h2>
        <p style={{ color: 'var(--co-text-muted)', fontSize: '0.9rem', marginBottom: 24, lineHeight: 1.5 }}>
          You do not have an active membership in any organization workspace. Create a new collegiate workspace or accept an invitation to begin.
        </p>
        <button
          type="button"
          className="co-btn co-btn-primary"
          onClick={() => setIsCreateModalOpen(true)}
        >
          Create First Workspace
        </button>

        <CreateOrgModal
          isOpen={isCreateModalOpen}
          onClose={() => setIsCreateModalOpen(false)}
          onSuccess={onCreateOrg}
          authToken={authToken}
        />
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto' }}>
      {/* Workspace Header & Switcher */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          flexWrap: 'wrap',
          gap: 16,
          marginBottom: 24,
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
            <h1 style={{ fontSize: 'var(--co-text-2xl)', fontWeight: 700, margin: 0, letterSpacing: '-0.02em' }}>
              {activeOrg?.club_name || 'Organization Workspace'}
            </h1>
            {activeOrg && (
              <Badge
                variant={
                  activeOrg.verification_status === 'verified'
                    ? 'success'
                    : activeOrg.verification_status === 'rejected'
                    ? 'danger'
                    : 'warning'
                }
              >
                {activeOrg.verification_status === 'verified'
                  ? 'Verified'
                  : activeOrg.verification_status === 'rejected'
                  ? 'Rejected'
                  : 'Pending Verification'}
              </Badge>
            )}
          </div>
          <div style={{ fontSize: '0.9rem', color: 'var(--co-text-muted)', display: 'flex', alignItems: 'center', gap: 8 }}>
            <span>{activeOrg?.college_name}</span>
            <span>·</span>
            <span>Created {activeOrg ? formatDateTime(activeOrg.created_at) : 'recently'}</span>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <OrganizationSwitcher
            organizations={organizations}
            activeOrgId={activeOrgId}
            onSelectOrg={onSelectOrg}
            onCreateOrgClick={() => setIsCreateModalOpen(true)}
            isLoading={isLoading}
          />
        </div>
      </div>

      {/* Verification Status Banner */}
      {activeOrg && (
        <VerificationBanner
          organization={activeOrg}
          isPlatformAdmin={isPlatformAdmin}
          onOpenVerifyModal={() => setIsVerifyModalOpen(true)}
        />
      )}

      {/* Setup Progress Milestones */}
      <div className="co-card" style={{ marginBottom: 24 }}>
        <div className="co-card-header" style={{ padding: '16px 20px' }}>
          <h3 className="co-card-title" style={{ fontSize: '0.95rem' }}>
            Workspace Setup Milestones
          </h3>
        </div>
        <div
          style={{
            padding: '16px 20px',
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
            gap: 16,
          }}
        >
          {/* Milestone 1 */}
          <div
            style={{
              padding: 12,
              borderRadius: 'var(--co-radius-md)',
              background: 'var(--co-bg-subtle)',
              border: '1px solid var(--co-border-subtle)',
              display: 'flex',
              gap: 12,
              alignItems: 'flex-start',
            }}
          >
            <div style={{ color: 'var(--co-success-600)', marginTop: 2 }}>
              <IconCheckCircle size={20} />
            </div>
            <div>
              <strong style={{ display: 'block', fontSize: '0.85rem', color: 'var(--co-text-main)' }}>
                1. Workspace Created
              </strong>
              <span style={{ fontSize: '0.75rem', color: 'var(--co-text-muted)' }}>
                Primary Admin registered.
              </span>
            </div>
          </div>

          {/* Milestone 2 */}
          <div
            style={{
              padding: 12,
              borderRadius: 'var(--co-radius-md)',
              background: isVerified ? 'var(--co-bg-subtle)' : 'var(--co-warning-50)',
              border: `1px solid ${isVerified ? 'var(--co-border-subtle)' : 'var(--co-warning-200)'}`,
              display: 'flex',
              gap: 12,
              alignItems: 'flex-start',
            }}
          >
            <div style={{ color: isVerified ? 'var(--co-success-600)' : 'var(--co-warning-600)', marginTop: 2 }}>
              {isVerified ? <IconCheckCircle size={20} /> : <IconClock size={20} />}
            </div>
            <div>
              <strong style={{ display: 'block', fontSize: '0.85rem', color: 'var(--co-text-main)' }}>
                2. Institutional Verification
              </strong>
              <span style={{ fontSize: '0.75rem', color: 'var(--co-text-muted)' }}>
                {isVerified ? 'Approved by platform admin.' : 'Awaiting platform review.'}
              </span>
            </div>
          </div>

          {/* Milestone 3 */}
          <div
            style={{
              padding: 12,
              borderRadius: 'var(--co-radius-md)',
              background: 'var(--co-bg-subtle)',
              border: '1px solid var(--co-border-subtle)',
              display: 'flex',
              gap: 12,
              alignItems: 'flex-start',
              opacity: isVerified ? 1 : 0.6,
            }}
          >
            <div style={{ color: 'var(--co-primary-600)', marginTop: 2 }}>
              <IconUsers size={20} />
            </div>
            <div>
              <strong style={{ display: 'block', fontSize: '0.85rem', color: 'var(--co-text-main)' }}>
                3. Team Onboarding
              </strong>
              <span style={{ fontSize: '0.75rem', color: 'var(--co-text-muted)' }}>
                {isVerified ? `${invitations.length} invitation(s) issued.` : 'Gated behind verification.'}
              </span>
            </div>
          </div>

          {/* Milestone 4 */}
          <div
            style={{
              padding: 12,
              borderRadius: 'var(--co-radius-md)',
              background: 'var(--co-bg-subtle)',
              border: '1px solid var(--co-border-subtle)',
              display: 'flex',
              gap: 12,
              alignItems: 'flex-start',
              opacity: isVerified ? 1 : 0.6,
            }}
          >
            <div style={{ color: 'var(--co-primary-600)', marginTop: 2 }}>
              <IconCalendar size={20} />
            </div>
            <div>
              <strong style={{ display: 'block', fontSize: '0.85rem', color: 'var(--co-text-main)' }}>
                4. Event Operations
              </strong>
              <span style={{ fontSize: '0.75rem', color: 'var(--co-text-muted)' }}>
                Programs, tasks &amp; check-in.
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Member Directory and Team Table */}
      {activeOrg && (
        <MemberDirectoryTable
          currentUser={currentUser}
          activeOrgId={activeOrg.id}
          invitations={invitations}
          onRevokeInvitation={onRevokeInvitation}
          canManageRoles={canManageRoles}
          onOpenInviteModal={() => setIsInviteModalOpen(true)}
          isVerified={isVerified}
          authToken={authToken}
        />
      )}

      {/* Modals */}
      <CreateOrgModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onSuccess={onCreateOrg}
        authToken={authToken}
      />

      {activeOrg && (
        <>
          <PlatformVerifyModal
            isOpen={isVerifyModalOpen}
            onClose={() => setIsVerifyModalOpen(false)}
            orgId={activeOrg.id}
            clubName={activeOrg.club_name}
            collegeName={activeOrg.college_name}
            onSuccess={onUpdateOrg}
            authToken={authToken}
          />

          <InviteMemberModal
            isOpen={isInviteModalOpen}
            onClose={() => setIsInviteModalOpen(false)}
            orgId={activeOrg.id}
            clubName={activeOrg.club_name}
            isVerified={isVerified}
            onSuccess={onAddInvitation}
            authToken={authToken}
          />
        </>
      )}
    </div>
  );
};

