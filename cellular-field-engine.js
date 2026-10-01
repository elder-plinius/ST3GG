(function (root) {
'use strict';
/**
 * Cellular Field · a small, inspectable Critters engine, adapted from JANUS.
 * Rule: Toffoli & Margolus, Cellular Automata Machines (1987), §12.8.2.
 * https://people.csail.mit.edu/nhm/cam-book.pdf (printed pp. 132–134)
 *
 * The world stores ONLY the current cells, dimensions and signed step.
 * No frame history, saved original bitmap, RNG, or reverse-time lookup.
 * An optional originDigest is inert comparison metadata, never read by a step.
 */
const FORMAT = 'janus-state-v1';
const RULE = 'critters-margolus-v1';
const MAX_CELLS = 1048576;
const MAX_DIMENSION = 1024;
const MAX_BATCH_STEPS = 1000000;

// Bit positions: top-left=1, top-right=2, bottom-left=4, bottom-right=8.
// Exactly two live cells: unchanged. Otherwise complement; additionally rotate
// by 180 degrees when the INPUT block contains exactly three live cells.
const popcount = n => (n & 1) + ((n >> 1) & 1) + ((n >> 2) & 1) + ((n >> 3) & 1);
const rotate180 = n => ((n & 1) << 3) | ((n & 2) << 1) | ((n & 4) >> 1) | ((n & 8) >> 3);
const ruleTable = Array.from({ length: 16 }, (_, n) => {
  const count = popcount(n);
  return count === 2 ? n : count === 3 ? rotate180(n ^ 15) : n ^ 15;
});
const inverseTable = new Array(16);
for (let n = 0; n < 16; n++) inverseTable[ruleTable[n]] = n;
// Frozen normal arrays prevent callers changing the dynamics globally.
const FORWARD_RULE = Object.freeze(ruleTable);
const INVERSE_RULE = Object.freeze(inverseTable);

function dimensions(width, height) {
  if (!Number.isInteger(width) || !Number.isInteger(height) || width < 2 || height < 2 ||
      width % 2 || height % 2 || width > MAX_DIMENSION || height > MAX_DIMENSION ||
      width * height > MAX_CELLS) {
    throw new RangeError('Dimensions must be even integers from 2 to 1024, at most 1048576 cells.');
  }
}

function validateCells(cells, length) {
  if (!(cells instanceof Uint8Array) || cells.length !== length) {
    throw new TypeError('Cells must be a Uint8Array of width × height entries.');
  }
  for (let i = 0; i < length; i++) if (cells[i] > 1) throw new TypeError('Every cell must be 0 or 1.');
}

function validateWorld(world, exhaustive = false) {
  if (!world || typeof world !== 'object') throw new TypeError('Expected a world.');
  dimensions(world.width, world.height);
  if (!(world.cells instanceof Uint8Array) || world.cells.length !== world.width * world.height) {
    throw new TypeError('Invalid world cells.');
  }
  if (!Number.isSafeInteger(world.step)) throw new RangeError('Step must be a safe integer.');
  if (exhaustive) validateCells(world.cells, world.width * world.height);
}

function createWorld(width, height, cells) {
  dimensions(width, height);
  if (cells === undefined) cells = new Uint8Array(width * height);
  validateCells(cells, width * height);
  return { width, height, step: 0, cells: cells.slice() };
}

function validateBatch(world, count, direction) {
  validateWorld(world, true);
  if (!Number.isSafeInteger(count) || count < 0 || count > MAX_BATCH_STEPS) {
    throw new RangeError('Step count must be an integer from 0 to 1000000.');
  }
  if (!Number.isSafeInteger(world.step + direction * count)) throw new RangeError('Step would exceed safe integer range.');
}

// Each partition consists of disjoint blocks: updating in place is exact.
// Odd partitions wrap their rightmost column and bottom row around the torus.
function partition(world, phase, table) {
  const { width, height, cells } = world;
  for (let y = phase; y < height; y += 2) {
    const top = y * width;
    const bottom = ((y + 1) % height) * width;
    for (let x = phase; x < width; x += 2) {
      const nextX = (x + 1) % width;
      const a = top + x, b = top + nextX, c = bottom + x, d = bottom + nextX;
      const out = table[cells[a] | (cells[b] << 1) | (cells[c] << 2) | (cells[d] << 3)];
      cells[a] = out & 1;
      cells[b] = (out >> 1) & 1;
      cells[c] = (out >> 2) & 1;
      cells[d] = (out >> 3) & 1;
    }
  }
}

function forward(world, count = 1) {
  validateBatch(world, count, 1);
  for (let i = 0; i < count; i++) {
    partition(world, world.step & 1, FORWARD_RULE);
    world.step++;
  }
  return world;
}

function backward(world, count = 1) {
  validateBatch(world, count, -1);
  for (let i = 0; i < count; i++) {
    world.step--;
    partition(world, world.step & 1, INVERSE_RULE);
  }
  return world;
}

function flip(world, index) {
  validateWorld(world, true);
  if (!Number.isInteger(index) || index < 0 || index >= world.cells.length) throw new RangeError('Cell index out of bounds.');
  world.cells[index] ^= 1;
  return world;
}

// Critters flips the empty background on every step. This DISPLAY convention
// cancels that flash while keeping raw dynamics and exported states untouched.
function displayCell(world, index) {
  return world.cells[index] ^ (world.step & 1);
}

function exportState(world, originDigest = world.originDigest) {
  validateWorld(world, true);
  if (originDigest !== undefined && (typeof originDigest !== 'string' || !/^[a-f0-9]{64}$/.test(originDigest))) {
    throw new TypeError('Optional originDigest must be 64 lowercase SHA-256 hex characters.');
  }
  const pieces = new Array(world.cells.length / 4);
  for (let i = 0; i < world.cells.length; i += 4) {
    pieces[i / 4] = (world.cells[i] * 8 + world.cells[i + 1] * 4 + world.cells[i + 2] * 2 + world.cells[i + 3]).toString(16);
  }
  const state = {
    format: FORMAT, rule: RULE, width: world.width, height: world.height,
    step: world.step, encoding: 'hex-nibbles-msb', cells: pieces.join('')
  };
  if (originDigest !== undefined) state.originDigest = originDigest;
  return state;
}

function importState(input) {
  if (typeof input === 'string' && input.length > MAX_CELLS / 4 + 2048) throw new RangeError('State file is too large.');
  const state = typeof input === 'string' ? JSON.parse(input) : input;
  if (!state || typeof state !== 'object' || Array.isArray(state)) throw new TypeError('Expected a state object.');
  const allowed = new Set(['format', 'rule', 'width', 'height', 'step', 'encoding', 'cells', 'originDigest']);
  for (const key of Object.keys(state)) if (!allowed.has(key)) throw new TypeError(`Unrecognized state field: ${key}`);
  if (state.format !== FORMAT || state.rule !== RULE || state.encoding !== 'hex-nibbles-msb') {
    throw new TypeError('Unsupported JANUS format, rule, or encoding.');
  }
  dimensions(state.width, state.height);
  if (!Number.isSafeInteger(state.step)) throw new RangeError('Step must be a safe integer.');
  if (typeof state.cells !== 'string' || state.cells.length !== state.width * state.height / 4 || !/^[a-f0-9]+$/.test(state.cells)) {
    throw new TypeError('Invalid packed binary cell data.');
  }
  if (state.originDigest !== undefined && (typeof state.originDigest !== 'string' || !/^[a-f0-9]{64}$/.test(state.originDigest))) {
    throw new TypeError('Invalid origin digest.');
  }
  const cells = new Uint8Array(state.width * state.height);
  for (let i = 0; i < state.cells.length; i++) {
    const nibble = parseInt(state.cells[i], 16);
    for (let b = 0; b < 4; b++) cells[i * 4 + b] = (nibble >> (3 - b)) & 1;
  }
  const world = { width: state.width, height: state.height, step: state.step, cells };
  if (state.originDigest !== undefined) world.originDigest = state.originDigest;
  return world;
}

// Comparison helper. Exact comparison is useful when independently retained
// fixture data exists; this is not needed or called by the inverse dynamics.
function hammingDistance(a, b) {
  if (!(a instanceof Uint8Array) || !(b instanceof Uint8Array) || a.length !== b.length) throw new TypeError('Expected equally sized Uint8Arrays.');
  let changed = 0;
  for (let i = 0; i < a.length; i++) if (a[i] !== b[i]) changed++;
  return changed;
}

const api = Object.freeze({ FORMAT, RULE, MAX_CELLS, MAX_DIMENSION, MAX_BATCH_STEPS, FORWARD_RULE, INVERSE_RULE, createWorld, forward, backward, flip, displayCell, exportState, importState, hammingDistance });
if (typeof module !== 'undefined' && module.exports) module.exports = api;
else root.CellularFieldEngine = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
