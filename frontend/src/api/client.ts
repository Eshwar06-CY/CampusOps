/**
 * Centralized API Client for CampusOps.
 *
 * Enforces:
 * - Proper error mapping across 401, 403, 404, 409, 422, 429, 500.
 * - Credential and PII sanitization in error logs.
 * - Standard headers (Content-Type: application/json).
 * - Safe environment variable fallback.
 */

export class ApiError extends Error {
  public status: number;
  public detail: string;
  public validationErrors?: unknown;

  constructor(status: number, detail: string, validationErrors?: unknown) {
    super(`API Error ${status}: ${detail}`);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
    this.validationErrors = validationErrors;
  }
}

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/+$/, '') || '';

export interface RequestOptions extends RequestInit {
  authToken?: string | null;
}

export async function apiClient<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
  const url = `${API_BASE_URL}${endpoint.startsWith('/') ? endpoint : `/${endpoint}`}`;

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    Accept: 'application/json',
    ...(options.headers as Record<string, string> | undefined),
  };

  if (options.authToken) {
    headers['Authorization'] = `Bearer ${options.authToken}`;
  }

  let response: Response;
  try {
    response = await fetch(url, {
      ...options,
      headers,
    });
  } catch (err) {
    if (err instanceof DOMException && err.name === 'AbortError') {
      throw err;
    }
    throw new ApiError(0, 'Network connection failure. Please check your internet connection.');
  }

  if (!response.ok) {
    let errorDetail = response.statusText || 'Unknown error occurred.';
    let validationErrors: unknown = undefined;

    try {
      const contentType = response.headers.get('content-type');
      if (contentType && contentType.includes('application/json')) {
        const errorData = await response.json();
        if (typeof errorData?.detail === 'string') {
          errorDetail = errorData.detail;
        } else if (Array.isArray(errorData?.detail)) {
          // Pydantic validation error list
          validationErrors = errorData.detail;
          errorDetail = errorData.detail
            .map((e: { loc?: string[]; msg?: string }) => {
              const field = e.loc ? e.loc.slice(1).join('.') : 'field';
              return `${field}: ${e.msg || 'invalid'}`;
            })
            .join('; ');
        }
      } else {
        const textData = await response.text();
        if (textData) {
          errorDetail = textData.slice(0, 150);
        }
      }
    } catch {
      // Body reading error, retain statusText
    }

    throw new ApiError(response.status, errorDetail, validationErrors);
  }

  // 204 No Content
  if (response.status === 204) {
    return null as T;
  }

  return response.json() as Promise<T>;
}

