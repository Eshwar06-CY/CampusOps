/**
 * Pure TypeScript QR Code generator (Model 2).
 * Zero external dependencies. Generates accessible, scalable SVG vector QR codes.
 */

// Error correction levels
export type QrEccLevel = 'L' | 'M' | 'Q' | 'H';

// QR Code version parameters (data codewords and EC codewords per block for levels L, M, Q, H)
// Versions 1 to 6 covers up to 134 bytes, more than enough for 128-bit tokens and URLs.
interface VersionParam {
  version: number;
  size: number;
  alignment: number[];
  eccData: Record<QrEccLevel, { totalCodewords: number; ecCodewords: number; numBlocks: number }>;
}

const VERSION_PARAMS: VersionParam[] = [
  {
    version: 1,
    size: 21,
    alignment: [],
    eccData: {
      L: { totalCodewords: 26, ecCodewords: 7, numBlocks: 1 },
      M: { totalCodewords: 26, ecCodewords: 10, numBlocks: 1 },
      Q: { totalCodewords: 26, ecCodewords: 13, numBlocks: 1 },
      H: { totalCodewords: 26, ecCodewords: 17, numBlocks: 1 },
    },
  },
  {
    version: 2,
    size: 25,
    alignment: [18],
    eccData: {
      L: { totalCodewords: 44, ecCodewords: 10, numBlocks: 1 },
      M: { totalCodewords: 44, ecCodewords: 16, numBlocks: 1 },
      Q: { totalCodewords: 44, ecCodewords: 22, numBlocks: 1 },
      H: { totalCodewords: 44, ecCodewords: 28, numBlocks: 1 },
    },
  },
  {
    version: 3,
    size: 29,
    alignment: [22],
    eccData: {
      L: { totalCodewords: 70, ecCodewords: 15, numBlocks: 1 },
      M: { totalCodewords: 70, ecCodewords: 26, numBlocks: 1 },
      Q: { totalCodewords: 70, ecCodewords: 36, numBlocks: 2 },
      H: { totalCodewords: 70, ecCodewords: 44, numBlocks: 2 },
    },
  },
  {
    version: 4,
    size: 33,
    alignment: [26],
    eccData: {
      L: { totalCodewords: 100, ecCodewords: 20, numBlocks: 1 },
      M: { totalCodewords: 100, ecCodewords: 36, numBlocks: 2 },
      Q: { totalCodewords: 100, ecCodewords: 52, numBlocks: 2 },
      H: { totalCodewords: 100, ecCodewords: 64, numBlocks: 4 },
    },
  },
  {
    version: 5,
    size: 37,
    alignment: [30],
    eccData: {
      L: { totalCodewords: 134, ecCodewords: 26, numBlocks: 1 },
      M: { totalCodewords: 134, ecCodewords: 48, numBlocks: 2 },
      Q: { totalCodewords: 134, ecCodewords: 72, numBlocks: 2 },
      H: { totalCodewords: 134, ecCodewords: 88, numBlocks: 4 },
    },
  },
  {
    version: 6,
    size: 41,
    alignment: [34],
    eccData: {
      L: { totalCodewords: 172, ecCodewords: 36, numBlocks: 2 },
      M: { totalCodewords: 172, ecCodewords: 64, numBlocks: 4 },
      Q: { totalCodewords: 172, ecCodewords: 96, numBlocks: 4 },
      H: { totalCodewords: 172, ecCodewords: 112, numBlocks: 4 },
    },
  },
];

// Galois Field GF(256) arithmetic for Reed-Solomon coding
const GF_EXP = new Uint8Array(512);
const GF_LOG = new Uint8Array(256);

(() => {
  let val = 1;
  for (let i = 0; i < 255; i++) {
    GF_EXP[i] = val;
    GF_EXP[i + 255] = val;
    GF_LOG[val] = i;
    val = (val << 1) ^ (val & 128 ? 0x11d : 0);
  }
})();

function gfMul(x: number, y: number): number {
  if (x === 0 || y === 0) return 0;
  return GF_EXP[GF_LOG[x] + GF_LOG[y]];
}

function rsCompute(data: Uint8Array, ecLength: number): Uint8Array {
  // Generate generator polynomial
  const gen = new Uint8Array(ecLength + 1);
  gen[0] = 1;
  for (let i = 0; i < ecLength; i++) {
    const factor = GF_EXP[i];
    for (let j = i + 1; j > 0; j--) {
      gen[j] = gen[j] ^ gfMul(gen[j - 1], factor);
    }
  }

  const remainder = new Uint8Array(ecLength);
  for (let i = 0; i < data.length; i++) {
    const factor = data[i] ^ remainder[0];
    remainder.copyWithin(0, 1);
    remainder[ecLength - 1] = 0;
    for (let j = 0; j < ecLength; j++) {
      remainder[j] ^= gfMul(gen[j + 1], factor);
    }
  }
  return remainder;
}

// Format info bit strings with BCH(15,5) mask XOR 0x5412
const FORMAT_INFO: Record<QrEccLevel, number[]> = {
  L: [0x77c4, 0x72f3, 0x7daa, 0x789d, 0x662f, 0x6318, 0x6c41, 0x6976],
  M: [0x5412, 0x5125, 0x5e7c, 0x5b4b, 0x45f9, 0x40ce, 0x4f97, 0x4aa0],
  Q: [0x355f, 0x3068, 0x3f31, 0x3a06, 0x24b4, 0x2183, 0x2eda, 0x2bfd],
  H: [0x1689, 0x13be, 0x1ce7, 0x19d0, 0x0762, 0x0255, 0x0d0c, 0x083b],
};

/**
 * Creates bitstream from string in byte mode (8-bit)
 */
function encodeByteMode(text: string, capacityCodewords: number): Uint8Array {
  const encoder = new TextEncoder();
  const textBytes = encoder.encode(text);
  const bitArray: number[] = [];

  function pushBits(val: number, len: number) {
    for (let i = len - 1; i >= 0; i--) {
      bitArray.push((val >> i) & 1);
    }
  }

  // Mode: Byte (0100)
  pushBits(0b0100, 4);
  // Character count indicator (8 bits for versions 1-9)
  pushBits(textBytes.length, 8);

  // Data bits
  for (const b of textBytes) {
    pushBits(b, 8);
  }

  // Terminator (up to 4 zeroes)
  const capacityBits = capacityCodewords * 8;
  const rem = capacityBits - bitArray.length;
  pushBits(0, Math.min(4, Math.max(0, rem)));

  // Pad to byte boundary
  while (bitArray.length % 8 !== 0) {
    bitArray.push(0);
  }

  // Convert to bytes
  const bytes = new Uint8Array(capacityCodewords);
  let byteIdx = 0;
  for (let i = 0; i < bitArray.length; i += 8) {
    let b = 0;
    for (let j = 0; j < 8; j++) {
      b = (b << 1) | (bitArray[i + j] ?? 0);
    }
    bytes[byteIdx++] = b;
  }

  // Pad with alternating 0xEC, 0x11
  let padByte = 0xec;
  while (byteIdx < capacityCodewords) {
    bytes[byteIdx++] = padByte;
    padByte = padByte === 0xec ? 0x11 : 0xec;
  }

  return bytes;
}

export interface QrOptions {
  ecc?: QrEccLevel;
  size?: number;
  margin?: number;
  darkColor?: string;
  lightColor?: string;
  title?: string;
}

/**
 * Generates an SVG string representation of a QR Code for the given text.
 */
export function generateQrSvg(text: string, options: QrOptions = {}): string {
  const ecc: QrEccLevel = options.ecc || 'M';
  const margin = options.margin ?? 4;
  const darkColor = options.darkColor || '#0f172a';
  const lightColor = options.lightColor || '#ffffff';
  const title = options.title || 'QR Code Admission Pass';

  // Select appropriate version
  const textLen = new TextEncoder().encode(text).length;
  let selectedParam: VersionParam | null = null;

  for (const param of VERSION_PARAMS) {
    const dataCodewords = param.eccData[ecc].totalCodewords - param.eccData[ecc].ecCodewords;
    // Overhead: 4 mode bits + 8 count bits = 12 bits = 2 bytes approx
    if (textLen + 3 <= dataCodewords) {
      selectedParam = param;
      break;
    }
  }

  if (!selectedParam) {
    // Fall back to max version
    selectedParam = VERSION_PARAMS[VERSION_PARAMS.length - 1];
  }

  const { size, alignment, eccData } = selectedParam;
  const eccInfo = eccData[ecc];
  const dataCodewordsCount = eccInfo.totalCodewords - eccInfo.ecCodewords;

  // Encode data
  const dataBytes = encodeByteMode(text, dataCodewordsCount);
  const ecCodewordsPerBlock = Math.floor(eccInfo.ecCodewords / eccInfo.numBlocks);
  const dataCodewordsPerBlock = Math.floor(dataCodewordsCount / eccInfo.numBlocks);

  // Divide into blocks and compute Reed-Solomon codewords
  const dataBlocks: Uint8Array[] = [];
  const ecBlocks: Uint8Array[] = [];

  for (let b = 0; b < eccInfo.numBlocks; b++) {
    const start = b * dataCodewordsPerBlock;
    const blockData = dataBytes.slice(start, start + dataCodewordsPerBlock);
    dataBlocks.push(blockData);
    ecBlocks.push(rsCompute(blockData, ecCodewordsPerBlock));
  }

  // Interleave data and EC codewords
  const interleaved: number[] = [];
  for (let i = 0; i < dataCodewordsPerBlock; i++) {
    for (let b = 0; b < eccInfo.numBlocks; b++) {
      interleaved.push(dataBlocks[b][i]);
    }
  }
  for (let i = 0; i < ecCodewordsPerBlock; i++) {
    for (let b = 0; b < eccInfo.numBlocks; b++) {
      interleaved.push(ecBlocks[b][i]);
    }
  }

  // Create Matrix (size x size)
  // -1: unassigned, 0: light, 1: dark
  const matrix: number[][] = Array.from({ length: size }, () => Array(size).fill(-1));
  const isFunctionModule: boolean[][] = Array.from({ length: size }, () => Array(size).fill(false));

  function setFunction(r: number, c: number, val: number) {
    if (r >= 0 && r < size && c >= 0 && c < size) {
      matrix[r][c] = val;
      isFunctionModule[r][c] = true;
    }
  }

  // 1. Finder patterns at 3 corners
  function drawFinderPattern(row: number, col: number) {
    for (let r = -1; r <= 7; r++) {
      for (let c = -1; c <= 7; c++) {
        const nr = row + r;
        const nc = col + c;
        if (nr < 0 || nr >= size || nc < 0 || nc >= size) continue;
        if (
          (r >= 0 && r <= 6 && (c === 0 || c === 6)) ||
          (c >= 0 && c <= 6 && (r === 0 || r === 6)) ||
          (r >= 2 && r <= 4 && c >= 2 && c <= 4)
        ) {
          setFunction(nr, nc, 1);
        } else {
          setFunction(nr, nc, 0);
        }
      }
    }
  }

  drawFinderPattern(0, 0);
  drawFinderPattern(0, size - 7);
  drawFinderPattern(size - 7, 0);

  // 2. Timing patterns (drawn before alignment patterns to set function modules)
  for (let i = 8; i < size - 8; i++) {
    if (!isFunctionModule[6][i]) setFunction(6, i, i % 2 === 0 ? 1 : 0);
    if (!isFunctionModule[i][6]) setFunction(i, 6, i % 2 === 0 ? 1 : 0);
  }

  // 3. Alignment patterns
  if (alignment.length > 0) {
    for (const r of alignment) {
      for (const c of alignment) {
        if (isFunctionModule[r][c]) continue;
        for (let dr = -2; dr <= 2; dr++) {
          for (let dc = -2; dc <= 2; dc++) {
            const isDark = Math.max(Math.abs(dr), Math.abs(dc)) !== 1;
            setFunction(r + dr, c + dc, isDark ? 1 : 0);
          }
        }
      }
    }
  }

  // Dark module
  setFunction(size - 8, 8, 1);

  // Reserve format information areas
  for (let i = 0; i < 9; i++) {
    if (!isFunctionModule[8][i]) setFunction(8, i, 0);
    if (!isFunctionModule[i][8]) setFunction(i, 8, 0);
  }
  for (let i = size - 8; i < size; i++) {
    if (!isFunctionModule[8][i]) setFunction(8, i, 0);
    if (!isFunctionModule[i][8]) setFunction(i, 8, 0);
  }

  // Place data bits in zigzag order
  let bitIdx = 0;
  const totalBits = interleaved.length * 8;
  let dir = -1; // -1 = up, 1 = down
  let row = size - 1;
  let col = size - 1;

  while (col > 0) {
    if (col === 6) col--; // Skip vertical timing column
    for (let c = 0; c < 2; c++) {
      const curCol = col - c;
      if (!isFunctionModule[row][curCol]) {
        let bit = 0;
        if (bitIdx < totalBits) {
          const byteVal = interleaved[Math.floor(bitIdx / 8)];
          bit = (byteVal >> (7 - (bitIdx % 8))) & 1;
          bitIdx++;
        }
        matrix[row][curCol] = bit;
      }
    }
    row += dir;
    if (row < 0 || row >= size) {
      dir = -dir;
      row += dir;
      col -= 2;
    }
  }

  // Standard ISO/IEC 18004 Mask Evaluation across all 8 mask patterns
  const MASK_PATTERNS: Array<(r: number, c: number) => boolean> = [
    (r, c) => (r + c) % 2 === 0,
    (r, _c) => r % 2 === 0,
    (_r, c) => c % 3 === 0,
    (r, c) => (r + c) % 3 === 0,
    (r, c) => (Math.floor(r / 2) + Math.floor(c / 3)) % 2 === 0,
    (r, c) => ((r * c) % 2) + ((r * c) % 3) === 0,
    (r, c) => (((r * c) % 2) + ((r * c) % 3)) % 2 === 0,
    (r, c) => (((r + c) % 2) + ((r * c) % 3)) % 2 === 0,
  ];

  function applyFormatBits(grid: number[][], s: number, eccLevel: QrEccLevel, maskIdx: number) {
    const fmtBits = FORMAT_INFO[eccLevel][maskIdx];
    for (let i = 0; i < 15; i++) {
      // Top-left finder: Bit 14 (MSB) at (8, 0) down to Bit 0 (LSB) at (0, 8)
      const bit = (fmtBits >> (14 - i)) & 1;
      if (i < 6) grid[8][i] = bit;
      else if (i === 6) grid[8][7] = bit;
      else if (i === 7) grid[8][8] = bit;
      else if (i === 8) grid[7][8] = bit;
      else grid[14 - i][8] = bit;
    }
    for (let i = 0; i < 15; i++) {
      // Bottom-left finder (bits 0..6) and Top-right finder (bits 7..14)
      const bit = (fmtBits >> i) & 1;
      if (i < 7) {
        grid[s - 1 - i][8] = bit;
      } else {
        grid[8][s - 8 + (i - 7)] = bit;
      }
    }
  }

  function calculatePenalty(grid: number[][], s: number): number {
    let penalty = 0;

    // Feature 1: Runs of 5+ identical modules in row or column
    for (let r = 0; r < s; r++) {
      let runColor = grid[r][0];
      let runLen = 1;
      for (let c = 1; c < s; c++) {
        if (grid[r][c] === runColor) {
          runLen++;
        } else {
          if (runLen >= 5) penalty += 3 + (runLen - 5);
          runColor = grid[r][c];
          runLen = 1;
        }
      }
      if (runLen >= 5) penalty += 3 + (runLen - 5);
    }

    for (let c = 0; c < s; c++) {
      let runColor = grid[0][c];
      let runLen = 1;
      for (let r = 1; r < s; r++) {
        if (grid[r][c] === runColor) {
          runLen++;
        } else {
          if (runLen >= 5) penalty += 3 + (runLen - 5);
          runColor = grid[r][c];
          runLen = 1;
        }
      }
      if (runLen >= 5) penalty += 3 + (runLen - 5);
    }

    // Feature 2: 2x2 blocks of identical modules
    for (let r = 0; r < s - 1; r++) {
      for (let c = 0; c < s - 1; c++) {
        const color = grid[r][c];
        if (
          color === grid[r][c + 1] &&
          color === grid[r + 1][c] &&
          color === grid[r + 1][c + 1]
        ) {
          penalty += 3;
        }
      }
    }

    // Feature 3: Finder-like patterns (1:1:3:1:1 ratio with 4 light modules on either side)
    for (let r = 0; r < s; r++) {
      for (let c = 0; c <= s - 11; c++) {
        if (
          grid[r][c] === 1 && grid[r][c + 1] === 0 && grid[r][c + 2] === 1 &&
          grid[r][c + 3] === 1 && grid[r][c + 4] === 1 && grid[r][c + 5] === 0 &&
          grid[r][c + 6] === 1 && grid[r][c + 7] === 0 && grid[r][c + 8] === 0 &&
          grid[r][c + 9] === 0 && grid[r][c + 10] === 0
        ) {
          penalty += 40;
        }
        if (
          grid[r][c] === 0 && grid[r][c + 1] === 0 && grid[r][c + 2] === 0 &&
          grid[r][c + 3] === 0 && grid[r][c + 4] === 1 && grid[r][c + 5] === 0 &&
          grid[r][c + 6] === 1 && grid[r][c + 7] === 1 && grid[r][c + 8] === 1 &&
          grid[r][c + 9] === 0 && grid[r][c + 10] === 1
        ) {
          penalty += 40;
        }
      }
    }

    for (let c = 0; c < s; c++) {
      for (let r = 0; r <= s - 11; r++) {
        if (
          grid[r][c] === 1 && grid[r + 1][c] === 0 && grid[r + 2][c] === 1 &&
          grid[r + 3][c] === 1 && grid[r + 4][c] === 1 && grid[r + 5][c] === 0 &&
          grid[r + 6][c] === 1 && grid[r + 7][c] === 0 && grid[r + 8][c] === 0 &&
          grid[r + 9][c] === 0 && grid[r + 10][c] === 0
        ) {
          penalty += 40;
        }
        if (
          grid[r][c] === 0 && grid[r + 1][c] === 0 && grid[r + 2][c] === 0 &&
          grid[r + 3][c] === 0 && grid[r + 4][c] === 1 && grid[r + 5][c] === 0 &&
          grid[r + 6][c] === 1 && grid[r + 7][c] === 1 && grid[r + 8][c] === 1 &&
          grid[r + 9][c] === 0 && grid[r + 10][c] === 1
        ) {
          penalty += 40;
        }
      }
    }

    // Feature 4: Proportion of dark modules (deviation from 50%)
    let darkCount = 0;
    for (let r = 0; r < s; r++) {
      for (let c = 0; c < s; c++) {
        if (grid[r][c] === 1) darkCount++;
      }
    }
    const pct = (darkCount * 100) / (s * s);
    const k = Math.floor(Math.abs(pct - 50) / 5);
    penalty += k * 10;

    return penalty;
  }

  // Evaluate all 8 masks to find the one with the lowest ISO penalty score
  let bestMask = 0;
  let minPenalty = Infinity;

  for (let m = 0; m < 8; m++) {
    const testMatrix = matrix.map((rowArr) => [...rowArr]);
    const maskFn = MASK_PATTERNS[m];

    for (let r = 0; r < size; r++) {
      for (let c = 0; c < size; c++) {
        if (!isFunctionModule[r][c]) {
          if (maskFn(r, c)) {
            testMatrix[r][c] ^= 1;
          }
        }
      }
    }

    applyFormatBits(testMatrix, size, ecc, m);
    const penalty = calculatePenalty(testMatrix, size);
    if (penalty < minPenalty) {
      minPenalty = penalty;
      bestMask = m;
    }
  }

  // Apply the winning lowest-penalty mask to matrix
  const bestMaskFn = MASK_PATTERNS[bestMask];
  for (let r = 0; r < size; r++) {
    for (let c = 0; c < size; c++) {
      if (!isFunctionModule[r][c]) {
        if (bestMaskFn(r, c)) {
          matrix[r][c] ^= 1;
        }
      }
    }
  }
  applyFormatBits(matrix, size, ecc, bestMask);

  // Render SVG
  const totalDim = size + margin * 2;
  const paths: string[] = [];

  for (let r = 0; r < size; r++) {
    for (let c = 0; c < size; c++) {
      if (matrix[r][c] === 1) {
        paths.push(`M${c + margin},${r + margin}h1v1h-1z`);
      }
    }
  }

  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${totalDim} ${totalDim}" shape-rendering="crispEdges" role="img" aria-label="${title}">
  <title>${title}</title>
  <rect width="100%" height="100%" fill="${lightColor}"/>
  <path d="${paths.join('')}" fill="${darkColor}"/>
</svg>`;
}

