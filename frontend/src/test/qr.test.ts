import { describe, expect, it } from 'vitest';
import jsQR from 'jsqr';
import { generateQrSvg, type QrEccLevel } from '../utils/qr';

function decodeQrSvg(svg: string, scale = 4): string | null {
  const viewBoxMatch = svg.match(/viewBox="0 0 (\d+) (\d+)"/);
  if (!viewBoxMatch) return null;
  const dim = parseInt(viewBoxMatch[1], 10);

  const darkModules = new Set<string>();
  const pathMatches = svg.matchAll(/M(\d+),(\d+)h1v1h-1z/g);
  for (const match of pathMatches) {
    darkModules.add(`${match[1]},${match[2]}`);
  }

  const width = dim * scale;
  const height = dim * scale;
  const rgba = new Uint8ClampedArray(width * height * 4);

  for (let y = 0; y < height; y++) {
    const modY = Math.floor(y / scale);
    for (let x = 0; x < width; x++) {
      const modX = Math.floor(x / scale);
      const idx = (y * width + x) * 4;
      if (darkModules.has(`${modX},${modY}`)) {
        rgba[idx] = 0;
        rgba[idx + 1] = 0;
        rgba[idx + 2] = 0;
        rgba[idx + 3] = 255;
      } else {
        rgba[idx] = 255;
        rgba[idx + 1] = 255;
        rgba[idx + 2] = 255;
        rgba[idx + 3] = 255;
      }
    }
  }

  const code = jsQR(rgba, width, height);
  return code ? code.data : null;
}

describe('QR Code SVG Utility', () => {
  it('generates a valid SVG string for opaque pass codes', () => {
    const passCode = 'CO-PASS-8B1A2C3D4E5F6G7H8I9J0K1L2M3N4O5P';
    const svg = generateQrSvg(passCode, {
      title: 'Test Pass QR',
      ecc: 'M',
      margin: 2,
    });

    expect(svg).toContain('<svg');
    expect(svg).toContain('xmlns="http://www.w3.org/2000/svg"');
    expect(svg).toContain('viewBox=');
    expect(svg).toContain('aria-label="Test Pass QR"');
    expect(svg).toContain('<rect');
    expect(svg).toContain('<path');
    expect(svg).toContain('</svg>');
  });

  it('contains zero PII in the rendered SVG output', () => {
    const passCode = 'CO-PASS-8B1A2C3D4E5F6G7H8I9J0K1L2M3N4O5P';
    const svg = generateQrSvg(passCode);

    // Ensure common PII patterns are completely absent
    expect(svg).not.toContain('@');
    expect(svg).not.toContain('+91');
    expect(svg).not.toContain('student');
    expect(svg).not.toContain('Aarav');
    expect(svg).not.toContain('phone');
  });

  it('adjusts size according to margin and version parameters', () => {
    const shortCode = 'TKT-1234';
    const svg = generateQrSvg(shortCode, { margin: 4 });
    expect(svg).toContain('viewBox="0 0 29 29"'); // version 1 (21) + 2*4 = 29
  });

  describe('Independent QR Code Decoder Verification (jsQR 1.4.0)', () => {
    it('independently decodes standard opaque pass token at default ECC M', () => {
      const passToken = 'CO-PASS-8B1A2C3D4E5F6G7H8I9J0K1L2M3N4O5P';
      const svg = generateQrSvg(passToken, { ecc: 'M', margin: 4 });
      const decoded = decodeQrSvg(svg);
      expect(decoded).toBe(passToken);
    });

    it('verifies all supported error correction levels (L, M, Q, H)', () => {
      const token = 'CO-PASS-ECC-VERIFICATION-TOKEN-42';
      const eccLevels: QrEccLevel[] = ['L', 'M', 'Q', 'H'];

      for (const ecc of eccLevels) {
        const svg = generateQrSvg(token, { ecc, margin: 4 });
        const decoded = decodeQrSvg(svg);
        expect(decoded, `Failed decoding at ECC level ${ecc}`).toBe(token);
      }
    });

    it('decodes representative payload lengths from short tickets to long tokens', () => {
      const payloads = [
        'TKT-101',                                                  // Short (Version 1)
        'CO-PASS-8B1A2C3D',                                         // 16 chars
        'CO-PASS-8B1A2C3D4E5F6G7H8I9J0K1L2M3N4O5P',                 // 39 chars standard
        'CO-PASS-LONG-PAYLOAD-WITH-ALPHANUMERIC-1234567890-ABCDEF',  // 56 chars
        'CO-PASS-MAX-CAPACITY-TEST-STRING-9876543210-XYZ-LMNOPQRST',// 57 chars
      ];

      for (const payload of payloads) {
        const svg = generateQrSvg(payload, { ecc: 'M', margin: 4 });
        const decoded = decodeQrSvg(svg);
        expect(decoded, `Failed decoding payload '${payload}'`).toBe(payload);
      }
    });

    it('decodes payloads containing diverse ASCII characters', () => {
      const mixedPayload = 'CO-PASS:uuid_1234-abcd.EFGH~5678';
      const svg = generateQrSvg(mixedPayload, { ecc: 'M', margin: 4 });
      const decoded = decodeQrSvg(svg);
      expect(decoded).toBe(mixedPayload);
    });

    it('gracefully returns null when decoding blank or malformed SVG images', () => {
      // 1. Completely blank SVG
      const blankSvg = '<svg viewBox="0 0 29 29"><rect width="100%" height="100%" fill="#ffffff"/></svg>';
      expect(decodeQrSvg(blankSvg)).toBeNull();

      // 2. Corrupted SVG with random module noise (no finder patterns)
      const noiseSvg = '<svg viewBox="0 0 29 29"><rect width="100%" height="100%" fill="#ffffff"/><path d="M5,5h1v1h-1zM10,10h1v1h-1z" fill="#000000"/></svg>';
      expect(decodeQrSvg(noiseSvg)).toBeNull();

      // 3. Invalid SVG string
      expect(decodeQrSvg('not-an-svg')).toBeNull();
    });
  });
});

