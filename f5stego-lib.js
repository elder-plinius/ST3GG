/*	This software is licensed under the MIT License.

	Copyright (c) 2016 desudesutalk

	Permission is hereby granted, free of charge, to any person obtaining a copy of
	this software and associated documentation files (the "Software"), to deal in
	the Software without restriction, including without limitation the rights to
	use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
	the Software, and to permit persons to whom the Software is furnished to do so,
	subject to the following conditions:

	The above copyright notice and this permission notice shall be included in all
	copies or substantial portions of the Software.

	THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
	IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
	FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
	COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
	IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
	CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

	https://github.com/desudesutalk/f5stegojs

	This library is based on https://github.com/owencm/js-steg by Owen Campbell-
	Moore. Decoder and encoder was optimized for speed, F5 algorithm and metadata
	manipulation utils was added to library.

	Original code was released under MIT and Apache licenses, so here follows
	original licenses of Owen code:

	jpeg decoder license:

	Modified JPEG decoder for Steganography by Owen Campbell-Moore, based on one
	released by Adobe.

	Copyright 2011 notmasteryet

	Licensed under the Apache License, Version 2.0 (the "License"); you may not use
	this file except in compliance with the License. You may obtain a copy of the
	License at

	http://www.apache.org/licenses/LICENSE-2.0

	Unless required by applicable law or agreed to in writing, software distributed
	under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
	CONDITIONS OF ANY KIND, either express or implied. See the License for the
	specific language governing permissions and limitations under the License.


	jpeg encoder license:

	JPEG encoder ported to JavaScript, optimized by Andreas Ritter
	(www.bytestrom.eu, 11/2009) and made suitable for steganography by Owen
	Campbell-Moore (www.owencampbellmoore.com, 03/13)

	Based on v 0.9a

	Licensed under the MIT License

	Copyright (c) 2009 Andreas Ritter

	Permission is hereby granted, free of charge, to any person obtaining a copy of
	this software and associated documentation files (the "Software"), to deal in
	the Software without restriction, including without limitation the rights to
	use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
	the Software, and to permit persons to whom the Software is furnished to do so,
	subject to the following conditions:

	The above copyright notice and this permission notice shall be included in all
	copies or substantial portions of the Software.

	THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
	IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
	FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
	COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
	IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
	CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

	Copyright (c) 2008, Adobe Systems Incorporated All rights reserved.

	Redistribution and use in source and binary forms, with or without modification,
	are permitted provided that the following conditions are met:

	Redistributions of source code must retain the above copyright notice, this list
	of conditions and the following disclaimer.

	Redistributions in binary form must reproduce the above copyright notice, this
	list of conditions and the following disclaimer in the documentation and/or
	other materials provided with the distribution.

	Neither the name of Adobe Systems Incorporated nor the names of its contributors
	may be used to endorse or promote products derived from this software without
	specific prior written permission.

	THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
	ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
	WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
	DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
	ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
	(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
	LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
	ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
	(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
	SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
	*/

/* global define, module, exports */
/* jshint sub:true */
;(function(root, factory) {
	'use strict';
	if (typeof define === 'function' && define.amd) {
		define([], factory);
	} else if (typeof exports === 'object') {
		module.exports = factory();
	} else {
		root.f5stego = factory();
	}
}(this, function() {
	'use strict';

	var f5stego = function(key, maxPixels) {
		this.maxPixels = maxPixels || 4096 * 4096;
		this.shuffleInit(key);
	};

	// Shuffle used in f5 algo
	// ===========================================================================================================
		f5stego.prototype.shuffleInit = function(key) {
			this.randPool = new ArrayBuffer(this.maxPixels * 4.125);

			if (!key.length) throw 'key needed';

			var i = 0,
				j = 0,
				t = 0,
				k = 0,
				S = new Uint8Array(256),
				rnd = new Uint8Array(this.randPool);

			// init state from key
			for (i = 0; i < 256; ++i) S[i] = i;

			for (i = 0; i < 256; ++i) {
				j = (j + S[i] + key[i % key.length]) & 255;
				t = S[i];
				S[i] = S[j];
				S[j] = t;
			}
			i = 0;
			j = 0;

			// shuffle data
			for (k = 0; k < this.maxPixels * 4.125; ++k) {
				i = (i + 1) & 255;
				j = (j + S[i]) & 255;
				t = S[i];
				S[i] = S[j];
				S[j] = t;
				rnd[k] = S[(t + S[i]) & 255];
			}
		};

		f5stego.prototype.stegShuffle = function(pm) {
			var t, l, k, random_index,
				rand32Array = new Uint32Array(this.randPool);

			if (typeof pm == 'number') {
				l = pm;
				pm = new Uint32Array(l);
				for (k = 1; k < l; k++) {
					random_index = rand32Array[k] % (k + 1);
					if (random_index != k) pm[k] = pm[random_index];
					pm[random_index] = k;
				}
			} else {
				l = pm.length;
				for (k = 1; k < l; k++) {
					random_index = rand32Array[k] % (k + 1);
					// if (random_index != k) {
						t = pm[k];
						pm[k] = pm[random_index];
						pm[random_index] = t;
					// }
				}
			}
			return { pm: pm, gamma: new Uint8Array(this.randPool, l * 4) };
		};

	// Internal f5 algo functions
	// ===========================================================================================================
		f5stego.prototype._analyze = function(coeff) {
			var _one = 0,
				_zero = 0,
				_large, _ratio, usable, i, k, embedded, matched, changed;

			for (i = 0; i < coeff.length; i++) {
				if (i % 64 === 0) continue;
				if (coeff[i] === 0) _zero++;
				if (coeff[i] == 1 || coeff[i] == -1) _one++;
			}

			_large = coeff.length - _zero - _one - coeff.length / 64;
			_ratio = _one / (_large + _one);

			var res = {
				'capacity': [0, ((_large + (0.49 * _one)) >> 3) - 1],
				'coeff_total': coeff.length,
				'coeff_large': _large,
				'coeff_zero': _zero,
				'coeff_one': _one,
				'coeff_one_ratio': _one / (_large + _one)
			};

			for (i = 2; i < 17; i++) {
				k = (1 << i) - 1;
				usable = _large + _one;
				embedded = 0;
				while (usable > k) {
					matched = (usable / k / (1 << i) / (1 << i)) | 0;
					usable -= matched * k;

					changed = (usable * (1 - _ratio) / k * 0.96) | 0;
					usable -= changed * k;
					embedded += changed + matched;

					k++;
				}
				res.capacity[i] = ((i * embedded) >> 3) - 1;
			}

			return res;
		};

		f5stego.prototype._f5write = function(coeff, data, k) {
			var coeff_count = coeff.length;

			var _changed = 0,
				_embedded = 0,
				_examined = 0,
				_thrown = 0,
				shuffled_index = 0,
				i, n, ii;

			var pm = this.stegShuffle(coeff_count);
			var gamma = pm.gamma,
				gammaI = 0;
			pm = pm.pm;

			var next_bit_to_embed = 0,
				byte_to_embed = data.length,
				data_idx = 0,
				available_bits_to_embed = 0;

			n = (1 << k) - 1;

			byte_to_embed = k - 1;
			byte_to_embed ^= gamma[gammaI++];
			next_bit_to_embed = byte_to_embed & 1;
			byte_to_embed >>= 1;
			available_bits_to_embed = 3;

			for (ii = 0; ii < coeff_count; ii++) {
				shuffled_index = pm[ii];

				if (shuffled_index % 64 === 0 || coeff[shuffled_index] === 0) continue;

				var cc = coeff[shuffled_index];
				_examined++;

				if (cc > 0 && (cc & 1) != next_bit_to_embed) {
					coeff[shuffled_index]--;
					_changed++;
				} else if (cc < 0 && (cc & 1) == next_bit_to_embed) {
					coeff[shuffled_index]++;
					_changed++;
				}

				if (coeff[shuffled_index] !== 0) {
					_embedded++;
					if (available_bits_to_embed === 0) {
						if (k != 1 || data_idx >= data.length) break;
						byte_to_embed = data[data_idx++];
						byte_to_embed ^= gamma[gammaI++];
						available_bits_to_embed = 8;
					}
					next_bit_to_embed = byte_to_embed & 1;
					byte_to_embed >>= 1;
					available_bits_to_embed--;
				} else {
					_thrown++;
				}
			}

			if (k == 1 && _embedded < data.length * 8) throw 'capacity exceeded ' + (_embedded / 8) + ' ' + data.length;

			if (k != 1) {
				//ii--;
				var is_last_byte = false,
					k_bits_to_embed = 0;

				while (!is_last_byte || (available_bits_to_embed !== 0 && is_last_byte)) {
					k_bits_to_embed = 0;

					for (i = 0; i < k; i++) {
						if (available_bits_to_embed === 0) {
							if (data_idx >= data.length) {
								is_last_byte = true;
								break;
							}
							byte_to_embed = data[data_idx++];
							byte_to_embed ^= gamma[gammaI++];
							available_bits_to_embed = 8;
						}
						next_bit_to_embed = byte_to_embed & 1;
						byte_to_embed >>= 1;
						available_bits_to_embed--;
						k_bits_to_embed |= next_bit_to_embed << i;

					}

					var code_word = [];
					var ci = null;

					for (i = 0; i < n; i++) {
						while (true) {
							if (++ii >= coeff_count) {
								throw 'capacity exceeded ' + (_embedded / 8);
							}
							ci = pm[ii];

							if (ci % 64 !== 0 && coeff[ci] !== 0) break;
						}
						code_word.push(ci);
					}
					_examined += n;

					while (true) {
						var vhash = 0,
							extracted_bit;

						for (i = 0; i < code_word.length; i++) {
							if (coeff[code_word[i]] > 0) {
								extracted_bit = coeff[code_word[i]] & 1;
							} else {
								extracted_bit = 1 - (coeff[code_word[i]] & 1);
							}

							if (extracted_bit == 1)
								vhash ^= i + 1;
						}

						i = vhash ^ k_bits_to_embed;
						if (!i) {
							_embedded += k;
							break;
						}

						i--;
						coeff[code_word[i]] += coeff[code_word[i]] < 0 ? 1 : -1;
						_changed++;

						if (coeff[code_word[i]] === 0) {
							_thrown++;
							code_word.splice(i, 1);

							while (true) {
								if (++ii >= coeff_count) {
									throw 'capacity exceeded ' + (_embedded / 8);
								}
								ci = pm[ii];
								if (ci % 64 !== 0 && coeff[ci] !== 0) break;

							}
							_examined++;
							code_word.push(ci);
						} else {
							_embedded += k;
							break;
						}
					}
				}
			}

			return {
				'k': k,
				'embedded': _embedded / 8,
				'examined': _examined,
				'changed': _changed,
				'thrown': _thrown,
				'efficiency': (_embedded / _changed).toFixed(2)
			};
		};

	// Public f5 algo functions
	// ===========================================================================================================
		f5stego.prototype.analyze = function() {
			var i, comp = this.frame.components[0];

			if (comp.componentId != 1) {
				for (i = 0; i < this.frame.components.length; i++) {
					if (this.frame.components[i].componentId == 1) {
						comp = this.frame.components[i];
						break;
					}
				}
			}

			return this._analyze(comp.blocks);
		};

		f5stego.prototype.f5put = function(data, k) {
			var t, i, comp = this.frame.components[0];

			// Looks funny, but who knows?
			// From the other hand you need ~80MB jpeg to hide 8MB of data and this will be bigger than 4096x4096 pixels
			if (data.length > 8388607) throw 'Data too big. Max 8388607 bytes allowed.';

			if (data.length < 32768) {
				t = new Uint8Array(2 + data.length);
				t[0] = data.length & 255;
				t[1] = data.length >>> 8;
				t.set(data, 2);
			} else {
				t = new Uint8Array(3 + data.length);
				t[0] = data.length & 255;
				t[1] = ((data.length >>> 8) & 127) + 128;
				t[2] = data.length >>> 15;
				t.set(data, 3);
			}

			if (comp.componentId != 1) {
				for (i = 0; i < this.frame.components.length; i++) {
					if (this.frame.components[i].componentId == 1) {
						comp = this.frame.components[i];
						break;
					}
				}
			}

			if (k) {
				return this._f5write(comp.blocks, t, k);
			}

			var ret, prop = this._analyze(comp.blocks);

			k = 0;

			for (i = prop.capacity.length - 1; i >= 0; i--) {
				if (prop.capacity[i] >= t.length) {
					k = i;
					break;
				}
			}

			if (k === 0) throw 'capacity exceeded';

			try {
				ret = this._f5write(comp.blocks, t, k);
			} catch (e) {
				k--;
				if (k === 0) throw 'capacity exceeded';
				ret = this._f5write(comp.blocks, t, k);
			}

			ret['stats'] = prop;

			return ret;
		};

		f5stego.prototype.f5get = function() {
			var comp = this.frame.components[0];

			if (comp.componentId != 1) {
				for (var i = 0; i < this.frame.components.length; i++) {
					if (this.frame.components[i].componentId == 1) {
						comp = this.frame.components[i];
						break;
					}
				}
			}

			var coeff = new Int16Array(comp.blocks.length);
			coeff.set(comp.blocks);

			var pos = -1,
				extrBit = 0,
				cCount = coeff.length - 1;

			var pm = this.stegShuffle(coeff),
				gamma = pm.gamma,
				gammaI = 0;

			var n, k = 0;

			var out = new Uint8Array((coeff.length / 8) | 0),
				extrByte = 0,
				outPos = 0,
				bitsAvail = 0,
				code = 0,
				hash = 0;

			while (bitsAvail < 4) {
				pos++;

				if (coeff[pos] === 0) {
					continue;
				}

				extrBit = coeff[pos] & 1;


				if (coeff[pos] < 0) {
					extrBit = 1 - extrBit;
				}

				k |= extrBit << bitsAvail;
				bitsAvail++;
			}

			k = (k ^ gamma[gammaI++] & 15) + 1;
			n = (1 << k) - 1;

			bitsAvail = 0;

			if (k == 1) {
				while (pos < cCount) {
					pos++;

					if (coeff[pos] === 0) {
						continue;
					}

					extrBit = coeff[pos] & 1;

					if (coeff[pos] < 0) {
						extrBit = 1 - extrBit;
					}

					extrByte |= extrBit << bitsAvail;
					bitsAvail++;

					if (bitsAvail == 8) {
						out[outPos++] = extrByte ^ gamma[gammaI++];
						extrByte = 0;
						bitsAvail = 0;
					}
				}
			} else {
				while (pos < cCount) {
					pos++;

					if (coeff[pos] === 0) {
						continue;
					}

					extrBit = coeff[pos] & 1;

					if (coeff[pos] < 0) {
						extrBit = 1 - extrBit;
					}

					hash ^= extrBit * ++code;

					if (code == n) {
						extrByte |= hash << bitsAvail;
						bitsAvail += k;
						code = 0;
						hash = 0;

						while (bitsAvail >= 8) {
							out[outPos++] = (extrByte & 0xFF) ^ gamma[gammaI++];
							bitsAvail -= 8;
							extrByte = extrByte >> 8;
						}
					}
				}
			}

			while (bitsAvail > 0) {
				out[outPos++] = (extrByte & 0xFF) ^ gamma[gammaI++];
				bitsAvail -= 8;
				extrByte = extrByte >> 8;
			}

			var s = 2,
				l = out[0];

			if (out[1] & 128) {
				s++;
				l += ((out[1] & 127) << 8) + (out[2] << 15);
			} else {
				l += out[1] << 8;
			}

			return out.subarray(s, s + l);
		};

	// JPEG decoder
	// ===========================================================================================================
		f5stego.prototype.parse = function(data) {
			var offset = 0;

			function _buildHuffmanTable(nrcodes, values) {
				var codevalue = 0,
					pos_in_table = 0,
					HT = new Uint16Array(65536);
				for (var k = 0; k < 16; k++) {
					for (var j = 0; j < nrcodes[k]; j++) {
						for (var i = codevalue << (15 - k), cntTo = ((codevalue + 1) << (15 - k)); i < cntTo; i++) {
							HT[i] = values[pos_in_table] + ((k + 1) << 8);
						}
						pos_in_table++;
						codevalue++;
					}
					codevalue *= 2;
				}
				return HT;
			}

			function decodeScan(data, offset, frame, components, resetInterval, spectralStart, spectralEnd, successivePrev, successive) {

				var startOffset = offset,
					bitsData = 0,
					bitsCount = 0,
					eobrun = 0,
					p1 = 1 << successive,  /*  1 in the bit position being coded */
					m1 = -1 << successive; /* -1 in the bit position being coded */

				function decodeBaseline(component, pos) {
					while (bitsCount < 16) {
						bitsData = (bitsData << 8) + (data[offset] | 0);
						bitsCount += 8;
						if (data[offset] == 0xFF) offset++;
						offset++;
					}
					var t = component.huffmanTableDC[(bitsData >>> (bitsCount - 16)) & 0xFFFF];
					if (!t) throw "invalid huffman sequence";
					bitsCount -= t >>> 8;
					t &= 255;

					var diff = 0;
					if (t !== 0) {
						while (bitsCount < t) {
							bitsData = (bitsData << 8) + data[offset++];
							if ((bitsData & 0xff) == 0xFF) offset++;
							bitsCount += 8;
						}
						diff = (bitsData >>> (bitsCount - t)) & ((1 << t) - 1);
						bitsCount -= t;
						if (diff < 1 << (t - 1)) diff += (-1 << t) + 1;
					}
					component.blocksDC[pos >> 6] = (component.pred += diff);

					var k = 1,
						s, r;
					while (k < 64) {

						while (bitsCount < 16) {
							bitsData = (bitsData << 8) + (data[offset] | 0);
							bitsCount += 8;
							if (data[offset] == 0xFF) offset++;
							offset++;
						}
						s = component.huffmanTableAC[(bitsData >>> (bitsCount - 16)) & 0xFFFF];
						if (!s) throw "invalid huffman sequence";
						bitsCount -= s >>> 8;
						r = (s >> 4) & 15;
						s &= 15;

						if (s === 0) {
							if (r < 15) {
								break;
							}
							k += 16;
							continue;
						}
						k += r;
						while (bitsCount < s) {
							bitsData = (bitsData << 8) + data[offset++];
							if ((bitsData & 0xff) == 0xFF) offset++;
							bitsCount += 8;
						}
						component.blocks[pos + k] = (bitsData >>> (bitsCount - s)) & ((1 << s) - 1);
						bitsCount -= s;
						if (component.blocks[pos + k] < 1 << (s - 1)) component.blocks[pos + k] += (-1 << s) + 1;
						k++;
					}
				}

				function decodeDCFirst(component, pos) {
					var diff = 0;
					while (bitsCount < 16) {
						bitsData = (bitsData << 8) + (data[offset] | 0);
						bitsCount += 8;
						if (data[offset] == 0xFF) offset++;
						offset++;
					}
					var t = component.huffmanTableDC[(bitsData >>> (bitsCount - 16)) & 0xFFFF];
					if (!t) throw "invalid huffman sequence";
					bitsCount -= t >>> 8;
					t &= 255;

					if (t !== 0) {
						while (bitsCount < t) {
							bitsData = (bitsData << 8) + data[offset++];
							if ((bitsData & 0xff) == 0xFF) offset++;
							bitsCount += 8;
						}
						diff = (bitsData >>> (bitsCount - t)) & ((1 << t) - 1);
						bitsCount -= t;
						if (diff < 1 << (t - 1)) diff += (-1 << t) + 1;
					}
					component.blocksDC[pos >> 6] = (component.pred += diff << successive);
				}

				function decodeDCSuccessive(component, pos) {
					if (!bitsCount) {
						bitsData = data[offset++];
						if (bitsData == 0xFF) offset++;
						bitsCount = 8;
					}
					component.blocksDC[pos >> 6] |= ((bitsData >>> --bitsCount) & 1) << successive;
				}

				function decodeACFirst(component, pos) {
					if (eobrun > 0) {
						eobrun--;
						return;
					}

					var k = spectralStart,
						s, r;

					while (k <= spectralEnd) {
						while (bitsCount < 16) {
							bitsData = (bitsData << 8) + (data[offset] | 0);
							bitsCount += 8;
							if (data[offset] == 0xFF) offset++;
							offset++;
						}
						s = component.huffmanTableAC[(bitsData >>> (bitsCount - 16)) & 0xFFFF];
						if (!s) throw "invalid huffman sequence";
						bitsCount -= s >>> 8;
						r = (s >> 4) & 15;
						s &= 15;

						if (s === 0) {
							if (r != 15) {
								eobrun = (1 << r) - 1;
								if (r) {
									while (bitsCount < r) {
										bitsData = (bitsData << 8) + data[offset++];
										if ((bitsData & 0xff) == 0xFF) offset++;
										bitsCount += 8;
									}
									eobrun += (bitsData >>> (bitsCount - r)) & ((1 << r) - 1);
									bitsCount -= r;
								}
								break;
							}
							k += 16;
							continue;
						}

						k += r;
						while (bitsCount < s) {
							bitsData = (bitsData << 8) + data[offset++];
							if ((bitsData & 0xff) == 0xFF) offset++;
							bitsCount += 8;
						}
						component.blocks[pos + k] = (bitsData >>> (bitsCount - s)) & ((1 << s) - 1);
						bitsCount -= s;
						if (component.blocks[pos + k] < 1 << (s - 1)) component.blocks[pos + k] += (-1 << s) + 1;
						component.blocks[pos + k] *= p1;
						k++;
					}
				}

				function decodeACSuccessive(component, pos) {
					var k = spectralStart,
						r, s;

					if (!eobrun) {
						while (k <= spectralEnd) {
							while (bitsCount < 16) {
								bitsData = (bitsData << 8) + (data[offset] | 0);
								bitsCount += 8;
								if (data[offset] == 0xFF) offset++;
								offset++;
							}
							s = component.huffmanTableAC[(bitsData >>> (bitsCount - 16)) & 0xFFFF];
							if (!s) throw "invalid huffman sequence";
							bitsCount -= s >>> 8;
							r = (s >> 4) & 15;
							s &= 15;

							if (s) {
								if (s != 1) throw "bad jpeg";
								if (!bitsCount) {
									bitsData = data[offset++];
									if (bitsData == 0xFF) offset++;
									bitsCount = 8;
								}
								s = ((bitsData >>> --bitsCount) & 1) ? p1 : m1;
							} else {
								if (r != 15) {
									eobrun = (1 << r);
									if (r) {
										while (bitsCount < r) {
											bitsData = (bitsData << 8) + data[offset++];
											if ((bitsData & 0xff) == 0xFF) offset++;
											bitsCount += 8;
										}
										eobrun += (bitsData >>> (bitsCount - r)) & ((1 << r) - 1);
										bitsCount -= r;
									}
									break;
								}
							}

							while (k <= spectralEnd) {
								if (component.blocks[pos + k]) {
									if (!bitsCount) {
										bitsData = data[offset++];
										if (bitsData == 0xFF) offset++;
										bitsCount = 8;
									}
									component.blocks[pos + k] += ((bitsData >>> --bitsCount) & 1) * (component.blocks[pos + k] >= 0 ? p1 : m1);
								} else {
									if (--r < 0) break;
								}
								k++;
							}

							if (s) component.blocks[pos + k] = s;
							k++;
						}
					}

					if (eobrun) {
						while (k <= spectralEnd) {
							if (component.blocks[pos + k]) {
								if (!bitsCount) {
									bitsData = data[offset++];
									if (bitsData == 0xFF) offset++;
									bitsCount = 8;
								}
								component.blocks[pos + k] += ((bitsData >>> --bitsCount) & 1) * (component.blocks[pos + k] >= 0 ? p1 : m1);
							}
							k++;
						}
						eobrun--;
					}
				}

				var decodeFn;

				if (frame.progressive) {
					if (spectralStart === 0)
						decodeFn = successivePrev === 0 ? decodeDCFirst : decodeDCSuccessive;
					else
						decodeFn = successivePrev === 0 ? decodeACFirst : decodeACSuccessive;
				} else {
					decodeFn = decodeBaseline;
				}

				var marker, mcuExpected, i, j, k, n, mcusPerLine, mcusPerRow, x, y;

				if (components.length == 1) {
					mcusPerLine = components[0].blocksPerLine;
					mcusPerRow = components[0].blocksPerColumn;
					mcuExpected = mcusPerRow * mcusPerLine;

					if (!resetInterval) resetInterval = mcuExpected;
					n = resetInterval;
					components[0].pred = 0;
					eobrun = 0;

					for (y = 0; y < mcusPerRow; y++) {
						for (x = 0; x < mcusPerLine; x++) {
							if (!n) {
								n = resetInterval;
								components[0].pred = 0;
								eobrun = 0;

								// find marker
								offset -= (bitsCount / 8) | 0;
								if (data[offset - 1] == 0xFF) offset--;
								bitsCount = 0;
								marker = (data[offset] << 8) | data[offset + 1];

								if (marker >= 0xFFD0 && marker <= 0xFFD7) { // RSTx
									offset += 2;
								} else {
									if (marker <= 0xFF00) {
										throw "bad jpeg";
									}
									break;
								}
							}
							n--;
							for (i = 0; i < components.length; i++) {
								decodeFn(components[i], (y * components[i].blocksPerLineForMcu + x) * 64);
							}

						}
					}
				} else {
					mcusPerLine = frame.mcusPerLine;
					mcusPerRow = frame.mcusPerColumn;
					mcuExpected = mcusPerRow * mcusPerLine;

					if (!resetInterval) resetInterval = mcuExpected;
					n = resetInterval;
					for (i = 0; i < components.length; i++) components[i].pred = 0;
					eobrun = 0;

					for (y = 0; y < mcusPerRow; y++) {
						for (x = 0; x < mcusPerLine; x++) {
							if (!n) {
								n = resetInterval;
								for (i = 0; i < components.length; i++) components[i].pred = 0;
								eobrun = 0;

								// find marker
								offset -= (bitsCount / 8) | 0;
								if (data[offset - 1] == 0xFF) offset--;
								bitsCount = 0;
								marker = (data[offset] << 8) | data[offset + 1];

								if (marker >= 0xFFD0 && marker <= 0xFFD7) { // RSTx
									offset += 2;
								} else {
									if (marker <= 0xFF00) {
										throw "bad jpeg";
									}
									break;
								}
							}
							n--;
							for (i = 0; i < components.length; i++) {
								for (j = 0; j < components[i].v; j++) {
									for (k = 0; k < components[i].h; k++) {
										decodeFn(components[i], ((y * components[i].v + j) * components[i].blocksPerLineForMcu + x * components[i].h + k) * 64);
									}
								}
							}
						}
					}
				}
				offset -= (bitsCount / 8) | 0;
				if (data[offset - 1] == 0xFF) offset--;
				return offset - startOffset;
			}

			function readUint16() {
				var value = (data[offset] << 8) | data[offset + 1];
				offset += 2;
				return value;
			}

			function readDataBlock() {
				var length = readUint16();
				var array = data.subarray(offset, offset + length - 2);
				offset += array.length;
				return array;
			}

			this['_raw'] = data;
			this['jfif'] = null;
			this['APPn'] = [];
			this['qts'] = [];
			this['frame'] = null;
			this['tail'] = null;

			var markerHi, markerLo, i, j, resetInterval, component;
			var huffmanTablesAC = [],
				huffmanTablesDC = [];

			while (1) {
				if (offset >= data.length) throw "unexpected EOF";

				markerHi = data[offset++];
				markerLo = data[offset++];

				if (markerHi == 0xFF) {
					if (markerLo == 0xE0) { //APP0 - JFIF header
						this.jfif = readDataBlock();
					}

					if ((markerLo > 0xE0 && markerLo < 0xF0) || markerLo == 0xFE) { //APPn + COM
						this.APPn.push({
							'app': markerLo,
							'data': readDataBlock()
						});
					}

					if (markerLo == 0xDB) { // DQT (Define Quantization Tables)
						this.qts.push(readDataBlock());
					}

					if (markerLo >= 0xC0 && markerLo <= 0xC2) {
						// SOF0 (Start of Frame, Baseline DCT)
						// SOF1 (Start of Frame, Extended DCT)
						// SOF2 (Start of Frame, Progressive DCT)
						if (this.frame) throw "Only single frame JPEGs supported";
						readUint16(); // skip data length

						this.frame = {
							'extended': (markerLo === 0xC1),
							'progressive': (markerLo === 0xC2),
							'precision': data[offset++],
							'scanLines': readUint16(),
							'samplesPerLine': readUint16(),
							'components': [],
							'componentIds': {},
							'maxH': 1,
							'maxV': 1
						};

						if (this.frame.scanLines * this.frame.samplesPerLine > this.maxPixels) throw "Image is too big.";

						var componentsCount = data[offset++],
							componentId;
						var maxH = 0,
							maxV = 0;
						for (i = 0; i < componentsCount; i++) {
							componentId = data[offset];
							var h = data[offset + 1] >> 4;
							var v = data[offset + 1] & 15;
							if (maxH < h) maxH = h;
							if (maxV < v) maxV = v;
							var qId = data[offset + 2];
							var l = this.frame.components.push({
								'componentId': componentId,
								'h': h,
								'v': v,
								'quantizationTable': qId
							});
							this.frame.componentIds[componentId] = l - 1;
							offset += 3;
						}
						this.frame.maxH = maxH;
						this.frame.maxV = maxV;

						var mcusPerLine = Math.ceil(this.frame.samplesPerLine / 8 / maxH);
						var mcusPerColumn = Math.ceil(this.frame.scanLines / 8 / maxV);
						for (i = 0; i < this.frame.components.length; i++) {
							component = this.frame.components[i];
							var blocksPerLine = Math.ceil(Math.ceil(this.frame.samplesPerLine / 8) * component.h / maxH);
							var blocksPerColumn = Math.ceil(Math.ceil(this.frame.scanLines / 8) * component.v / maxV);
							var blocksPerLineForMcu = mcusPerLine * component.h;
							var blocksPerColumnForMcu = mcusPerColumn * component.v;

							component['blocks'] = new Int16Array(blocksPerColumnForMcu * blocksPerLineForMcu * 64);
							component['blocksDC'] = new Int16Array(blocksPerColumnForMcu * blocksPerLineForMcu);
							component['blocksPerLine'] = blocksPerLine;
							component['blocksPerColumn'] = blocksPerColumn;
							component['blocksPerLineForMcu'] = blocksPerLineForMcu;
							component['blocksPerColumnForMcu'] = blocksPerColumnForMcu;
						}
						this.frame['mcusPerLine'] = mcusPerLine;
						this.frame['mcusPerColumn'] = mcusPerColumn;
					}

					if (markerLo == 0xC4) { // DHT (Define Huffman Tables)
						var huffmanLength = readUint16();
						for (i = 2; i < huffmanLength;) {
							var huffmanTableSpec = data[offset++];
							var codeLengths = new Uint8Array(16);
							var codeLengthSum = 0;
							for (j = 0; j < 16; j++, offset++)
								codeLengthSum += (codeLengths[j] = data[offset]);
							var huffmanValues = new Uint8Array(codeLengthSum);
							for (j = 0; j < codeLengthSum; j++, offset++)
								huffmanValues[j] = data[offset];
							i += 17 + codeLengthSum;
							((huffmanTableSpec >> 4) === 0 ?
								huffmanTablesDC : huffmanTablesAC)[huffmanTableSpec & 15] = _buildHuffmanTable(codeLengths, huffmanValues);
						}
					}

					if (markerLo == 0xDD) { // DRI (Define Restart Interval)
						resetInterval = readUint16();
					}

					if (markerLo == 0xDA) { // SOS (Start of Scan)
						readUint16();
						var selectorsCount = data[offset++];
						var components = [];

						for (i = 0; i < selectorsCount; i++) {
							var componentIndex = this.frame.componentIds[data[offset++]];
							component = this.frame.components[componentIndex];
							var tableSpec = data[offset++];
							component.huffmanTableDC = huffmanTablesDC[tableSpec >> 4];
							component.huffmanTableAC = huffmanTablesAC[tableSpec & 15];
							components.push(component);
						}

						var spectralStart = data[offset++];
						var spectralEnd = data[offset++];
						var successiveApproximation = data[offset++];
						var processed = decodeScan(data, offset,
							this.frame, components, resetInterval,
							spectralStart, spectralEnd,
							successiveApproximation >> 4, successiveApproximation & 15);
						offset += processed;
					}

					if (markerLo == 0xD9) { // EOI (End of image)
						break;
					}
				} else {
					if (data[offset - 3] == 0xFF &&
						data[offset - 2] >= 0xC0 && data[offset - 2] <= 0xFE) {
						// could be incorrect encoding -- last 0xFF byte of the previous
						// block was eaten by the encoder
						offset -= 3;
					}
					while (data[offset] != 0xFF && offset < data.length) {
						// file could be damaged and have some extra data between blocks
						offset++;
					}

					if (data[offset] != 0xFF) {
						throw "bad jpeg ";
					}
				}
			}

			if (!this.frame) throw 'bad jpeg';

			if (offset < data.length) this.tail = data.subarray(offset);

			return this;
		};

	// Standard Huffman tables for coder initialization
	// ===========================================================================================================
		var bitcode = new Array(65535),
			category = new Array(65535),
			std_dc_luminance_nrcodes = [0, 0, 1, 5, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0],
			std_dc_luminance_values = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11],
			std_ac_luminance_nrcodes = [0, 0, 2, 1, 3, 3, 2, 4, 3, 5, 5, 4, 4, 0, 0, 1, 0x7d],
			std_ac_luminance_values = [
				0x01, 0x02, 0x03, 0x00, 0x04, 0x11, 0x05, 0x12,
				0x21, 0x31, 0x41, 0x06, 0x13, 0x51, 0x61, 0x07,
				0x22, 0x71, 0x14, 0x32, 0x81, 0x91, 0xa1, 0x08,
				0x23, 0x42, 0xb1, 0xc1, 0x15, 0x52, 0xd1, 0xf0,
				0x24, 0x33, 0x62, 0x72, 0x82, 0x09, 0x0a, 0x16,
				0x17, 0x18, 0x19, 0x1a, 0x25, 0x26, 0x27, 0x28,
				0x29, 0x2a, 0x34, 0x35, 0x36, 0x37, 0x38, 0x39,
				0x3a, 0x43, 0x44, 0x45, 0x46, 0x47, 0x48, 0x49,
				0x4a, 0x53, 0x54, 0x55, 0x56, 0x57, 0x58, 0x59,
				0x5a, 0x63, 0x64, 0x65, 0x66, 0x67, 0x68, 0x69,
				0x6a, 0x73, 0x74, 0x75, 0x76, 0x77, 0x78, 0x79,
				0x7a, 0x83, 0x84, 0x85, 0x86, 0x87, 0x88, 0x89,
				0x8a, 0x92, 0x93, 0x94, 0x95, 0x96, 0x97, 0x98,
				0x99, 0x9a, 0xa2, 0xa3, 0xa4, 0xa5, 0xa6, 0xa7,
				0xa8, 0xa9, 0xaa, 0xb2, 0xb3, 0xb4, 0xb5, 0xb6,
				0xb7, 0xb8, 0xb9, 0xba, 0xc2, 0xc3, 0xc4, 0xc5,
				0xc6, 0xc7, 0xc8, 0xc9, 0xca, 0xd2, 0xd3, 0xd4,
				0xd5, 0xd6, 0xd7, 0xd8, 0xd9, 0xda, 0xe1, 0xe2,
				0xe3, 0xe4, 0xe5, 0xe6, 0xe7, 0xe8, 0xe9, 0xea,
				0xf1, 0xf2, 0xf3, 0xf4, 0xf5, 0xf6, 0xf7, 0xf8,
				0xf9, 0xfa
			],
			std_dc_chrominance_nrcodes = [0, 0, 3, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0],
			std_dc_chrominance_values = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11],
			std_ac_chrominance_nrcodes = [0, 0, 2, 1, 2, 4, 4, 3, 4, 7, 5, 4, 4, 0, 1, 2, 0x77],
			std_ac_chrominance_values = [
				0x00, 0x01, 0x02, 0x03, 0x11, 0x04, 0x05, 0x21,
				0x31, 0x06, 0x12, 0x41, 0x51, 0x07, 0x61, 0x71,
				0x13, 0x22, 0x32, 0x81, 0x08, 0x14, 0x42, 0x91,
				0xa1, 0xb1, 0xc1, 0x09, 0x23, 0x33, 0x52, 0xf0,
				0x15, 0x62, 0x72, 0xd1, 0x0a, 0x16, 0x24, 0x34,
				0xe1, 0x25, 0xf1, 0x17, 0x18, 0x19, 0x1a, 0x26,
				0x27, 0x28, 0x29, 0x2a, 0x35, 0x36, 0x37, 0x38,
				0x39, 0x3a, 0x43, 0x44, 0x45, 0x46, 0x47, 0x48,
				0x49, 0x4a, 0x53, 0x54, 0x55, 0x56, 0x57, 0x58,
				0x59, 0x5a, 0x63, 0x64, 0x65, 0x66, 0x67, 0x68,
				0x69, 0x6a, 0x73, 0x74, 0x75, 0x76, 0x77, 0x78,
				0x79, 0x7a, 0x82, 0x83, 0x84, 0x85, 0x86, 0x87,
				0x88, 0x89, 0x8a, 0x92, 0x93, 0x94, 0x95, 0x96,
				0x97, 0x98, 0x99, 0x9a, 0xa2, 0xa3, 0xa4, 0xa5,
				0xa6, 0xa7, 0xa8, 0xa9, 0xaa, 0xb2, 0xb3, 0xb4,
				0xb5, 0xb6, 0xb7, 0xb8, 0xb9, 0xba, 0xc2, 0xc3,
				0xc4, 0xc5, 0xc6, 0xc7, 0xc8, 0xc9, 0xca, 0xd2,
				0xd3, 0xd4, 0xd5, 0xd6, 0xd7, 0xd8, 0xd9, 0xda,
				0xe2, 0xe3, 0xe4, 0xe5, 0xe6, 0xe7, 0xe8, 0xe9,
				0xea, 0xf2, 0xf3, 0xf4, 0xf5, 0xf6, 0xf7, 0xf8,
				0xf9, 0xfa
			];

		function _initCategoryNumber() {
			var nrlower = 1;
			var nrupper = 2;
			for (var cat = 1; cat <= 15; cat++) {
				//Positive numbers
				for (var nr = nrlower; nr < nrupper; nr++) {
					category[32767 + nr] = cat;
					bitcode[32767 + nr] = [];
					bitcode[32767 + nr][1] = cat;
					bitcode[32767 + nr][0] = nr;
				}
				//Negative numbers
				for (var nrneg = -(nrupper - 1); nrneg <= -nrlower; nrneg++) {
					category[32767 + nrneg] = cat;
					bitcode[32767 + nrneg] = [];
					bitcode[32767 + nrneg][1] = cat;
					bitcode[32767 + nrneg][0] = nrupper - 1 + nrneg;
				}
				nrlower <<= 1;
				nrupper <<= 1;
			}
		}

		_initCategoryNumber();

		function _computeHuffmanTbl(nrcodes, std_table) {
			var codevalue = 0;
			var pos_in_table = 0;
			var HT = [];
			for (var k = 1; k <= 16; k++) {
				for (var j = 1; j <= nrcodes[k]; j++) {
					HT[std_table[pos_in_table]] = [];
					HT[std_table[pos_in_table]][0] = codevalue;
					HT[std_table[pos_in_table]][1] = k;
					pos_in_table++;
					codevalue++;
				}
				codevalue *= 2;
			}
			return HT;
		}

		var YDC_HT = _computeHuffmanTbl(std_dc_luminance_nrcodes, std_dc_luminance_values),
			UVDC_HT = _computeHuffmanTbl(std_dc_chrominance_nrcodes, std_dc_chrominance_values),
			YAC_HT = _computeHuffmanTbl(std_ac_luminance_nrcodes, std_ac_luminance_values),
			UVAC_HT = _computeHuffmanTbl(std_ac_chrominance_nrcodes, std_ac_chrominance_values);

	// JPEG encoder
	// ===========================================================================================================
		f5stego.prototype.pack = function() {
			var byteout, bytenew, bytepos, poslast, outpos, byte;

			// IO functions
			function writeByte(value) {
				var t;

				byteout[outpos++] = value;
				if (outpos > poslast) {
					t = new Uint8Array(byteout.length * 2);
					t.set(byteout);
					byteout = t;
					poslast = t.length - 128;
				}
			}

			function writeWord(value) {
				writeByte((value >> 8) & 0xFF);
				writeByte((value) & 0xFF);
			}

			function writeBlock(block) {
				var t;
				if (outpos + block.length > poslast) {
					t = new Uint8Array(byteout.length * 2 + block.length);
					t.set(byteout);
					byteout = t;
					poslast = t.length - 128;
				}

				byteout.set(block, outpos);
				outpos += block.length;
			}

			function writeAPP0(self) {
				writeWord(0xFFE0); // marker
				if (!self.jfif) {
					writeWord(16); // length
					writeByte(0x4A); // J
					writeByte(0x46); // F
					writeByte(0x49); // I
					writeByte(0x46); // F
					writeByte(0); // = "JFIF",'\0'
					writeByte(1); // versionhi
					writeByte(1); // versionlo
					writeByte(0); // xyunits
					writeWord(1); // xdensity
					writeWord(1); // ydensity
					writeByte(0); // thumbnwidth
					writeByte(0); // thumbnheight
				} else {
					writeWord(self.jfif.length + 2); // length
					writeBlock(self.jfif);
				}
			}

			function writeDQT(self) {
				for (var i = 0; i < self.qts.length; i++) {
					writeWord(0xFFDB); // marker
					writeWord(self.qts[i].length + 2); // length
					writeBlock(self.qts[i]);
				}
			}

			function writeAPPn(self) {
				for (var i = 0; i < self.APPn.length; i++) {
					writeWord(0xFF00 | self.APPn[i].app);
					writeWord(self.APPn[i].data.length + 2);
					writeBlock(self.APPn[i].data);
				}
			}

			function writeSOF0(self) {
				writeWord(0xFFC0); // marker
				writeWord(8 + self.frame.components.length * 3); // length
				writeByte(self.frame.precision); // precision
				writeWord(self.frame.scanLines);
				writeWord(self.frame.samplesPerLine);
				writeByte(self.frame.components.length); // nrofcomponents

				for (var i = 0; i < self.frame.components.length; i++) {
					var c = self.frame.components[i];
					writeByte(c.componentId);
					writeByte(c.h << 4 | c.v);
					writeByte(c.quantizationTable);
				}
			}

			function writeDHT(self) {
				writeWord(0xFFC4); // marker
				writeWord(31); // length
				writeByte(0); // HTYDCinfo
				for (var i = 0; i < 16; i++) {
					writeByte(std_dc_luminance_nrcodes[i + 1]);
				}
				for (var j = 0; j <= 11; j++) {
					writeByte(std_dc_luminance_values[j]);
				}

				writeWord(0xFFC4); // marker
				writeWord(181); // length
				writeByte(0x10); // HTYACinfo
				for (var k = 0; k < 16; k++) {
					writeByte(std_ac_luminance_nrcodes[k + 1]);
				}
				for (var l = 0; l <= 161; l++) {
					writeByte(std_ac_luminance_values[l]);
				}

				if (self.frame.components.length != 1) {
					writeWord(0xFFC4); // marker
					writeWord(31); // length
					writeByte(1); // HTUDCinfo
					for (var m = 0; m < 16; m++) {
						writeByte(std_dc_chrominance_nrcodes[m + 1]);
					}
					for (var n = 0; n <= 11; n++) {
						writeByte(std_dc_chrominance_values[n]);
					}

					writeWord(0xFFC4); // marker
					writeWord(181); // length
					writeByte(0x11); // HTUACinfo
					for (var o = 0; o < 16; o++) {
						writeByte(std_ac_chrominance_nrcodes[o + 1]);
					}
					for (var p = 0; p <= 161; p++) {
						writeByte(std_ac_chrominance_values[p]);
					}
				}
			}

			function writeSOS(self) {
				writeWord(0xFFDA); // marker
				writeWord(6 + self.frame.components.length * 2); // length
				writeByte(self.frame.components.length); // nrofcomponents

				for (var i = 0; i < self.frame.components.length; i++) {
					var c = self.frame.components[i];
					writeByte(c.componentId);
					if (i === 0) {
						writeByte(0);
					} else {
						writeByte(0x11);
					}
				}

				writeByte(0); // Ss
				writeByte(0x3f); // Se
				writeByte(0); // Bf
			}

			function processDU(comp, POS, DC, HTDC, HTAC) {
				var pos, posval, t;

				if (bytepos === 0) bytenew = 0;

				var Diff = comp.blocksDC[POS >> 6] - DC;
				DC = comp.blocksDC[POS >> 6];
				//Encode DC
				if (Diff === 0) {
					posval = HTDC[0][1];

					bytenew <<= posval;
					bytenew += HTDC[0][0];
					bytepos += posval;

					while (bytepos > 7) {
						byte = 0xFF & (bytenew >>> (bytepos - 8));
						byteout[outpos++] = byte;
						if (byte == 0xFF) {
							outpos++;
						}
						bytepos -= 8;
						bytenew &= (1 << bytepos) - 1;
					}

				} else {
					pos = 32767 + Diff;

					posval = HTDC[category[pos]][1];
					bytenew <<= posval;
					bytenew += HTDC[category[pos]][0];
					bytepos += posval;

					posval = bitcode[pos][1];
					bytenew <<= posval;
					bytenew += bitcode[pos][0];
					bytepos += posval;

					while (bytepos > 7) {
						byte = 0xFF & (bytenew >>> (bytepos - 8));
						byteout[outpos++] = byte;
						if (byte == 0xFF) {
							outpos++;
						}
						bytepos -= 8;
						bytenew &= (1 << bytepos) - 1;
					}
				}
				//Encode ACs
				var end0pos = 63; // was const... which is crazy
				for (;
					(end0pos > 0) && (comp.blocks[POS + end0pos] === 0); end0pos--) {}
				//end0pos = first element in reverse order !=0
				if (end0pos === 0) {
					posval = HTAC[0x00][1];
					bytenew <<= posval;
					bytenew += HTAC[0x00][0];
					bytepos += posval;

					while (bytepos > 7) {
						byte = 0xFF & (bytenew >>> (bytepos - 8));
						byteout[outpos++] = byte;
						if (byte == 0xFF) {
							outpos++;
						}
						bytepos -= 8;
						bytenew &= (1 << bytepos) - 1;
					}
					return DC;
				}
				var i = 1;
				var lng;
				while (i <= end0pos) {
					var startpos = i;
					for (;
						(comp.blocks[POS + i] === 0) && (i <= end0pos); ++i) {}
					var nrzeroes = i - startpos;
					if (nrzeroes >= 16) {
						lng = nrzeroes >> 4;
						for (var nrmarker = 1; nrmarker <= lng; ++nrmarker) {
							posval = HTAC[0xF0][1];
							bytenew <<= posval;
							bytenew += HTAC[0xF0][0];
							bytepos += posval;

							while (bytepos > 7) {
								byte = 0xFF & (bytenew >>> (bytepos - 8));
								byteout[outpos++] = byte;
								if (byte == 0xFF) {
									outpos++;
								}
								bytepos -= 8;
								bytenew &= (1 << bytepos) - 1;
							}
						}
						nrzeroes = nrzeroes & 0xF;
					}
					pos = 32767 + comp.blocks[POS + i];

					posval = HTAC[(nrzeroes << 4) + category[pos]][1];
					bytenew <<= posval;
					bytenew += HTAC[(nrzeroes << 4) + category[pos]][0];
					bytepos += posval;

					while (bytepos > 7) {
						byte = 0xFF & (bytenew >>> (bytepos - 8));
						byteout[outpos++] = byte;
						if (byte == 0xFF) {
							outpos++;
						}
						bytepos -= 8;
						bytenew &= (1 << bytepos) - 1;
					}

					posval = bitcode[pos][1];
					bytenew <<= posval;
					bytenew += bitcode[pos][0];
					bytepos += posval;

					while (bytepos > 7) {
						byte = 0xFF & (bytenew >>> (bytepos - 8));
						byteout[outpos++] = byte;
						if (byte == 0xFF) {
							outpos++;
						}
						bytepos -= 8;
						bytenew &= (1 << bytepos) - 1;
					}
					i++;
				}
				if (end0pos != 63) {
					posval = HTAC[0x00][1];
					bytenew <<= posval;
					bytenew += HTAC[0x00][0];
					bytepos += posval;

					while (bytepos > 7) {
						byte = 0xFF & (bytenew >>> (bytepos - 8));
						byteout[outpos++] = byte;
						if (byte == 0xFF) {
							outpos++;
						}
						bytepos -= 8;
						bytenew &= (1 << bytepos) - 1;
					}
				}

				if (outpos > poslast) {
					t = new Uint8Array(byteout.length * 2);
					t.set(byteout);
					byteout = t;
					poslast = t.length - 128;
				}

				return DC;
			}

			// Initialize bit writer
			byteout = new Uint8Array(65536);
			poslast = 65536 - 128;
			outpos = 0;
			bytenew = 0;
			bytepos = 0;

			// Add JPEG headers
			writeWord(0xFFD8); // SOI
			writeAPP0(this);
			writeAPPn(this);
			writeDQT(this);
			writeSOF0(this);
			writeDHT(this);
			writeSOS(this);

			bytenew = 0;
			bytepos = 0;

			var c, mcuRow, mcuCol, blockRow, blockCol, mcu, i, v, h;

			var DCdiff = [];
			for (i = 0; i < this.frame.components.length; i++) {
				DCdiff.push(0);
			}

			for (mcu = 0; mcu < this.frame.mcusPerLine * this.frame.mcusPerColumn; mcu++) {
				mcuRow = (mcu / this.frame.mcusPerLine) | 0;
				mcuCol = mcu % this.frame.mcusPerLine;
				for (i = 0; i < this.frame.components.length; i++) {
					c = this.frame.components[i];
					for (v = 0; v < c.v; v++) {
						blockRow = mcuRow * c.v + v;
						for (h = 0; h < c.h; h++) {
							blockCol = mcuCol * c.h + h;
							if (i === 0) {
								DCdiff[i] = processDU(c, (blockRow * this.frame.mcusPerLine * c.h + blockCol) * 64, DCdiff[i], YDC_HT, YAC_HT);
							} else {
								DCdiff[i] = processDU(c, (blockRow * this.frame.mcusPerLine * c.h + blockCol) * 64, DCdiff[i], UVDC_HT, UVAC_HT);
							}
						}
					}
				}
			}

			// Write last bytes from coder
			while (bytepos > 7) {
				byte = 0xFF & (bytenew >>> (bytepos - 8));
				byteout[outpos++] = byte;
				if (byte == 0xFF) {
					outpos++;
				}
				bytepos -= 8;
			}
			// And do the bit alignment of the EOI marker
			if (bytepos > 0) {
				bytenew <<= 8 - bytepos;
				bytenew += (1 << (8 - bytepos)) - 1;
				byteout[outpos++] = 0xFF & bytenew;
			}

			writeWord(0xFFD9); //EOI
			if (this.tail) writeBlock(this.tail);

			return byteout.slice(0, outpos);
		};

	// Metadata manipulation
	// ===========================================================================================================
		f5stego.prototype.clearTail = function() {
			if (!this.tail) return null;

			var t = this.tail;
			this.tail = null;

			return t;
		};

		f5stego.prototype.setTail = function(data) {
			this.tail = data;
		};

		f5stego.prototype.getTail = function() {
			return this.tail;
		};

		f5stego.prototype.clearAPPs = function() {
			var t = this.APPn;
			this.APPn = [];
			return t;
		};

		f5stego.prototype.getAPPn = function(id, remove) {
			var i, t, ret = new Uint8Array(0),
				n = [];

			id &= 0xFF;
			if (id < 16) id += 0xE0;
			if (id === 0xE0) return this.jfif;

			for (i = 0; i < this.APPn.length; i++) {
				if (this.APPn[i].app == id) {
					t = new Uint8Array(ret.length + this.APPn[i].data.length);
					t.set(ret);
					t.set(this.APPn[i].data, ret.length);
					ret = t;
				} else if (remove) n.push(this.APPn[i]);
			}

			if (remove) this.APPn = n;

			if (ret.length === 0) return null;

			return ret;
		};

		f5stego.prototype.setAPPn = function(id, data) {
			var i, t, ret;

			id &= 0xFF;
			if (id < 16) id += 0xE0;

			if (id === 0xE0) {
				t = this.jfif;
				this.jfif = data;
				return t;
			}

			ret = this.getAPPn(id, true);

			if (data.length < 65534) {
				this.APPn.push({ 'app': id, 'data': data });
				return ret;
			}

			i = 0;

			while (i < data.length) {
				this.APPn.push({ 'app': id, 'data': data.subarray(i, i + 65533) });
				i += 65533;
			}

			return ret;
		};

		f5stego.prototype.strip = function() {
			this.clearTail();
			this.clearAPPs();
			return true;
		};

	// Shorthand functions to embed/extract f5 data
	// ===========================================================================================================
		f5stego.prototype.embed = function(image, data) {
			this.parse(image).f5put(data);
			return this.pack();
		};

		f5stego.prototype.extract = function(image) {
			return this.parse(image).f5get();
		};

	return f5stego;
}));
