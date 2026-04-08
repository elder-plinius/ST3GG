# ST3GG Example Files

Pre-encoded steganography samples for testing the **Agent tab's Exhaustive Mode** and other decoder tools without having to encode files yourself.

All new examples (Plinian divider series) encode the secret message:
```
⊰•-•✧•-•-⦑/L\O/V\E/\P/L\I/N\Y/⦒-•-•✧•-•⊱
```

## Original Examples

| File | Technique | What's Hidden |
|------|-----------|---------------|
| `example_lsb_rgb.png` | LSB RGB 1-bit (STEG v3 header) | Text message embedded in pixel LSBs |
| `example_png_chunks.png` | PNG tEXt chunks | Secret messages in metadata chunks |
| `example_trailing_data.png` | Trailing data after IEND | Data appended after PNG end marker |
| `example_metadata.png` | PNG metadata (base64 + hex) | Encoded strings in Description/HexData fields |
| `example_zero_width.txt` | Zero-width Unicode | Invisible characters between visible text |
| `example_whitespace.txt` | Whitespace encoding | Hidden bits in trailing spaces/tabs |
| `example_invisible_ink.txt` | Unicode tag characters | Invisible ink using U+E0000 range |
| `example_audio_lsb.wav` | Audio LSB | Message in least significant bits of audio samples |

## Image Formats (Plinian Divider)

| File | Technique | What's Hidden |
|------|-----------|---------------|
| `example_lsb.bmp` | BMP LSB RGB | Plinian divider in pixel LSBs |
| `example_comment.gif` | GIF comment extension | Plinian divider in GIF comment block |
| `example_lsb.gif` | GIF palette index LSB | Plinian divider in palette index LSBs |
| `example_metadata.tiff` | TIFF metadata (base64) | Plinian divider in TIFF description tag |
| `example_lsb.tiff` | TIFF LSB RGB | Plinian divider in pixel LSBs |
| `example_lsb.ppm` | PPM (Portable Pixmap) LSB | Plinian divider in raw pixel LSBs |
| `example_lsb.pgm` | PGM (Portable Graymap) LSB | Plinian divider in grayscale LSBs |
| `example_hidden.svg` | SVG XML comments + attributes | Plinian divider in comments, data-attrs, metadata |
| `example_lsb.ico` | ICO LSB RGB | Plinian divider in icon pixel LSBs |
| `example_metadata.webp` | WebP EXIF metadata | Plinian divider in EXIF ImageDescription |
| `example_lsb.webp` | WebP lossless LSB | Plinian divider in pixel LSBs |

## Document & Structured Data Formats (Plinian Divider)

| File | Technique | What's Hidden |
|------|-----------|---------------|
| `example_hidden.html` | HTML comments + zero-width + hidden divs | Plinian divider in comments, meta tags, invisible elements, zero-width chars |
| `example_hidden.xml` | XML comments + CDATA + PIs | Plinian divider in processing instructions, CDATA, attributes |
| `example_hidden.json` | JSON metadata fields | Plinian divider in base64, hex, and direct Unicode fields |
| `example_whitespace.csv` | CSV whitespace encoding | Plinian divider in trailing spaces/tabs per row |
| `example_hidden.yaml` | YAML comments + byte table | Plinian divider in comments, base64, hex, and per-byte references |
| `example_hidden.pdf` | PDF metadata + streams + post-EOF | Plinian divider in XMP metadata, content streams, and after %%EOF |
| `example_hidden.rtf` | RTF hidden text groups | Plinian divider in \\v hidden text, info fields, bookmarks |
| `example_hidden.md` | Markdown HTML comments + zero-width | Plinian divider in HTML comments, link references, zero-width chars |

## Audio, Binary & Archive Formats (Plinian Divider)

| File | Technique | What's Hidden |
|------|-----------|---------------|
| `example_lsb.aiff` | AIFF audio LSB + annotation | Plinian divider in sample LSBs and ANNO chunk |
| `example_lsb.au` | AU (Sun/NeXT) audio LSB | Plinian divider in sample LSBs and header annotation |
| `example_hidden.zip` | ZIP archive comment + trailing | Plinian divider in archive comment and appended after ZIP |
| `example_hidden.tar` | TAR PAX extended headers | Plinian divider in pax header comment and custom STEG fields |
| `example_hidden.gz` | GZip extra field + comment | Plinian divider in FEXTRA and FCOMMENT header fields |
| `example_hidden.sqlite` | SQLite hidden table | Plinian divider in `_steg_payload` table (direct, base64, hex) |
| `example_hidden.hexdump` | Hex dump embedded bytes | Plinian divider embedded at offset 0x40 in raw byte data |
| `example_hidden.mid` | MIDI SysEx + text event | Plinian divider in SysEx message and MIDI text event |
| `example_hidden.pcap` | PCAP packet payloads | Plinian divider split across UDP packet payloads |

## Code & Config Formats (Plinian Divider)

| File | Technique | What's Hidden |
|------|-----------|---------------|
| `example_hidden.py` | Python comments + zero-width docstring | Plinian divider in comments, hex byte table, zero-width docstring |
| `example_hidden.js` | JavaScript zero-width + comments | Plinian divider in zero-width chars between tokens, hex comments |
| `example_hidden.c` | C comments + byte array | Plinian divider in block comments and `_cal_data[]` array literal |
| `example_hidden.css` | CSS comments + pseudo-elements | Plinian divider in comments, `::after` content, zero-width chars |
| `example_hidden.ini` | INI comments + byte table | Plinian divider in comments and calibration byte entries |
| `example_hidden.sh` | Shell whitespace + comments | Plinian divider in trailing whitespace and script comments |
| `example_hidden.sql` | SQL comments + byte checksums | Plinian divider in comments and per-byte checksum lines |
| `example_hidden.tex` | LaTeX comments | Plinian divider in TeX comments, base64, and hex |
| `example_hidden.toml` | TOML comments | Plinian divider in TOML comments, base64, and hex |

## How to Use

1. Open ST3GG in your browser
2. Go to the **Agent** tab
3. Upload any example file
4. Enable **Exhaustive Mode** for the most thorough analysis
5. Run the agent and watch it find the hidden data

## Unicode & Text Tricks (Plinian Divider)

| File | Technique | What's Hidden |
|------|-----------|---------------|
| `example_homoglyph.txt` | Cyrillic/Latin homoglyphs | Plinian divider in Cyrillic letter substitutions (а vs a, с vs c, etc.) |
| `example_variation_selector.txt` | Unicode variation selectors | Plinian divider in VS1 (U+FE01) presence/absence after letters |
| `example_combining_diacritics.txt` | Combining Grapheme Joiner | Plinian divider in invisible U+034F marks after letters |
| `example_confusable_whitespace.txt` | Unicode space variants | Plinian divider in en/em/thin space substitution (2 bits per space) |
| `example_emoji_substitution.txt` | Emoji pair encoding | Plinian divider in emoji choice (🌑=0 vs 🌚=1, etc.) |

## Network Protocol Steganography (Plinian Divider)

| File | Technique | What's Hidden |
|------|-----------|---------------|
| `example_dns_tunnel.pcap` | DNS query name tunneling | Plinian divider base32-encoded in DNS query labels |
| `example_icmp_steg.pcap` | ICMP echo payload | Plinian divider in ICMP ping request payloads |
| `example_tcp_covert.pcap` | TCP covert channel | Plinian divider in TCP ISN + timestamp option fields |
| `example_http_headers.pcap` | HTTP header smuggling | Plinian divider in custom X- headers, cookies |

## Image Format Tricks (Plinian Divider)

| File | Technique | What's Hidden |
|------|-----------|---------------|
| `example_polyglot.png.zip` | PNG+ZIP polyglot | Valid as both PNG image and ZIP archive with secret.txt |
| `example_filter_encoding.png` | PNG scanline filter types | Plinian divider in per-scanline filter byte choice (None=0, Sub=1) |
| `example_alpha_lsb.png` | Alpha channel LSB only | Plinian divider in transparency channel LSBs (RGB untouched) |

## Miscellaneous Techniques (Plinian Divider)

| File | Technique | What's Hidden |
|------|-----------|---------------|
| `example_key_ordering.json` | JSON key sort order | Plinian divider in object key ordering (alphabetical=0, reversed=1) |
| `example_capitalization.txt` | Letter case encoding | Plinian divider in word-initial capitalization (lower=0, upper=1) |
| `example_silence_interval.wav` | Audio silence timing | Plinian divider in silence gap durations (short=0, long=1) |

## More Unicode & Text Tricks (Plinian Divider)

| File | Technique | What's Hidden |
|------|-----------|---------------|
| `example_directional_override.txt` | Bidi overrides (RLO/LRO) | Plinian divider in directional control chars with PDF cancellation |
| `example_hangul_filler.txt` | Hangul filler (U+3164) | Plinian divider in Korean invisible filler vs regular space |
| `example_braille.txt` | Braille patterns (U+2800) | Plinian divider bytes mapped to Braille Unicode block |
| `example_math_alphanumeric.txt` | Math bold (U+1D400) | Plinian divider in normal vs mathematical bold letter substitution |
| `example_normalization.txt` | NFC vs NFD | Plinian divider in Unicode normalization form choice per word |
| `example_sentence_length.txt` | Sentence word count | Plinian divider in odd (=1) vs even (=0) word count sentences |
| `example_word_choice.txt` | Synonym substitution | Plinian divider in synonym A (=0) vs synonym B (=1) selection |
| `example_misspelling.txt` | Typo patterns | Plinian divider in correct (=0) vs deliberately misspelled (=1) words |

## More Network Protocol Steganography (Plinian Divider)

| File | Technique | What's Hidden |
|------|-----------|---------------|
| `example_ttl_covert.pcap` | IP TTL covert channel | Plinian divider bytes encoded directly in IP TTL field values |
| `example_ipid_covert.pcap` | IP ID field encoding | Plinian divider 2 bytes per packet in IP Identification field |
| `example_tcp_window.pcap` | TCP window size | Plinian divider 2 bytes per packet in TCP window size field |
| `example_tcp_urgent.pcap` | TCP urgent pointer | Plinian divider in TCP URG pointer with URG flag set |
| `example_dns_txt.pcap` | DNS TXT record | Plinian divider base64-encoded in DNS TXT response record |
| `example_covert_timing.pcap` | Covert timing channel | Plinian divider in inter-packet delays (10ms=0, 50ms=1) |
| `example_multibase.txt` | Multi-base encoding | Plinian divider in base16, base32, base64, and base85 |
| `example_morse.txt` | Morse code | Plinian divider encoded in dot-dash Morse alphabet |

## Advanced Image Techniques (Plinian Divider)

| File | Technique | What's Hidden |
|------|-----------|---------------|
| `example_pvd.png` | Pixel Value Differencing | Plinian divider in adjacent pixel pair difference parity |
| `example_histogram_shift.png` | Histogram shifting | Plinian divider via peak pixel value shifting (peak=0, peak+1=1) |
| `example_lsb_4bit.png` | LSB 4-bit per channel | Plinian divider using 4 lower bits per channel (high capacity) |
| `example_lsb_msb_first.png` | LSB MSB-first ordering | Plinian divider with reversed bit extraction order per byte |
| `example_bmp_dib.bmp` | BMP DIB header fields | Plinian divider in reserved header bytes + trailing data |
| `example_gif_disposal.gif` | GIF disposal method | Plinian divider in frame disposal flag bits |
| `example_jpeg_app.jpg` | JPEG APP segment | Plinian divider in custom APP14 segment (ST3GG identifier) |
| `example_ycbcr.png` | YCbCr color space | Plinian divider in Cb chrominance channel LSB after RGB conversion |
| `example_png_chunks_custom.png` | PNG custom chunks | Plinian divider in private stEg/sT3g ancillary PNG chunks |

## More Document & Archive Techniques (Plinian Divider)

| File | Technique | What's Hidden |
|------|-----------|---------------|
| `example_pdf_javascript.pdf` | PDF JavaScript | Plinian divider base64 in OpenAction JavaScript |
| `example_pdf_incremental.pdf` | PDF incremental update | Plinian divider in appended incremental update annotation |
| `example_pdf_forms.pdf` | PDF form fields | Plinian divider in hidden form field default values |
| `example_html_events.html` | HTML event handlers | Plinian divider in onclick, onload, onmouseover attributes |
| `example_xml_entities.xml` | XML entity declarations | Plinian divider in DOCTYPE entity definitions + per-byte entities |
| `example_nested.zip` | Nested ZIP archive | Plinian divider in inner ZIP comment + secret.txt inside ZIP-in-ZIP |
| `example_emoji_skin_tone.txt` | Emoji skin tone selectors | Plinian divider in skin tone modifier choice (4 tones = 2 bits) |
| `example_punycode.txt` | Punycode/IDN domains | Plinian divider bytes encoded as internationalized domain names |

## Final Techniques (Plinian Divider)

| File | Technique | What's Hidden |
|------|-----------|---------------|
| `example_jpeg_restart.jpg` | JPEG restart markers + COM | Plinian divider in RST marker indices + COM comment segment |
| `example_matched_pairs.png` | Matched pairs LSB | Plinian divider in pixel pair ordering (left>right=1, left<=right=0) |
| `example_scanline_filter.png` | PNG scanline filter abuse | Plinian divider in per-row filter byte choice (None=0, Sub=1) |
| `example_qr_steg.txt` | QR code data encoding | Plinian divider in QR data bit pattern + error correction analysis |

## Audio DSP Techniques (Plinian Divider)

| File | Technique | What's Hidden |
|------|-----------|---------------|
| `example_echo_hiding.wav` | Echo hiding | Plinian divider in echo delay patterns (short=0, long=1) |
| `example_phase_coding.wav` | Phase coding | Plinian divider in DFT phase of frequency bins per segment |
| `example_spread_spectrum.wav` | Spread spectrum (DSSS) | Plinian divider spread via PN sequence at low amplitude |
| `example_quantization_noise.wav` | Quantization noise | Plinian divider in 2nd LSB of 16-bit audio samples |

## Image DSP Techniques (Plinian Divider)

| File | Technique | What's Hidden |
|------|-----------|---------------|
| `example_bpcs.png` | BPCS | Plinian divider in complex 8x8 bit-plane blocks (complexity segmentation) |
| `example_dct_manual.png` | DCT coefficient | Plinian divider in mid-frequency DCT coefficients of 8x8 blocks |
| `example_dft.png` | DFT magnitude | Plinian divider in Fourier transform magnitude spectrum |
| `example_dwt_haar.png` | DWT Haar wavelet | Plinian divider in HH high-frequency wavelet subband |
| `example_subsampling.png` | Chroma subsampling | Plinian divider in 4:2:0 vs 4:4:4 chroma pattern per 2x2 block |

## Misc Techniques (Plinian Divider)

| File | Technique | What's Hidden |
|------|-----------|---------------|
| `example_self_extracting.sh` | Self-extracting archive | Plinian divider in base64 tar.gz payload embedded in shell script |
| `example_xattr.txt` | Extended attributes | Plinian divider in user.st3gg.payload xattr (+ b64, hex, flag) |
| `example_tls_cert.pem` | TLS certificate fields | Plinian divider in CN, SAN, extension fields of certificate structure |

## Regenerating Files

If you want to modify the hidden messages or create new samples:

```bash
python3 examples/generate_examples.py
```

Requires Python 3 with Pillow (`pip install Pillow`).
