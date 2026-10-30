/**
 * Public Participant Registration & Ticketing API Client.
 *
 * Implements the approved Slice 5C public routes with URL credential protection
 * (POST body endpoints for passes/verify, registrations/lookup, registrations/cancel).
 */

import { apiClient } from './client';
import type {
  PublicEventDetails,
  PublicRegistrationRequest,
  PublicRegistrationResponse,
  PublicPassVerifyResponse,
  PublicRegistrationLookupResponse,
  PublicRegistrationCancelRequest,
  PublicRegistrationCancelResponse,
} from './types';

/**
 * Retrieves public event details, format, capacity availability, and registration status.
 */
export async function getPublicEventDetails(
  registrationKey: string,
  signal?: AbortSignal,
): Promise<PublicEventDetails> {
  return apiClient<PublicEventDetails>(`/api/v1/public/events/${encodeURIComponent(registrationKey)}`, {
    method: 'GET',
    signal,
  });
}

/**
 * Submits self-service native registration (solo or team).
 */
export async function submitPublicRegistration(
  registrationKey: string,
  payload: PublicRegistrationRequest,
): Promise<PublicRegistrationResponse> {
  return apiClient<PublicRegistrationResponse>(
    `/api/v1/public/events/${encodeURIComponent(registrationKey)}/registrations`,
    {
      method: 'POST',
      body: JSON.stringify(payload),
    },
  );
}

/**
 * Verifies and fetches admission pass details using secure POST body.
 * Prevents bearer pass token leakage into browser history, proxy logs, and referer headers.
 */
export async function verifyPass(
  registrationKey: string,
  passCode: string,
): Promise<PublicPassVerifyResponse> {
  return apiClient<PublicPassVerifyResponse>(
    `/api/v1/public/events/${encodeURIComponent(registrationKey)}/passes/verify`,
    {
      method: 'POST',
      body: JSON.stringify({ pass_code: passCode }),
    },
  );
}

/**
 * Looks up registration details using capability confirmation code in POST body.
 */
export async function lookupRegistration(
  registrationKey: string,
  confirmationCode: string,
): Promise<PublicRegistrationLookupResponse> {
  return apiClient<PublicRegistrationLookupResponse>(
    `/api/v1/public/events/${encodeURIComponent(registrationKey)}/registrations/lookup`,
    {
      method: 'POST',
      body: JSON.stringify({ confirmation_code: confirmationCode }),
    },
  );
}

/**
 * Self-service registration cancellation using POST body.
 */
export async function cancelRegistration(
  registrationKey: string,
  payload: PublicRegistrationCancelRequest,
): Promise<PublicRegistrationCancelResponse> {
  return apiClient<PublicRegistrationCancelResponse>(
    `/api/v1/public/events/${encodeURIComponent(registrationKey)}/registrations/cancel`,
    {
      method: 'POST',
      body: JSON.stringify(payload),
    },
  );
}

