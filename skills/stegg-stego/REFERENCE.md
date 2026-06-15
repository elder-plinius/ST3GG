# ST3GG Tool Reference

## stegg_encode — Full Arguments

| Arg | Type | Default | Description |
|---|---|---|---|
| `image_path` | str | required | Path to carrier image (PNG recommended) |
| `payload_text` | str | `""` | Text to hide (mutually exclusive with `payload_file`) |
| `payload_file` | str | `""` | Path to file whose bytes to hide |
| `output_path` | str | auto | Where to write stegged image |
| `channels` | str | `"RGB"` | Channel preset (see below) |
| `bits_per_channel` | int | `1` | Bits per channel, 1-8 |
| `strategy` | str | `"interleaved"` | Embedding strategy |
| `seed` | int | `0` | Random seed for randomized strategy |
| `password` | str | `""` | Encryption password (AES-256-GCM) |
| `compress` | bool | `true` | zlib-compress payload before encoding |

## stegg_decode — Full Arguments

| Arg | Type | Default | Description |
|---|---|---|---|
| `image_path` | str | required | Path to encoded image |
| `output_path` | str | `""` | Save extracted data to file |
| `auto_detect` | bool | `true` | Auto-detect config from STEG header |
| `channels` | str | `"RGB"` | Channel preset (manual mode) |
| `bits_per_channel` | int | `1` | Bits per channel (manual mode) |
| `strategy` | str | `"interleaved"` | Strategy (manual mode) |
| `seed` | int | `0` | Seed (manual mode) |
| `password` | str | `""` | Decryption password |

## stegg_inject_chunk — Full Arguments

| Arg | Type | Default | Description |
|---|---|---|---|
| `image_path` | str | required | Path to source PNG |
| `output_path` | str | required | Where to write modified PNG |
| `chunk_type` | str | `"tEXt"` | PNG chunk type (tEXt, zTXt, iTXt, or 4-char private) |
| `keyword` | str | `"Comment"` | Chunk keyword |
| `text` | str | `""` | Text content to inject |
| `compressed` | bool | `false` | Use zTXt compression |

## stegg_inject_exif — Full Arguments

| Arg | Type | Default | Description |
|---|---|---|---|
| `image_path` | str | required | Path to source image |
| `output_path` | str | required | Where to write modified image |
| `comment` | str | `""` | Image comment field |
| `author` | str | `""` | Author / artist field |
| `description` | str | `""` | Image description |
| `title` | str | `""` | Image title |
| `custom_fields` | str | `""` | JSON object of additional key-value pairs |

## Channel Presets (15 options)

`R`, `G`, `B`, `A`, `RG`, `RB`, `RA`, `GB`, `GA`, `BA`, `RGB`, `RGA`, `RBA`, `GBA`, `RGBA`

More channels = more capacity, more visual distortion.

## Bits Per Channel

| Bits | Visual Impact | Use Case |
|---|---|---|
| 1 (default) | Invisible to human eye | Covert operations, PoCs |
| 2-3 | Barely detectable | Good capacity/stealth tradeoff |
| 4+ | Visible artifacts | CTF, non-visual-fidelity scenarios |

## Strategies

| Strategy | Auto-Detect | Decode Needs | Status |
|---|---|---|---|
| `interleaved` (default) | Yes | Nothing extra | Working |
| `sequential` | No | Manual config | Working |
| `spread` | No | Manual config | Upstream decode bug |
| `randomized` | No | Manual config + seed | Upstream decode bug |

## All Analysis Actions (stegg_analysis_tool)

Call `stegg_list_analysis_tools` for the full live list. High-value actions:

| Action | Detects |
|---|---|
| `rs_analysis` | RS steganalysis — most sensitive LSB detector |
| `sample_pairs_analysis` | Complementary statistical approach to RS |
| `png_chi_square_analysis` | Chi-square on pixel value pairs |
| `png_bit_plane_analysis` | Visual attack on individual bit planes |
| `png_steg_signature_scan` | Known steg tool signatures (OpenStego, Steghide, etc.) |
| `png_detect_appended_data` | Data appended after IEND chunk |
| `png_detect_embedded_png` | PNG embedded inside another PNG |
| `png_color_histogram_analysis` | Color distribution anomalies |
| `png_filter_analysis` | PNG filter type analysis |
| `png_visual_attack` | LSB visual attack rendering |
| `detect_homoglyph_steg` | Unicode homoglyph substitution |
| `detect_unicode_steg` | Zero-width character steganography |
| `detect_whitespace_steg` | Whitespace-based encoding |
| `detect_variation_selector_steg` | Unicode variation selector abuse |
| `detect_combining_mark_steg` | Combining diacritical mark hiding |
| `detect_emoji_steg` | Emoji-based steganography |
| `detect_capitalization_steg` | Case-based encoding |
| `jpeg_decode` | JPEG-specific steg analysis |
| `audio_lsb_decode` | WAV audio LSB extraction |
| `pcap_decode` | Network capture steg analysis |
| `pdf_decode` | PDF steganography |
| `zip_decode` | ZIP archive steg analysis |
| `svg_decode` | SVG steganography |

## Injection Filename Templates

| Template | Target |
|---|---|
| `chatgpt_decoder` | ChatGPT image upload |
| `claude_decoder` | Claude image upload |
| `gemini_decoder` | Gemini image upload |
| `universal_decoder` | Any LLM |
| `system_override` | System prompt override |
| `roleplay_trigger` | Roleplay-based bypass |
| `dev_mode` | Developer mode activation |
| `subtle` | Low-profile injection |
