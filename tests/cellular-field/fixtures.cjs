// Deterministic test fixtures. These are retained by the tests, not the engine.
function randomCells(width, height, seed = 12345) {
  let state = seed | 0;
  return Uint8Array.from({ length: width * height }, () => {
    state ^= state << 13; state ^= state >>> 17; state ^= state << 5;
    return state & 1;
  });
}

function textCells(width = 192, height = 192) {
  const letters = {
    J: ['11111','00010','00010','00010','10010','10010','01100'],
    A: ['01110','10001','10001','11111','10001','10001','10001'],
    N: ['10001','11001','11001','10101','10011','10011','10001'],
    U: ['10001','10001','10001','10001','10001','10001','01110'],
    S: ['01111','10000','10000','01110','00001','00001','11110']
  };
  const word = 'JANUS', scale = Math.floor(width / 36);
  const left = Math.floor((width - (word.length * 6 - 1) * scale) / 2);
  const top = Math.floor((height - 7 * scale) / 2);
  const cells = new Uint8Array(width * height);
  for (let letter = 0; letter < word.length; letter++) {
    const rows = letters[word[letter]];
    for (let y = 0; y < 7; y++) for (let x = 0; x < 5; x++) {
      if (rows[y][x] === '1') for (let py = 0; py < scale; py++) for (let px = 0; px < scale; px++) {
        cells[(top + y * scale + py) * width + left + (letter * 6 + x) * scale + px] = 1;
      }
    }
  }
  return cells;
}

module.exports = { randomCells, textCells };
