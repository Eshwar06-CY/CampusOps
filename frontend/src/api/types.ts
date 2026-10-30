/**
 * Strict TypeScript Request and Response Contracts for CampusOps Slice 5C.
 * Matches backend Pydantic models in backend/app/schemas/registration.py.
 */

// ==========================================
// 1. Public API Contracts
// ==========================================

export type RegistrationFormat = 'solo' | 'team' | 'both';
export type RegistrationStatus = 'open' | 'closed' | 'not_yet_open' | 'ended';
export type RegistrationType = 'solo' | 'team';
export type AttendeeRole = 'leader' | 'member';

export interface PublicEventDetails {
  public_registration_key: string;
  event_id: string;
  event_name: string;
  description: string | null;
  event_date: string;
  event_end_date: string | null;
  venue: string | null;
  timezone: string;
  registration_status: RegistrationStatus;
  registration_format: RegistrationFormat;
  team_size_min: number;
  team_size_max: number;
  capacity_available: boolean;
}

export interface PublicParticipantInput {
  full_name: string;
  email: string;
  phone_number?: string | null;
  college_name?: string | null;
  student_id?: string | null;
  is_primary_contact?: boolean;
  team_role?: AttendeeRole | null;
}

export interface PublicRegistrationRequest {
  registration_type: RegistrationType;
  team_name?: string | null;
  contact_email: string;
  contact_phone?: string | null;
  idempotency_key?: string | null;
  participants: PublicParticipantInput[];
}

export interface IssuedPass {
  participant_id: string;
  participant_name: string;
  ticket_reference: string;
  pass_code: string; // "CO-PASS-..." or "<REDACTED_AFTER_ISSUANCE>"
  pass_url: string;
}

export interface PublicRegistrationResponse {
  registration_id: string;
  confirmation_code: string;
  registration_status: 'confirmed' | 'waitlisted' | 'cancelled';
  registration_type: RegistrationType;
  team_name: string | null;
  is_waitlisted: boolean;
  passes: IssuedPass[];
}

export interface PublicPassVerifyRequest {
  pass_code: string;
}

export interface PublicPassVerifyResponse {
  ticket_reference: string;
  pass_code: string;
  event_name: string;
  participant_name: string;
  status: string; // 'issued', 'used', 'revoked', 'cancelled'
  issued_at: string;
  used_at: string | null;
  qr_payload: string;
  instructions: string;
}

export interface PublicRegistrationLookupRequest {
  confirmation_code: string;
}

export interface PublicRegistrationLookupParticipant {
  full_name: string;
  team_role: string | null;
  is_primary_contact: boolean;
  status: string;
}

export interface PublicRegistrationLookupResponse {
  confirmation_code: string;
  registration_status: string;
  registration_type: RegistrationType;
  team_name: string | null;
  participant_count: number;
  created_at: string;
  participants: PublicRegistrationLookupParticipant[];
}

export interface PublicRegistrationCancelRequest {
  confirmation_code: string;
  contact_email: string;
  cancellation_reason: string;
}

export interface PublicRegistrationCancelResponse {
  confirmation_code: string;
  registration_status: string;
  cancelled_at: string;
  message: string;
}

// ==========================================
// 2. Staff API Contracts
// ==========================================

export interface EventRegistrationSettingsResponse {
  event_id: string;
  is_open: boolean;
  registration_format: RegistrationFormat;
  capacity_limit: number;
  current_confirmed_count: number;
  waitlist_limit: number | null;
  team_size_min: number;
  team_size_max: number;
  registration_start_at: string | null;
  registration_end_at: string | null;
  public_registration_key?: string | null;
}

export interface EventRegistrationSettingsUpdateRequest {
  is_open?: boolean;
  registration_format?: RegistrationFormat;
  capacity_limit?: number;
  team_size_min?: number;
  team_size_max?: number;
  rotate_registration_key?: boolean;
}

export interface StaffRegistrationSummaryResponse {
  registration_id: string;
  confirmation_code: string;
  registration_type: RegistrationType;
  team_name: string | null;
  status: string;
  participant_count: number;
  contact_email: string; // masked or unmasked
  contact_phone: string | null; // masked or unmasked
  created_at: string;
}

export interface StaffParticipantRosterItemResponse {
  participant_id: string;
  full_name: string;
  email: string; // masked or unmasked
  phone_number: string | null; // masked or unmasked
  college_name: string | null;
  student_id: string | null;
  team_name: string | null;
  role_in_team: string | null;
  attendance_status: string; // 'registered', 'checked_in', 'cancelled'
  ticket_status: string | null; // 'active', 'revoked', 'cancelled', 'expired'
  ticket_reference: string | null;
  check_in_id: string | null;
  checked_in_at: string | null;
}

export interface CheckInRequest {
  pass_code?: string | null;
  participant_id?: string | null;
  method?: string; // 'qr_scan', 'manual_code', 'manual_search'
  station_id?: string | null;
  idempotency_key?: string | null;
}

export interface CheckInResponse {
  check_in_id: string;
  status: 'verified' | 'already_checked_in';
  participant_id: string;
  participant_name: string;
  team_name: string | null;
  checked_in_at: string;
  station_id: string | null;
  message: string;
}

export interface CheckInLookupItemResponse {
  participant_id: string;
  full_name: string;
  email_masked: string;
  team_name: string | null;
  student_id: string | null;
  ticket_reference: string | null;
  can_check_in: boolean;
  attendance_status: string;
}

export interface CheckInVoidRequest {
  reason: string; // min length 10
}

export interface CheckInVoidResponse {
  check_in_id: string;
  participant_id: string;
  status: 'voided';
  voided_at: string;
  reason: string;
  message: string;
}

export interface AttendanceSummaryResponse {
  event_id: string;
  capacity_limit: number;
  current_confirmed_count: number;
  current_attended_count: number;
  attendance_percentage: number;
  total_individual_registrations: number;
  total_team_registrations: number;
  total_participants_registered: number;
  teams_fully_attended: number;
  teams_partially_attended: number;
  teams_absent: number;
}

// ==========================================
// 3. Organization, Identity & Team Contracts (Phase 1)
// ==========================================

export type VerificationStatus = 'pending_verification' | 'verified' | 'rejected';

export interface OrganizationResponse {
  id: string;
  college_name: string;
  club_name: string;
  verification_status: VerificationStatus;
  created_at: string;
}

export interface OrganizationDetailResponse extends OrganizationResponse {
  created_by_user_id: string;
  verification_note?: string | null;
  verification_reviewed_at?: string | null;
  verification_reviewer_id?: string | null;
}

export interface OrganizationCreateRequest {
  college_name: string;
  club_name: string;
}

export interface OrganizationVerifyRequest {
  decision: 'verified' | 'rejected';
  note?: string | null;
}

export type InvitableRole =
  | 'OFFICE_BEARER'
  | 'EVENT_LEAD'
  | 'DEPARTMENT_LEAD'
  | 'COORDINATOR'
  | 'REGISTRATION_STAFF';

export interface InvitationCreateRequest {
  email: string;
  role_name: InvitableRole | string;
  scope_type?: 'organization' | 'department' | 'event';
  scope_id?: string | null;
}

export interface InvitationResponse {
  id: string;
  organization_id: string;
  email: string;
  email_normalized: string;
  role_name: string;
  scope_type: string;
  scope_id: string | null;
  status: string; // 'pending' | 'accepted' | 'revoked' | 'expired'
  expires_at: string;
  created_at: string;
}

export interface InvitationAcceptRequest {
  token: string;
}

export interface InvitationAcceptResponse {
  membership_id: string;
  organization_id: string;
  role_name: string;
  scope_type: string;
  status: string;
}

export interface RoleSummaryResponse {
  id: string;
  role_name: string;
  scope_type: string;
  scope_id: string | null;
}

export interface OrganizationMemberResponse {
  id: string;
  organization_id: string;
  user_id: string;
  display_name: string;
  email: string;
  email_masked: boolean;
  membership_status: string;
  joined_at: string;
  roles: RoleSummaryResponse[];
}

export interface MembershipSummaryResponse {
  id: string;
  organization_id: string;
  organization_name: string;
  college_name: string;
  membership_status: string;
  roles: RoleSummaryResponse[];
}

export interface CurrentUserResponse {
  id: string;
  email: string;
  display_name: string;
  account_status: string;
  email_verified: boolean;
  is_platform_admin: boolean;
  memberships: MembershipSummaryResponse[];
}

