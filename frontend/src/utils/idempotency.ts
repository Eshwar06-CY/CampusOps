/**
 * Idempotency Key Management for CampusOps Registration & Check-In.
 *
 * Rules:
 * - Generates high-entropy client-side idempotency keys.
 * - On network/transient failures, re-submitting the identical payload preserves the SAME key.
 * - If form data changes materially, a NEW idempotency key must be generated.
 */

export function generateIdempotencyKey(prefix = 'idemp'): string {
  const randomBytes = new Uint8Array(16);
  if (typeof crypto !== 'undefined' && crypto.getRandomValues) {
    crypto.getRandomValues(randomBytes);
  } else {
    for (let i = 0; i < 16; i++) {
      randomBytes[i] = Math.floor(Math.random() * 256);
    }
  }
  const hex = Array.from(randomBytes)
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('');
  return `${prefix}_${hex}`;
}

/**
 * Creates a deterministic fingerprint of a registration payload
 * to detect material changes.
 */
export function createPayloadFingerprint(payload: unknown): string {
  try {
    return JSON.stringify(payload);
  } catch {
    return String(Date.now());
  }
}

