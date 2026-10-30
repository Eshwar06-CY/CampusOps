/**
 * Staff Event Operations API Client.
 *
 * Implements Slice 5C staff operational endpoints:
 * - Registration settings management
 * - Roster list and participant detail (with masked contact fields)
 * - Check-in desk operations and lookup
 * - Manager check-in voids with mandatory audit reason
 * - Real-time attendance KPIs
 * - CSV export
 */

import { apiClient } from './client';
import type {
  EventRegistrationSettingsResponse,
  EventRegistrationSettingsUpdateRequest,
  StaffRegistrationSummaryResponse,
  StaffParticipantRosterItemResponse,
  CheckInRequest,
  CheckInResponse,
  CheckInLookupItemResponse,
  CheckInVoidResponse,
  AttendanceSummaryResponse,
  IssuedPass,
  PublicRegistrationRequest,
  PublicRegistrationResponse,
} from './types';

export interface StaffApiOptions {
  authToken?: string | null;
  signal?: AbortSignal;
}

/**
 * Retrieves registration settings and counters.
 */
export async function getRegistrationSettings(
  orgId: string,
  eventId: string,
  options: StaffApiOptions = {},
): Promise<EventRegistrationSettingsResponse> {
  return apiClient<EventRegistrationSettingsResponse>(
    `/api/v1/organizations/${encodeURIComponent(orgId)}/events/${encodeURIComponent(eventId)}/registration-settings`,
    {
      method: 'GET',
      authToken: options.authToken,
      signal: options.signal,
    },
  );
}

/**
 * Updates registration settings, limits, or rotates key.
 */
export async function updateRegistrationSettings(
  orgId: string,
  eventId: string,
  payload: EventRegistrationSettingsUpdateRequest,
  options: StaffApiOptions = {},
): Promise<EventRegistrationSettingsResponse> {
  return apiClient<EventRegistrationSettingsResponse>(
    `/api/v1/organizations/${encodeURIComponent(orgId)}/events/${encodeURIComponent(eventId)}/registration-settings`,
    {
      method: 'PUT',
      body: JSON.stringify(payload),
      authToken: options.authToken,
      signal: options.signal,
    },
  );
}

/**
 * Lists registration transactions with pagination.
 */
export async function listRegistrations(
  orgId: string,
  eventId: string,
  params: { status?: string; registration_type?: string; limit?: number; offset?: number } = {},
  options: StaffApiOptions = {},
): Promise<StaffRegistrationSummaryResponse[]> {
  const query = new URLSearchParams();
  if (params.status) query.set('status', params.status);
  if (params.registration_type) query.set('registration_type', params.registration_type);
  if (params.limit) query.set('limit', String(params.limit));
  if (params.offset) query.set('offset', String(params.offset));

  const qs = query.toString();
  return apiClient<StaffRegistrationSummaryResponse[]>(
    `/api/v1/organizations/${encodeURIComponent(orgId)}/events/${encodeURIComponent(eventId)}/registrations${qs ? `?${qs}` : ''}`,
    {
      method: 'GET',
      authToken: options.authToken,
      signal: options.signal,
    },
  );
}

/**
 * Creates desk walk-in registration.
 */
export async function createWalkInRegistration(
  orgId: string,
  eventId: string,
  payload: PublicRegistrationRequest,
  options: StaffApiOptions = {},
): Promise<PublicRegistrationResponse> {
  return apiClient<PublicRegistrationResponse>(
    `/api/v1/organizations/${encodeURIComponent(orgId)}/events/${encodeURIComponent(eventId)}/registrations/walk-in`,
    {
      method: 'POST',
      body: JSON.stringify(payload),
      authToken: options.authToken,
      signal: options.signal,
    },
  );
}

/**
 * Lists attendee roster items with tiered privacy masking.
 */
export async function listParticipants(
  orgId: string,
  eventId: string,
  params: { search?: string; status?: string; limit?: number; offset?: number } = {},
  options: StaffApiOptions = {},
): Promise<StaffParticipantRosterItemResponse[]> {
  const query = new URLSearchParams();
  if (params.search) query.set('search', params.search);
  if (params.status) query.set('status', params.status);
  if (params.limit) query.set('limit', String(params.limit));
  if (params.offset) query.set('offset', String(params.offset));

  const qs = query.toString();
  return apiClient<StaffParticipantRosterItemResponse[]>(
    `/api/v1/organizations/${encodeURIComponent(orgId)}/events/${encodeURIComponent(eventId)}/participants${qs ? `?${qs}` : ''}`,
    {
      method: 'GET',
      authToken: options.authToken,
      signal: options.signal,
    },
  );
}

/**
 * Reissues participant admission pass with manager authority.
 */
export async function reissueParticipantPass(
  orgId: string,
  eventId: string,
  participantId: string,
  reason: string,
  options: StaffApiOptions = {},
): Promise<IssuedPass> {
  return apiClient<IssuedPass>(
    `/api/v1/organizations/${encodeURIComponent(orgId)}/events/${encodeURIComponent(eventId)}/participants/${encodeURIComponent(participantId)}/reissue-pass`,
    {
      method: 'POST',
      body: JSON.stringify({ reason }),
      authToken: options.authToken,
      signal: options.signal,
    },
  );
}

/**
 * Verifies attendance arrival via pass code or participant ID.
 */
export async function performCheckIn(
  orgId: string,
  eventId: string,
  payload: CheckInRequest,
  options: StaffApiOptions = {},
): Promise<CheckInResponse> {
  return apiClient<CheckInResponse>(
    `/api/v1/organizations/${encodeURIComponent(orgId)}/events/${encodeURIComponent(eventId)}/check-ins`,
    {
      method: 'POST',
      body: JSON.stringify(payload),
      authToken: options.authToken,
      signal: options.signal,
    },
  );
}

/**
 * Searches candidates by name, token, reference, or student ID for desk check-in.
 */
export async function lookupCheckInCandidates(
  orgId: string,
  eventId: string,
  searchQuery: string,
  options: StaffApiOptions = {},
): Promise<CheckInLookupItemResponse[]> {
  const query = new URLSearchParams({ q: searchQuery });
  return apiClient<CheckInLookupItemResponse[]>(
    `/api/v1/organizations/${encodeURIComponent(orgId)}/events/${encodeURIComponent(eventId)}/check-in-lookup?${query.toString()}`,
    {
      method: 'GET',
      authToken: options.authToken,
      signal: options.signal,
    },
  );
}

/**
 * Voids an accidental check-in record (manager-only, requires >= 10 char reason).
 */
export async function voidCheckIn(
  orgId: string,
  eventId: string,
  checkInId: string,
  reason: string,
  options: StaffApiOptions = {},
): Promise<CheckInVoidResponse> {
  return apiClient<CheckInVoidResponse>(
    `/api/v1/organizations/${encodeURIComponent(orgId)}/events/${encodeURIComponent(eventId)}/check-ins/${encodeURIComponent(checkInId)}/void`,
    {
      method: 'POST',
      body: JSON.stringify({ reason }),
      authToken: options.authToken,
      signal: options.signal,
    },
  );
}

/**
 * Retrieves real-time attendance KPIs and breakdown.
 */
export async function getAttendanceSummary(
  orgId: string,
  eventId: string,
  options: StaffApiOptions = {},
): Promise<AttendanceSummaryResponse> {
  return apiClient<AttendanceSummaryResponse>(
    `/api/v1/organizations/${encodeURIComponent(orgId)}/events/${encodeURIComponent(eventId)}/attendance-summary`,
    {
      method: 'GET',
      authToken: options.authToken,
      signal: options.signal,
    },
  );
}

/**
 * Constructs the CSV export URL.
 */
export function getRosterExportUrl(orgId: string, eventId: string): string {
  const baseUrl = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/+$/, '') || '';
  return `${baseUrl}/api/v1/organizations/${encodeURIComponent(orgId)}/events/${encodeURIComponent(eventId)}/roster-export`;
}

