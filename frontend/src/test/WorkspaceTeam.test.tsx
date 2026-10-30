import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import { OrganizationSwitcher } from '../components/org/OrganizationSwitcher';
import { CreateOrgModal } from '../components/org/CreateOrgModal';
import { VerificationBanner } from '../components/org/VerificationBanner';
import { PlatformVerifyModal } from '../components/org/PlatformVerifyModal';
import { InviteMemberModal } from '../components/org/InviteMemberModal';
import { MemberDirectoryTable } from '../components/org/MemberDirectoryTable';
import { InvitationAcceptView } from '../components/org/InvitationAcceptView';
import { WorkspaceOverview } from '../components/org/WorkspaceOverview';
import * as orgApi from '../api/organizations';
import { ApiError } from '../api/client';
import { parseInitialInvitationState } from '../App';
import type {
  CurrentUserResponse,
  OrganizationResponse,
  OrganizationDetailResponse,
  InvitationResponse,
  OrganizationMemberResponse,
} from '../api/types';

const mockCurrentUser: CurrentUserResponse = {
  id: 'usr-1111',
  email: 'admin@stanford.edu',
  display_name: 'Alex Rivera',
  account_status: 'active',
  email_verified: true,
  is_platform_admin: false,
  memberships: [
    {
      id: 'mem-1111',
      organization_id: 'org-1111',
      organization_name: 'AI Safety Student Group',
      college_name: 'Stanford University',
      membership_status: 'active',
      roles: [
        {
          id: 'role-1',
          role_name: 'PRIMARY_ADMIN',
          scope_type: 'organization',
          scope_id: null,
        },
      ],
    },
  ],
};

const mockOrgs: OrganizationResponse[] = [
  {
    id: 'org-1111',
    college_name: 'Stanford University',
    club_name: 'AI Safety Student Group',
    verification_status: 'pending_verification',
    created_at: '2026-10-30T10:00:00Z',
  },
  {
    id: 'org-2222',
    college_name: 'UC Berkeley',
    club_name: 'Robotics Team',
    verification_status: 'verified',
    created_at: '2026-10-29T12:00:00Z',
  },
];

const mockOrgDetail: OrganizationDetailResponse = {
  id: 'org-1111',
  college_name: 'Stanford University',
  club_name: 'AI Safety Student Group',
  verification_status: 'pending_verification',
  created_at: '2026-10-30T10:00:00Z',
  created_by_user_id: 'usr-1111',
  verification_note: null,
  verification_reviewed_at: null,
  verification_reviewer_id: null,
};

const mockInvitations: InvitationResponse[] = [
  {
    id: 'inv-1',
    organization_id: 'org-1111',
    email: 'sarah@stanford.edu',
    email_normalized: 'sarah@stanford.edu',
    role_name: 'OFFICE_BEARER',
    scope_type: 'organization',
    scope_id: null,
    status: 'pending',
    expires_at: '2026-11-06T10:00:00Z',
    created_at: '2026-10-30T10:00:00Z',
  },
];

describe('Phase 1: Workspace, Organization & Team Management', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  describe('OrganizationSwitcher Component', () => {
    it('renders the active organization and allows switching workspaces', () => {
      const handleSelect = vi.fn();
      const handleCreateClick = vi.fn();

      render(
        <OrganizationSwitcher
          organizations={mockOrgs}
          activeOrgId="org-1111"
          onSelectOrg={handleSelect}
          onCreateOrgClick={handleCreateClick}
        />,
      );

      // Verify active org is displayed
      expect(screen.getByText('AI Safety Student Group')).toBeInTheDocument();

      // Open dropdown
      const button = screen.getByRole('button', { name: /select organization workspace/i });
      fireEvent.click(button);

      // Verify other org is listed
      expect(screen.getByText('Robotics Team')).toBeInTheDocument();

      // Click the other workspace
      fireEvent.click(screen.getByText('Robotics Team'));
      expect(handleSelect).toHaveBeenCalledWith('org-2222');
    });

    it('triggers create workspace modal when new workspace button is clicked', () => {
      const handleCreateClick = vi.fn();

      render(
        <OrganizationSwitcher
          organizations={mockOrgs}
          activeOrgId="org-1111"
          onSelectOrg={vi.fn()}
          onCreateOrgClick={handleCreateClick}
        />,
      );

      const button = screen.getByRole('button', { name: /select organization workspace/i });
      fireEvent.click(button);

      const createBtn = screen.getByRole('button', { name: /create new workspace/i });
      fireEvent.click(createBtn);

      expect(handleCreateClick).toHaveBeenCalledTimes(1);
    });
  });

  describe('CreateOrgModal Component', () => {
    it('validates min length and submits new organization workspace', async () => {
      const handleSuccess = vi.fn();
      const handleClose = vi.fn();

      const createdOrg: OrganizationResponse = {
        id: 'org-3333',
        college_name: 'MIT',
        club_name: 'Autonomous Systems Society',
        verification_status: 'pending_verification',
        created_at: '2026-10-30T11:00:00Z',
      };

      vi.spyOn(orgApi, 'createOrganization').mockResolvedValue(createdOrg);

      render(
        <CreateOrgModal
          isOpen={true}
          onClose={handleClose}
          onSuccess={handleSuccess}
        />,
      );

      const collegeInput = screen.getByLabelText(/college \/ university name/i);
      const clubInput = screen.getByLabelText(/student club \/ chapter name/i);
      const submitBtn = screen.getByRole('button', { name: /create workspace/i });

      // Button is initially disabled because inputs are empty
      expect(submitBtn).toBeDisabled();

      fireEvent.change(collegeInput, { target: { value: 'MIT' } });
      fireEvent.change(clubInput, { target: { value: 'Autonomous Systems Society' } });

      expect(submitBtn).not.toBeDisabled();
      fireEvent.click(submitBtn);

      await waitFor(() => {
        expect(orgApi.createOrganization).toHaveBeenCalledWith(
          {
            college_name: 'MIT',
            club_name: 'Autonomous Systems Society',
          },
          { authToken: undefined },
        );
        expect(handleSuccess).toHaveBeenCalledWith(createdOrg);
        expect(handleClose).toHaveBeenCalled();
      });
    });

    it('displays server validation error on failure', async () => {
      vi.spyOn(orgApi, 'createOrganization').mockRejectedValue(
        new ApiError(400, 'Creator email must be verified before creating an organization workspace.'),
      );

      render(
        <CreateOrgModal
          isOpen={true}
          onClose={vi.fn()}
          onSuccess={vi.fn()}
        />,
      );

      fireEvent.change(screen.getByLabelText(/college \/ university name/i), {
        target: { value: 'Harvard' },
      });
      fireEvent.change(screen.getByLabelText(/student club \/ chapter name/i), {
        target: { value: 'Debate Council' },
      });

      fireEvent.click(screen.getByRole('button', { name: /create workspace/i }));

      await waitFor(() => {
        expect(
          screen.getByText(/creator email must be verified before creating an organization workspace/i),
        ).toBeInTheDocument();
      });
    });
  });

  describe('VerificationBanner & Platform Review', () => {
    it('displays pending verification warning and hides admin review button from ordinary members', () => {
      render(
        <VerificationBanner
          organization={mockOrgDetail}
          isPlatformAdmin={false}
          onOpenVerifyModal={vi.fn()}
        />,
      );

      expect(screen.getByText(/workspace verification pending/i)).toBeInTheDocument();
      expect(screen.queryByRole('button', { name: /review as admin/i })).not.toBeInTheDocument();
    });

    it('displays review button for platform administrators and triggers modal', () => {
      const handleOpenModal = vi.fn();

      render(
        <VerificationBanner
          organization={mockOrgDetail}
          isPlatformAdmin={true}
          onOpenVerifyModal={handleOpenModal}
        />,
      );

      const reviewBtn = screen.getByRole('button', { name: /review as admin/i });
      expect(reviewBtn).toBeInTheDocument();
      fireEvent.click(reviewBtn);
      expect(handleOpenModal).toHaveBeenCalledTimes(1);
    });

    it('displays rejection reason when organization status is rejected', () => {
      const rejectedOrg: OrganizationDetailResponse = {
        ...mockOrgDetail,
        verification_status: 'rejected',
        verification_note: 'Institutional email domain unverified by campus registry.',
        verification_reviewed_at: '2026-10-30T10:30:00Z',
      };

      render(
        <VerificationBanner
          organization={rejectedOrg}
          isPlatformAdmin={false}
          onOpenVerifyModal={vi.fn()}
        />,
      );

      expect(screen.getByText(/workspace verification rejected/i)).toBeInTheDocument();
      expect(
        screen.getByText(/institutional email domain unverified by campus registry/i),
      ).toBeInTheDocument();
    });

    it('submits platform verification review through PlatformVerifyModal', async () => {
      const handleSuccess = vi.fn();
      const handleClose = vi.fn();

      const updatedOrg: OrganizationDetailResponse = {
        ...mockOrgDetail,
        verification_status: 'verified',
        verification_reviewed_at: '2026-10-30T11:00:00Z',
      };

      vi.spyOn(orgApi, 'verifyOrganization').mockResolvedValue(updatedOrg);

      render(
        <PlatformVerifyModal
          isOpen={true}
          onClose={handleClose}
          orgId="org-1111"
          clubName="AI Safety Student Group"
          collegeName="Stanford University"
          onSuccess={handleSuccess}
        />,
      );

      expect(screen.getByText(/platform administrator verification review/i)).toBeInTheDocument();

      const confirmBtn = screen.getByRole('button', { name: /confirm verification/i });
      fireEvent.click(confirmBtn);

      await waitFor(() => {
        expect(orgApi.verifyOrganization).toHaveBeenCalledWith(
          'org-1111',
          {
            decision: 'verified',
            note: null,
          },
          { authToken: undefined },
        );
        expect(handleSuccess).toHaveBeenCalledWith(updatedOrg);
        expect(handleClose).toHaveBeenCalled();
      });
    });
  });

  describe('InviteMemberModal Component', () => {
    it('disables invitation submission when organization is unverified per policy FPC-02', () => {
      render(
        <InviteMemberModal
          isOpen={true}
          onClose={vi.fn()}
          orgId="org-1111"
          clubName="AI Safety Student Group"
          isVerified={false}
          onSuccess={vi.fn()}
        />,
      );

      expect(screen.getByText(/verification prerequisite/i)).toBeInTheDocument();
      const sendBtn = screen.getByRole('button', { name: /send invitation/i });
      expect(sendBtn).toBeDisabled();
    });

    it('handles transactional email unconfigured error (HTTP 503 / FPC-06) cleanly', async () => {
      vi.spyOn(orgApi, 'createInvitation').mockRejectedValue(
        new ApiError(
          503,
          'Invitation delivery is unavailable: transactional email provider is not configured (FPC-06).',
        ),
      );

      render(
        <InviteMemberModal
          isOpen={true}
          onClose={vi.fn()}
          orgId="org-2222"
          clubName="Robotics Team"
          isVerified={true}
          onSuccess={vi.fn()}
        />,
      );

      const emailInput = screen.getByLabelText(/recipient email address/i);
      fireEvent.change(emailInput, { target: { value: 'robotics-lead@berkeley.edu' } });

      const sendBtn = screen.getByRole('button', { name: /send invitation/i });
      fireEvent.click(sendBtn);

      await waitFor(() => {
        expect(
          screen.getByText(/transactional email delivery is unconfigured on the server \(policy fpc-06\)/i),
        ).toBeInTheDocument();
      });
    });
  });

  describe('MemberDirectoryTable Component', () => {
    it('renders active current user member and roles', () => {
      render(
        <MemberDirectoryTable
          currentUser={mockCurrentUser}
          activeOrgId="org-1111"
          invitations={mockInvitations}
          onRevokeInvitation={vi.fn()}
          canManageRoles={true}
          onOpenInviteModal={vi.fn()}
          isVerified={true}
        />,
      );

      expect(screen.getByText('Alex Rivera')).toBeInTheDocument();
      expect(screen.getByText('admin@stanford.edu')).toBeInTheDocument();
      expect(screen.getAllByText('Primary Admin').length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText('You')).toBeInTheDocument();
    });

    it('switches to invitations tab and supports revoking pending invitations', async () => {
      const handleRevoke = vi.fn().mockResolvedValue(undefined);

      render(
        <MemberDirectoryTable
          currentUser={mockCurrentUser}
          activeOrgId="org-1111"
          invitations={mockInvitations}
          onRevokeInvitation={handleRevoke}
          canManageRoles={true}
          onOpenInviteModal={vi.fn()}
          isVerified={true}
        />,
      );

      const invitationsTab = screen.getByRole('button', { name: /invitations \(1\)/i });
      fireEvent.click(invitationsTab);

      expect(screen.getByText('sarah@stanford.edu')).toBeInTheDocument();
      expect(screen.getAllByText('Office Bearer').length).toBeGreaterThanOrEqual(1);

      const revokeBtn = screen.getByRole('button', { name: /revoke/i });
      fireEvent.click(revokeBtn);

      expect(handleRevoke).toHaveBeenCalledWith('inv-1');
    });

    it('fetches and renders real member roster from listOrganizationMembers API with contact privacy masking', async () => {
      const apiMembers: OrganizationMemberResponse[] = [
        {
          id: 'mem-1',
          organization_id: 'org-1111',
          user_id: 'usr-1111',
          display_name: 'Alex Rivera',
          email: 'admin@stanford.edu',
          email_masked: false,
          membership_status: 'active',
          joined_at: '2026-10-30T10:00:00Z',
          roles: [
            {
              id: 'role-1',
              role_name: 'PRIMARY_ADMIN',
              scope_type: 'organization',
              scope_id: null,
            },
          ],
        },
        {
          id: 'mem-2',
          organization_id: 'org-1111',
          user_id: 'usr-2222',
          display_name: 'Taylor Coordinator',
          email: 't***r@stanford.edu',
          email_masked: true,
          membership_status: 'active',
          joined_at: '2026-10-30T11:00:00Z',
          roles: [
            {
              id: 'role-2',
              role_name: 'COORDINATOR',
              scope_type: 'organization',
              scope_id: null,
            },
          ],
        },
      ];

      vi.spyOn(orgApi, 'listOrganizationMembers').mockResolvedValue(apiMembers);

      render(
        <MemberDirectoryTable
          currentUser={mockCurrentUser}
          activeOrgId="org-1111"
          invitations={[]}
          canManageRoles={true}
          onOpenInviteModal={vi.fn()}
          isVerified={true}
          authToken="test_token"
        />,
      );

      await waitFor(() => {
        expect(orgApi.listOrganizationMembers).toHaveBeenCalledWith(
          'org-1111',
          { status: undefined, limit: 20, offset: 0 },
          { authToken: 'test_token' },
        );
        expect(screen.getByText('Taylor Coordinator')).toBeInTheDocument();
        expect(screen.getByText('t***r@stanford.edu')).toBeInTheDocument();
        expect(screen.getByText('Masked')).toBeInTheDocument();
        expect(screen.getByText('admin@stanford.edu')).toBeInTheDocument();
      });
    });

    it('supports member status filtering and pagination', async () => {
      const listMembersSpy = vi.spyOn(orgApi, 'listOrganizationMembers').mockResolvedValue([]);

      render(
        <MemberDirectoryTable
          currentUser={mockCurrentUser}
          activeOrgId="org-1111"
          invitations={[]}
          canManageRoles={true}
          onOpenInviteModal={vi.fn()}
          isVerified={true}
        />,
      );

      const statusSelect = screen.getByLabelText(/filter members by status/i);
      fireEvent.change(statusSelect, { target: { value: 'invited' } });

      await waitFor(() => {
        expect(listMembersSpy).toHaveBeenCalledWith(
          'org-1111',
          { status: 'invited', limit: 20, offset: 0 },
          { authToken: undefined },
        );
      });
    });
  });

  describe('InvitationAcceptView Component', () => {
    it('submits token and renders successful acceptance details', async () => {
      const handleAcceptSuccess = vi.fn();

      vi.spyOn(orgApi, 'acceptInvitation').mockResolvedValue({
        membership_id: 'mem-9999',
        organization_id: 'org-1111',
        role_name: 'COORDINATOR',
        scope_type: 'organization',
        status: 'active',
      });

      render(
        <InvitationAcceptView
          initialToken="raw_token_1234567890abcdef"
          onAcceptSuccess={handleAcceptSuccess}
        />,
      );

      const submitBtn = screen.getByRole('button', { name: /accept invitation/i });
      fireEvent.click(submitBtn);

      await waitFor(() => {
        expect(orgApi.acceptInvitation).toHaveBeenCalledWith(
          { token: 'raw_token_1234567890abcdef' },
          { authToken: undefined },
        );
        expect(screen.getByText(/invitation accepted!/i)).toBeInTheDocument();
        expect(screen.getByText('COORDINATOR')).toBeInTheDocument();
      });
    });

    it('maps 401 unauthenticated error with clear identity binding message', async () => {
      vi.spyOn(orgApi, 'acceptInvitation').mockRejectedValue(
        new ApiError(401, 'Authentication token required.'),
      );

      render(
        <InvitationAcceptView
          initialToken="invalid_token_12345"
          onAcceptSuccess={vi.fn()}
        />,
      );

      fireEvent.click(screen.getByRole('button', { name: /accept invitation/i }));

      await waitFor(() => {
        expect(
          screen.getByText(/authentication is required to accept an invitation/i),
        ).toBeInTheDocument();
      });
    });

    it('maps 409 already member conflict error', async () => {
      vi.spyOn(orgApi, 'acceptInvitation').mockRejectedValue(
        new ApiError(409, 'User already has an active membership in this organization.'),
      );

      render(
        <InvitationAcceptView
          initialToken="token_already_member"
          onAcceptSuccess={vi.fn()}
        />,
      );

      fireEvent.click(screen.getByRole('button', { name: /accept invitation/i }));

      await waitFor(() => {
        expect(
          screen.getByText(/you are already an active member of this organization workspace/i),
        ).toBeInTheDocument();
      });
    });

    it('displays legacy query rejection warning and prompts manual entry', () => {
      render(
        <InvitationAcceptView
          initialToken=""
          legacyQueryRejected={true}
          onAcceptSuccess={vi.fn()}
        />,
      );

      expect(screen.getByText(/legacy link format rejected/i)).toBeInTheDocument();
      expect(
        screen.getByText(/legacy query-parameter invitation links are no longer supported for security/i),
      ).toBeInTheDocument();
      const tokenInput = screen.getByLabelText(/single-use invitation token/i) as HTMLInputElement;
      expect(tokenInput.value).toBe('');
    });

    it('never persists tokens into localStorage or sessionStorage', async () => {
      const setItemLocalSpy = vi.spyOn(Storage.prototype, 'setItem');
      vi.spyOn(orgApi, 'acceptInvitation').mockResolvedValue({
        membership_id: 'mem-9999',
        organization_id: 'org-1111',
        role_name: 'COORDINATOR',
        scope_type: 'organization',
        status: 'active',
      });

      render(
        <InvitationAcceptView
          initialToken="ephemeral_memory_token"
          onAcceptSuccess={vi.fn()}
        />,
      );

      fireEvent.click(screen.getByRole('button', { name: /accept invitation/i }));

      await waitFor(() => {
        expect(orgApi.acceptInvitation).toHaveBeenCalledWith(
          { token: 'ephemeral_memory_token' },
          { authToken: undefined },
        );
      });

      // Storage.prototype.setItem should never be called with tokens
      const tokenStored = setItemLocalSpy.mock.calls.some(([key, val]) =>
        String(key).includes('token') || String(val).includes('ephemeral_memory_token'),
      );
      expect(tokenStored).toBe(false);
    });
  });

  describe('Secure Fragment Token Routing & Extraction', () => {
    it('extracts URL fragment #token=... and immediately scrubs window.location without storing in storage', () => {
      const replaceStateSpy = vi.spyOn(window.history, 'replaceState');
      delete (window as any).location;
      (window as any).location = {
        pathname: '/app',
        search: '?mode=workspace',
        hash: '#token=frag_sec_token_987654321',
      };

      const result = parseInitialInvitationState();

      expect(result.initialToken).toBe('frag_sec_token_987654321');
      expect(result.legacyQueryRejected).toBe(false);
      expect(result.initialMode).toBe('accept-invite');
      expect(replaceStateSpy).toHaveBeenCalledWith(null, '', '/app?mode=workspace');
    });

    it('rejects legacy query parameter ?token=... without extracting into initialToken and scrubs query', () => {
      const replaceStateSpy = vi.spyOn(window.history, 'replaceState');
      delete (window as any).location;
      (window as any).location = {
        pathname: '/app',
        search: '?token=insecure_query_token_123',
        hash: '',
      };

      const result = parseInitialInvitationState();

      expect(result.initialToken).toBe('');
      expect(result.legacyQueryRejected).toBe(true);
      expect(result.initialMode).toBe('accept-invite');
      expect(replaceStateSpy).toHaveBeenCalledWith(null, '', '/app');
    });
  });

  describe('WorkspaceOverview Hub', () => {
    it('renders milestones, organization switcher, and member table', () => {
      render(
        <WorkspaceOverview
          currentUser={mockCurrentUser}
          organizations={mockOrgs}
          activeOrg={mockOrgDetail}
          activeOrgId="org-1111"
          onSelectOrg={vi.fn()}
          onRefreshOrg={vi.fn()}
          onCreateOrg={vi.fn()}
          onUpdateOrg={vi.fn()}
          invitations={mockInvitations}
          onAddInvitation={vi.fn()}
          onRevokeInvitation={vi.fn()}
          isLoading={false}
          error={null}
        />,
      );

      expect(screen.getByText('Workspace Setup Milestones')).toBeInTheDocument();
      expect(screen.getByText('1. Workspace Created')).toBeInTheDocument();
      expect(screen.getByText('2. Institutional Verification')).toBeInTheDocument();
      expect(screen.getByText('Team & Access Management')).toBeInTheDocument();
    });

    it('renders empty workspace prompt when user has no organizations', () => {
      render(
        <WorkspaceOverview
          currentUser={mockCurrentUser}
          organizations={[]}
          activeOrg={null}
          activeOrgId={null}
          onSelectOrg={vi.fn()}
          onRefreshOrg={vi.fn()}
          onCreateOrg={vi.fn()}
          onUpdateOrg={vi.fn()}
          invitations={[]}
          onAddInvitation={vi.fn()}
          onRevokeInvitation={vi.fn()}
          isLoading={false}
          error={null}
        />,
      );

      expect(screen.getByText('No Workspaces Found')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /create first workspace/i })).toBeInTheDocument();
    });
  });
});
