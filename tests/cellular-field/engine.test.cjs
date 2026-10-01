const test = require('node:test');
const assert = require('node:assert/strict');
const { spawnSync } = require('node:child_process');
const {
  createWorld, forward, backward, flip, exportState, importState, displayCell,
  hammingDistance, FORWARD_RULE, INVERSE_RULE, MAX_BATCH_STEPS
} = require('../../cellular-field-engine.js');
const { randomCells, textCells } = require('./fixtures.cjs');

// An independent out-of-place reference: explicit 4-cell lists, coordinate
// modular arithmetic, and logic rather than the production lookup table.
function referenceStep(cells, width, height, step, reverse = false) {
  const output = cells.slice();
  const phase = ((step % 2) + 2) % 2;
  for (let by = 0; by < height / 2; by++) for (let bx = 0; bx < width / 2; bx++) {
    const points = [[0, 0], [1, 0], [0, 1], [1, 1]].map(([x, y]) =>
      ((2 * by + phase + y) % height) * width + ((2 * bx + phase + x) % width));
    let values = points.map(p => cells[p]);
    const population = values.reduce((a, b) => a + b, 0);
    if (population !== 2) {
      values = values.map(v => 1 - v);
      if (population === (reverse ? 1 : 3)) values.reverse();
    }
    points.forEach((p, i) => { output[p] = values[i]; });
  }
  return output;
}

test('all 16 block patterns follow the documented Critters rule and inverse', () => {
  const expected = [15,14,13,3,11,5,6,1,7,9,10,2,12,4,8,0];
  assert.deepEqual(FORWARD_RULE, expected);
  assert.equal(new Set(FORWARD_RULE).size, 16);
  for (let pattern = 0; pattern < 16; pattern++) {
    const cells = Uint8Array.from({ length: 4 }, (_, b) => (pattern >> b) & 1);
    const world = createWorld(2, 2, cells);
    forward(world);
    assert.deepEqual([...world.cells], Array.from({ length: 4 }, (_, b) => (expected[pattern] >> b) & 1));
    assert.equal(INVERSE_RULE[FORWARD_RULE[pattern]], pattern);
    backward(world);
    assert.deepEqual(world.cells, cells);
  }
});

test('all 65536 binary 4×4 inputs agree with independent reference for both phases and reverse', () => {
  for (let pattern = 0; pattern < 65536; pattern++) {
    const cells = Uint8Array.from({ length: 16 }, (_, b) => (pattern >> b) & 1);
    const world = createWorld(4, 4, cells);
    let reference = cells;
    for (let step = 0; step < 3; step++) {
      reference = referenceStep(reference, 4, 4, step);
      forward(world);
      assert.deepEqual(world.cells, reference);
    }
    for (let step = 2; step >= 0; step--) {
      reference = referenceStep(reference, 4, 4, step, true);
      backward(world);
      assert.deepEqual(world.cells, reference);
    }
    assert.deepEqual(world.cells, cells);
    assert.equal(world.step, 0);
  }
});

test('arbitrary rectangular inputs recover across odd, even, zero, and negative times', () => {
  for (const [width, height] of [[2,2],[2,18],[18,2],[6,10],[32,48],[192,192]]) {
    for (const count of [0,1,2,3,16,127,256,513]) {
      const cells = randomCells(width, height, count + width);
      const world = createWorld(width, height, cells);
      forward(world, count); backward(world, count);
      assert.equal(hammingDistance(cells, world.cells), 0);
      backward(world, count); forward(world, count);
      assert.equal(hammingDistance(cells, world.cells), 0);
      assert.equal(world.step, 0);
    }
  }
});

test('odd partition wraps horizontally, vertically and at the bottom-right corner', () => {
  const width = 6, height = 4;
  const cells = new Uint8Array(width * height);
  cells[width * height - 1] = 1; cells[0] = 1; cells[width - 1] = 1;
  const world = createWorld(width, height, cells);
  world.step = 1;
  const expected = referenceStep(cells, width, height, 1);
  forward(world);
  assert.deepEqual(world.cells, expected);
  // One block crosses BOTH boundaries: [23,18,5,0] began [1,0,1,1].
  assert.deepEqual([23,18,5,0].map(i => world.cells[i]), [0,0,1,0]);
  backward(world);
  assert.deepEqual(world.cells, cells);
});

test('export/import preserves packed raw state, signed phase and inert digest', () => {
  const original = randomCells(192, 192);
  const world = createWorld(192, 192, original);
  forward(world, 513);
  const digest = 'a'.repeat(64), exported = exportState(world, digest);
  assert.deepEqual(Object.keys(exported), ['format','rule','width','height','step','encoding','cells','originDigest']);
  assert.equal(exported.cells.length, 192 * 192 / 4);
  const fresh = importState(JSON.stringify(exported));
  assert.notEqual(fresh.cells, world.cells);
  assert.equal(fresh.originDigest, digest);
  backward(fresh, 513);
  assert.equal(hammingDistance(fresh.cells, original), 0);
  assert.equal(world.step, 513);
  const noDigest = importState(exportState(world));
  assert.deepEqual(Object.keys(noDigest), ['width','height','step','cells']);
  backward(noDigest, 513);
  assert.deepEqual(noDigest.cells, original);
  backward(world, 700);
  const negative = importState(exportState(world));
  forward(negative, 187);
  assert.deepEqual(negative.cells, original);
});

test('a separate fresh Node process reverses exported state without original or frame history', () => {
  const original = randomCells(64, 48, 4582);
  const world = createWorld(64, 48, original);
  forward(world, 129);
  const child = spawnSync(process.execPath, ['-e',
    'const {readFileSync}=require("node:fs"); const {importState,backward}=require("../../cellular-field-engine.js"); const w=importState(readFileSync(0,"utf8")); backward(w,w.step); process.stdout.write(Buffer.from(w.cells));'
  ], { cwd: __dirname, input: JSON.stringify(exportState(world)) });
  assert.equal(child.status, 0, child.stderr.toString());
  assert.deepEqual(new Uint8Array(child.stdout), original);
});

test('one flipped evolved cell remains a distinct predecessor, and two flips restore control', () => {
  const original = randomCells(192, 192);
  const world = createWorld(192, 192, original);
  forward(world, 513);
  const clean = importState(exportState(world)), perturbed = importState(exportState(world));
  flip(perturbed, 18528);
  assert.equal(hammingDistance(clean.cells, perturbed.cells), 1);
  backward(clean, 513); backward(perturbed, 513);
  assert.equal(hammingDistance(original, clean.cells), 0);
  assert.equal(hammingDistance(original, perturbed.cells), 18527);
  flip(world, 0); flip(world, 0); backward(world, 513);
  assert.deepEqual(world.cells, original);
});

test('typographic fixture recovers exactly and display parity does not touch raw state', () => {
  const original = textCells();
  const world = createWorld(192, 192, original);
  forward(world, 193);
  const before = world.cells.slice();
  for (let i = 0; i < before.length; i++) assert.equal(displayCell(world, i), 1 - before[i]);
  assert.deepEqual(world.cells, before);
  backward(world, 193);
  assert.deepEqual(world.cells, original);
});

test('creation copies caller data and state carries no snapshot', () => {
  const cells = new Uint8Array(16);
  const world = createWorld(4, 4, cells);
  cells[0] = 1;
  assert.equal(world.cells[0], 0);
  forward(world, 100);
  assert.deepEqual(Object.keys(world), ['width','height','step','cells']);
  assert.equal(world.cells.byteLength, 16);
});

test('invalid dimensions, binary cells, counts, overflow and cell indexes are rejected before mutation', () => {
  for (const [w,h] of [[0,2],[3,4],[4,3],[1026,2],[2,Infinity],[2,NaN],[4.5,4],[-2,2]]) assert.throws(() => createWorld(w,h));
  assert.throws(() => createWorld(2,2,[0,0,0,0]));
  assert.throws(() => createWorld(2,2,new Uint8Array(3)));
  assert.throws(() => createWorld(2,2,new Uint8Array([0,0,0,2])));
  const world = createWorld(4,4);
  for (const count of [-1,0.5,NaN,Infinity,MAX_BATCH_STEPS+1,'1']) {
    assert.throws(() => forward(world,count));
    assert.throws(() => backward(world,count));
  }
  for (const index of [-1,16,1.5,NaN,'1']) assert.throws(() => flip(world,index));
  assert.equal(world.step,0);
  assert.deepEqual(world.cells,new Uint8Array(16));
  world.step = Number.MAX_SAFE_INTEGER; assert.throws(() => forward(world,1));
  world.step = Number.MIN_SAFE_INTEGER; assert.throws(() => backward(world,1));
  world.step = 0; world.cells[0] = 2; assert.throws(() => forward(world));
});

test('import rejects malformed, ambiguous, oversized and hidden-data states', () => {
  const valid = exportState(createWorld(4,4));
  for (const value of [null,[],1,'null','{',JSON.stringify(valid)+'x']) assert.throws(() => importState(value));
  for (const changes of [
    {format:'old'}, {rule:'other'}, {encoding:'bits'}, {step:0.1}, {step:1e100},
    {width:3}, {height:0}, {cells:'000'}, {cells:'00000'}, {cells:'000g'},
    {cells:[0,0,0,0]}, {cells:'000A'}, {original:'hidden bitmap'}, {frames:[]},
    {originDigest:'x'}, {originDigest:17}
  ]) assert.throws(() => importState({...valid,...changes}));
  assert.throws(() => importState(' '.repeat(1048576)));
  assert.throws(() => exportState(createWorld(4,4),'invalid'));
});
