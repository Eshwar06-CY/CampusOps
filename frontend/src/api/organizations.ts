/**
 * Workspace, Organization, and Member Invitation API Client (Phase 1).
 *
 * Implements endpoints from Slice 2B:
 * - Current user discovery: GET /api/v1/me
 * - Workspace list: GET /api/v1/organizations
 * - Workspace details: GET /api/v1/organizations/{id}
 * - Workspace creation: POST /api/v1/organizations
 * - Platform admin verification: POST /api/v1/organizations/{id}/verify
 * - Scoped member invitation: POST /api/v1/organizations/{id}/invitations
 * - Single-use token acceptance: POST /api/v1/invitations/accept
 * - Invitation revocation: POST /api/v1/organizations/{id}/invitations/{id}/revoke
 */

import { apiClient, type RequestOptions } from './client';
import type {
  CurrentUserResponse,
  OrganizationResponse,
  OrganizationDetailResponse,
  OrganizationCreateRequest,
  OrganizationVerifyRequest,
  OrganizationMemberResponse,
  InvitationCreateRequest,
  InvitationResponse,
  InvitationAcceptRequest,
  InvitationAcceptResponse,
} from './types';

export interface OrgApiOptions extends RequestOptions {
  authToken?: string | null;
  signal?: AbortSignal;
}

/**
 * Returns current authenticated user profile, platform admin status, and active memberships.
 */
export async function getCurrentUser(options: OrgApiOptions = {}): Promise<CurrentUserResponse> {
  return apiClient<CurrentUserResponse>('/api/v1/me', {
    method: 'GET',
    authToken: options.authToken,
    signal: options.signal,
  });
}

/**
 * Lists organizations where caller holds active membership (strictly tenant-isolated).
 */
export async function listOrganizations(options: OrgApiOptions = {}): Promise<OrganizationResponse[]> {
  return apiClient<OrganizationResponse[]>('/api/v1/organizations', {
    method: 'GET',
    authToken: options.authToken,
    signal: options.signal,
  });
}

/**
 * Retrieves details and verification state for an organization workspace.
 * Caller must be active member or platform admin; otherwise returns HTTP 404.
 */
export async function getOrganizationDetails(
  orgId: string,
  options: OrgApiOptions = {},
): Promise<OrganizationDetailResponse> {
  return apiClient<OrganizationDetailResponse>(`/api/v1/organizations/${encodeURIComponent(orgId)}`, {
    method: 'GET',
    authToken: options.authToken,
    signal: options.signal,
  });
}

/**
 * Creates a new organization workspace in pending_verification status.
 * Authenticated creator is granted PRIMARY_ADMIN role.
 */
export async function createOrganization(
  payload: OrganizationCreateRequest,
  options: OrgApiOptions = {},
): Promise<OrganizationResponse> {
  return apiClient<OrganizationResponse>('/api/v1/organizations', {
    method: 'POST',
    body: JSON.stringify(payload),
    authToken: options.authToken,
    signal: options.signal,
  });
}

/**
 * Platform administrator approves or rejects an organization workspace.
 * Requires explicit platform admin authority.
 */
export async function verifyOrganization(
  orgId: string,
  payload: OrganizationVerifyRequest,
  options: OrgApiOptions = {},
): Promise<OrganizationDetailResponse> {
  return apiClient<OrganizationDetailResponse>(`/api/v1/organizations/${encodeURIComponent(orgId)}/verify`, {
    method: 'POST',
    body: JSON.stringify(payload),
    authToken: options.authToken,
    signal: options.signal,
  });
}

/**
 * Creates an organization, department, or event invitation.
 * Fails closed (HTTP 503) if transactional email is unconfigured (FPC-06).
 */
export async function createInvitation(
  orgId: string,
  payload: InvitationCreateRequest,
  options: OrgApiOptions = {},
): Promise<InvitationResponse> {
  return apiClient<InvitationResponse>(`/api/v1/organizations/${encodeURIComponent(orgId)}/invitations`, {
    method: 'POST',
    body: JSON.stringify(payload),
    authToken: options.authToken,
    signal: options.signal,
  });
}

/**
 * Accepts a single-use invitation via token in JSON body.
 */
export async function acceptInvitation(
  payload: InvitationAcceptRequest,
  options: OrgApiOptions = {},
): Promise<InvitationAcceptResponse> {
  return apiClient<InvitationAcceptResponse>('/api/v1/invitations/accept', {
    method: 'POST',
    body: JSON.stringify(payload),
    authToken: options.authToken,
    signal: options.signal,
  });
}

/**
 * Revokes a pending invitation. Requires role management authority in the organization.
 */
export async function revokeInvitation(
  orgId: string,
  invitationId: string,
  options: OrgApiOptions = {},
): Promise<InvitationResponse> {
  return apiClient<InvitationResponse>(
    `/api/v1/organizations/${encodeURIComponent(orgId)}/invitations/${encodeURIComponent(invitationId)}/revoke`,
    {
      method: 'POST',
      authToken: options.authToken,
      signal: options.signal,
    },
  );
}

export interface ListMembersParams {
  status?: string;
  limit?: number;
  offset?: number;
}

export interface ListInvitationsParams {
  status?: string;
  limit?: number;
  offset?: number;
}

/**
 * Lists organization members with roles and privacy-aware contact disclosure.
 * Tenant-isolated: only active members or platform administrators can query.
 */
export async function listOrganizationMembers(
  orgId: string,
  params: ListMembersParams = {},
  options: OrgApiOptions = {},
): Promise<OrganizationMemberResponse[]> {
  const query = new URLSearchParams();
  if (params.status) query.set('status', params.status);
  if (params.limit !== undefined) query.set('limit', String(params.limit));
  if (params.offset !== undefined) query.set('offset', String(params.offset));
  const qs = query.toString();
  const path = `/api/v1/organizations/${encodeURIComponent(orgId)}/members${qs ? `?${qs}` : ''}`;
  return apiClient<OrganizationMemberResponse[]>(path, {
    method: 'GET',
    authToken: options.authToken,
    signal: options.signal,
  });
}

/**
 * Lists organization invitations. Requires role management authority (PRIMARY_ADMIN / OFFICE_BEARER).
 */
export async function listOrganizationInvitations(
  orgId: string,
  params: ListInvitationsParams = {},
  options: OrgApiOptions = {},
): Promise<InvitationResponse[]> {
  const query = new URLSearchParams();
  if (params.status) query.set('status', params.status);
  if (params.limit !== undefined) query.set('limit', String(params.limit));
  if (params.offset !== undefined) query.set('offset', String(params.offset));
  const qs = query.toString();
  const path = `/api/v1/organizations/${encodeURIComponent(orgId)}/invitations${qs ? `?${qs}` : ''}`;
  return apiClient<InvitationResponse[]>(path, {
    method: 'GET',
    authToken: options.authToken,
    signal: options.signal,
  });
}

