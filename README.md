<p align="center">
<pre>
     ███████╗████████╗██████╗  ██████╗  ██████╗
     ██╔════╝╚══██╔══╝╚════██╗██╔════╝ ██╔════╝
     ███████╗   ██║    █████╔╝██║  ███╗██║  ███╗
     ╚════██║   ██║    ╚═══██╗██║   ██║██║   ██║
     ███████║   ██║   ██████╔╝╚██████╔╝╚██████╔╝
     ╚══════╝   ╚═╝   ╚═════╝  ╚═════╝  ╚═════╝
</pre>
</p>

<div align="center">

<!-- ⊰ If you can read this, you understand steganography. The real flag is in the banner image. Decode it with ST3GG. ST3GG{s0urc3_v13w3r} LOVE PLINY ⊱ -->

### ⊰•-•✧ THE ULTIMATE STEGANOGRAPHY TOOLKIT ✧•-•⊱

**Hide anything. In any file. Across every modality. Undetected.**

👉 **Hosted site:** [ste.gg](https://ste.gg)

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://python.org)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](http://makeapullrequest.com)
[![60+ Examples](https://img.shields.io/badge/Examples-60%2B_files-purple.svg)](examples/)

```
       __                                    .--.
      /  '-.                               .'    '.
     / .-. |  ⊰ ev͏er͏y pi͏x͏el͏ ha͏s a͏ story͏ ⊱ /  .--.  \
    /.'   \|     you just can't see it    |  /    \  |
   //   |\  \                             | |      | |
  ||   | \  |    ⊰ LOVE PLINY ⊱          |  \    /  |
 /||   |  \ |                              \  '--'  /
/ ||__/   \/                                '.____..'
```

</div>

<p align="center">
<img src="examples/st3gg_banner.png" alt="ST3GG Banner" width="600">
<br><sub><i>This image contains hidden data. Can you find it?</i></sub>
</p>

---

## ⊰ What Is ST3GG? ⊱

**ST3GG**‍​‌​‌​​​​​‌​​‌‌​​​‌​​‌​​‌​‌​​‌‌‌​​‌​‌‌​​‌​​‌​​​​​​‌​​‌‌​​​‌​​‌‌‌‌​‌​‌​‌‌​​‌​​​‌​‌​‌​‌​​‌‌​​‌​​​​​​‌​‌‌​​‌​‌​​‌‌‌‌​‌​‌​‌​‌‍ is a feature-rich, open-source steganography toolkit that hides secret data inside images, audio, documents, network packets, and more — using **75+ encoding techniques** across every file format imaginable.

It runs **100% in your browser** (static site, no server) or as a **Python CLI/TUI/WebUI**. No data ever leaves your machine. Every technique that encodes also decodes. Every attack surface is also a detection surface.

> *⊰•-•✧ Some secrets are hidden in plain sight ✧•-•⊱*

---

## ⊰ Why ST3GG? ⊱

| Feature | Other Tools | **ST3GG** |
|---------|-------------|-----------|
| Channel Options | RGB only | **15 presets** (R, G, B, A, RG, RB, RA, GB, GA, BA, RGB, RGA, RBA, GBA, RGBA) |
| Bit Depth | 1 bit fixed | **1-8 bits per channel** (adjustable) |
| Encoding Strategies | Sequential | **4 strategies** (sequential, interleaved, spread, randomized) |
| Nested Steg | - | **Up to 11 layers deep** (Matryoshka mode) |
| Channel Cipher | - | **Novel cross-channel hopping** (GODMODE) |
| Compression Survival | - | **DCT mode survives JPEG/social media** |
| Smart Decode | - | **16+ config auto-detection** |
| Encryption | Basic/None | **AES-256-GCM + XOR** |
| Image Formats | PNG only | **PNG, JPEG, WebP, GIF** |
| File Types | Images only | **Images, audio, text, docs, network, archives, code** |
| Example Library | None | **60+ pre-encoded example files** |
| Browser-Based | - | **100% client-side JS, no server** |
| AI Agent | - | **Exhaustive AI-powered decoding across all methods** |

---

## ⊰ The Big Picture: Offense & Defense ⊱

ST3GG is a **dual-use** toolkit — built for both sides of the steganography battlefield.

### RED TEAM / Offense — Poisoning Simulations

Data exfiltration doesn't always look like data exfiltration. ST3GG lets red teams and researchers simulate **every known data smuggling vector** to test whether defenses actually catch them:

- **75+ encoding techniques** across images, audio, text, documents, network packets, archives, and code files
- **Polyglot file generation** — files that are simultaneously valid as two formats (PNG+ZIP)
- **Network protocol covert channels** — data hidden in DNS queries, ICMP payloads, TCP sequence numbers, HTTP headers
- **Unicode steganography** — invisible homoglyphs, zero-width chars, variation selectors, confusable whitespace
- **Compression-resistant encoding** — DCT mode survives JPEG re-compression on social media
- **Multi-layer nesting** — up to 11 recursive layers of steganography (Matryoshka mode)
- **Ghost Mode** — AES-256 encryption + bit scrambling + noise decoys for maximum evasion

*If your DLP can't catch it, you need to know that before the adversary does.*

### BLUE TEAM / Defense — ALLSIGHT Comprehensive Detection

The same toolkit that creates steganographic payloads also **detects and decodes them**. ST3GG's analysis engine provides full-spectrum visibility across all known data smuggling surfaces:

- **20+ detection functions** — chi-square analysis, bit-plane entropy, histogram analysis, signature scanning, STEG header detection
- **AI-powered exhaustive analysis** — autonomous agent tests every decoding method for the uploaded file type
- **File type identification** — magic byte detection for 20+ formats (PNG, JPEG, GIF, BMP, WebP, TIFF, ICO, SVG, WAV, AIFF, AU, MIDI, PCAP, PDF, ZIP, GZip, TAR, SQLite, and more)
- **Unicode steganography detection** — zero-width chars, homoglyphs, variation selectors, combining marks, confusable whitespace, emoji patterns
- **Whitespace analysis** — trailing space/tab encoding, Unicode space variant detection
- **Metadata forensics** — base64/hex string extraction, EXIF analysis, PNG chunk inspection
- **Network packet analysis** — PCAP parsing for covert channel indicators
- **146 automated tests** verifying detection accuracy with zero false negatives on known techniques

*See everything. Miss nothing. That's ALLSIGHT.*

> *⊰•-•✧ The best defense starts with understanding the offense ✧•-•⊱*

---

## ⊰ Who Is This For? ⊱

ST3GG isn't just a toy. Different communities use steganography tools for very different — and very real — reasons.

### Penetration Testers & Red Teams
Simulate data exfiltration through steganographic channels during engagements. Test whether endpoint DLP, SIEM rules, and network monitoring catch covert data smuggling across 75+ vectors. Generate adversarial payloads across every file type to validate detection coverage.

### Blue Teams & SOC Analysts
Use ALLSIGHT to scan suspicious files for hidden payloads. Run exhaustive analysis against every known encoding method. Build detection rules from the comprehensive example library. Train analysts on what steganographic artifacts look like in the wild.

### CTF Players & Competitive Hackers
The ultimate steg toolkit for Capture The Flag competitions. Encode and decode across every channel/bit/strategy combination. Auto-detect unknown configurations with Smart Scan. Unwrap multi-layered Matryoshka challenges automatically.

### Digital Forensics & Incident Response
Analyze seized media for steganographic communication channels. Detect hidden data in image attachments, document metadata, audio files, and network captures. Identify which encoding technique was used and extract the hidden payload.

### Privacy Researchers & Journalists
Explore steganography as a privacy-preserving communication channel. Understand the trade-offs between capacity, stealth, and compression survival. Test which techniques survive social media re-encoding for real-world deniable communication.

### Academics & Students
Study the full landscape of steganographic techniques across every modality. Use the 60+ example files as a teaching dataset. Benchmark new detection algorithms against known encodings. The codebase is well-documented and MIT-licensed for research.

### AI Safety & LLM Security
Test how AI systems handle steganographic content — hidden instructions in images, invisible Unicode in prompts, polyglot files that bypass content filters. Understand the data smuggling surface area that AI systems need to defend against.

### Data Loss Prevention (DLP) Vendors
Benchmark your DLP solution against ST3GG's 75+ encoding techniques. If your product can't detect data hidden in DNS query names, TCP sequence numbers, or invisible Unicode characters — your customers deserve to know. ST3GG is your adversarial test suite.

---

## ⊰ Megalithic Features ⊱

### GODMODE — Channel Cipher Steganography

*A novel approach where data hops between color channels like a cryptographic dance.*

Instead of hiding all data in one channel, GODMODE distributes bits across R, G, and B channels in a pattern that becomes your key:

```
Pattern: R1-G2-B1-RG2-B1
         │  │  │  │   └─ 1 bit in Blue
         │  │  │  └───── 2 bits in Red+Green
         │  │  └──────── 1 bit in Blue
         │  └─────────── 2 bits in Green
         └────────────── 1 bit in Red
```

Two modes: **Manual Pattern** (you define) or **Password Mode** (derived from passphrase + optional encryption). Embed via **LSB** (high capacity) or **DCT** (compression-resistant).

### Ghost Mode — Maximum Stealth

Triple-layer obfuscation for when the stakes are real:

1. **AES-256-GCM Encryption** — authenticated, military-grade
2. **Bit Scrambling** — Fisher-Yates shuffle with seeded PRNG
3. **50% Noise Decoys** — half the embedded bits are random noise

An attacker would need to know the channel pattern, the password for unscrambling, AND the decryption key. Trade-off: halves capacity.

### Matryoshka Mode — Recursive Nesting

Hide images within images within images — up to **11 layers deep**. The smart decoder automatically detects PNG magic bytes and recursively unwraps every layer. Russian nesting dolls, but for secrets.

### DCT Mode — Compression Resistant

Traditional LSB dies to JPEG compression. DCT mode embeds data in frequency-domain coefficients of 8x8 pixel blocks — the same way JPEG stores image data. **Survives social media re-encoding at quality 70%+.**

### AI Agent — Exhaustive Analysis

An autonomous AI agent that analyzes uploaded files using **all known decoding methods** for that file type. Powered by OpenRouter, it intelligently tests every steganographic technique — LSB extraction, metadata parsing, frequency analysis, unicode detection, and more.

---

## ⊰ 75+ Steganographic Techniques ⊱

ST3GG doesn't just hide data in images. It covers **every modality**:

### Image Techniques
LSB embedding (RGB, RGBA, grayscale) across PNG, BMP, TIFF, GIF, WebP, ICO, PPM, PGM — plus alpha channel LSB, PNG filter-type encoding, palette index manipulation, DCT frequency domain, PNG+ZIP polyglots, metadata injection (EXIF, XMP, tEXt chunks), and trailing data after IEND.

### Text & Unicode Techniques
Zero-width characters (ZWSP/ZWNJ/ZWJ), invisible ink (Unicode tag chars U+E0000), homoglyph substitution (Cyrillic/Latin), variation selectors, combining diacritics (CGJ), confusable whitespace (en/em/thin/hair spaces), whitespace encoding (space=0/tab=1), emoji substitution, and capitalization encoding.

### Audio Techniques
Sample LSB in WAV, AIFF, and AU formats. Silence interval timing (gap duration encodes bits). MIDI SysEx message embedding.

### Network Protocol Techniques
DNS tunneling (base32 in query labels), ICMP payload injection, TCP covert channels (ISN + timestamps), HTTP header smuggling (custom X- headers, cookies).

### Document & Archive Techniques
PDF (metadata streams + XMP + post-EOF), HTML (comments + hidden elements + data attributes + zero-width), XML (CDATA + PIs + namespaces), JSON (Unicode escapes + key ordering), CSV/YAML/TOML/INI (comment encoding + whitespace), RTF (hidden text groups), Markdown (HTML comments + link references), ZIP/TAR/GZip (comments + extended headers + extra fields), SQLite (hidden tables), and more.

### Code Techniques
Python, JavaScript, C, CSS, Shell, SQL, LaTeX — all with steganographic comments, hex byte tables, zero-width docstrings, and per-byte calibration entries.

> *⊰•-•✧ See the full catalog: [`examples/README.md`](examples/README.md) ✧•-•⊱*

---

## ⊰ Quick Start ⊱

### Browser (Recommended)

```bash
# Just open index.html — that's it. No server needed.
open index.html
```

Everything runs 100% client-side. No data ever leaves your machine.

### Python Tools

```bash
# Clone
git clone https://github.com/LYS10S/ST3GG.git
cd ST3GG

# Install
pip install -r requirements.txt

# Pick your interface
python webui.py       # Modern browser UI (NiceGUI)
python cli.py --help  # Command line
python tui.py         # Terminal UI (Textual)
```

### Encode from CLI

```bash
# Basic LSB encode
python cli.py encode image.png "your secret message" -o output.png

# GODMODE with password
python cli.py encode image.png "{GODMODE:ENABLED}" -o output.png

# Analyze a suspicious file
python cli.py analyze suspicious.png --full
```

---

## ⊰ Channel & Bit Depth ⊱

### 15 Channel Presets x 8 Bit Depths = 120 Combinations

| Preset | Stealth | Capacity | Best For |
|--------|---------|----------|----------|
| B (Blue, 1-bit) | Excellent | Low | Maximum invisibility |
| RGB (3-channel, 1-bit) | Very Good | Medium | Balanced |
| RGBA (4-channel, 4-bit) | Moderate | **4MB+** | Large file hiding |

### 4 Encoding Strategies

| Strategy | Description |
|----------|-------------|
| **Sequential** | Bits placed in pixel order (fastest) |
| **Interleaved** | Alternating pixels across image |
| **Spread** | Distributed evenly across entire image |
| **Randomized** | Pseudo-random placement (seeded PRNG) |

### Capacity Formula

```
Capacity = (Width x Height x Channels x BitsPerChannel) / 8 bytes
```

A 1920x1080 image with RGB 1-bit holds ~760KB. With RGBA 4-bit: **~4MB**.

---

## ⊰ Encryption ⊱

| Method | Strength | Speed | Use Case |
|--------|----------|-------|----------|
| **AES-256-GCM** | Maximum | Medium | Ghost Mode |
| **XOR Cipher** | Basic | Fast | Quick obfuscation |
| **None** | - | Fastest | When secrecy isn't needed |

---

## ⊰ Example Library ⊱

ST3GG ships with **60+ pre-encoded example files** spanning every technique — images, audio, documents, network captures, code files, and more. Each one contains a hidden message that the analysis tools can find.

```bash
# Regenerate all examples
python examples/generate_examples.py

# Run the full test suite (146 tests)
python test_examples.py
```

See [`examples/README.md`](examples/README.md) for the full catalog.

---

## ⊰ Project Structure ⊱

```
ST3GG/
├── index.html              # Browser UI (100% client-side)
├── steg_core.py            # Core LSB encoding/decoding engine
├── crypto.py               # AES-256-GCM + XOR encryption
├── analysis_tools.py       # 20+ detection & analysis functions
├── cli.py                  # Command-line interface
├── tui.py                  # Terminal UI (Textual)
├── webui.py                # Web UI (NiceGUI)
├── app.py                  # Core application logic
├── injector.py             # Metadata & filename injection
├── ascii_art.py            # Terminal art & animations
├── f5stego-lib.js          # F5 JPEG steganography (browser)
├── test_examples.py        # Test suite (146 tests)
├── examples/               # 60+ pre-encoded example files
│   ├── generate_examples.py
│   └── README.md
├── requirements.txt
└── pyproject.toml
```

---

## ⊰ Security Notes ⊱

- Standard LSB steganography is **statistically detectable** — chi-square and bit-plane analysis can reveal it
- **GODMODE Channel Cipher** increases resistance by hopping across channels unpredictably
- **Ghost Mode** adds encryption + scrambling + noise for maximum stealth
- **DCT mode** survives JPEG compression but has lower capacity
- Always **encrypt** sensitive data before embedding
- For maximum security: **Ghost Mode + DCT + strong password**

---

## ⊰ Contributing ⊱

PRs are welcome! Whether it's new steganographic techniques, better detection algorithms, or documentation improvements.

```bash
# Run tests before submitting
python test_examples.py

# Regenerate examples after changes
python examples/generate_examples.py
```

---

## ⊰ License ⊱

Apache License 2.0. See [LICENSE](LICENSE) for details.

This tool is intended for **authorized security research**, **CTF competitions**, **digital forensics education**, and **privacy research**. Use responsibly.

---

<div align="center">

```
⊰•-•✧•-•-⦑ ST3GG ⦒-•-•✧•-•⊱
  every pixel has a story
    you just can't see it
           🦕︁
```

*⊰ hidden in plain sight ⊱*

</div>

[//]: # (⊰ ST3GG{r34dm3_h4ck3r} - you found the hidden link reference! The Plinian divider lives in all things. LOVE PLINY ⊱)
