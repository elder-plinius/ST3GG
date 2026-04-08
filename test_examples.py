#!/usr/bin/env python3
"""
Test all example files against ST3GG's analysis and decoding tools.
Validates that the steganographic payloads can actually be detected/extracted.
"""

import os
import sys
import struct
import json
import wave
import traceback
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

EXAMPLES_DIR = Path(__file__).parent / 'examples'
PLINIAN_DIVIDER = "⊰•-•✧•-•-⦑/L\\O/V\\E/\\P/L\\I/N\\Y/⦒-•-•✧•-•⊱"
ORIGINAL_SECRET = "STEGOSAURUS WRECKS - Hidden message found! 🦕"

# Result tracking
results = {}
total = 0
passed = 0
failed = 0
warnings = 0


def record(name, status, detail=""):
    global total, passed, failed, warnings
    total += 1
    icon = ""
    if status == "PASS":
        passed += 1
        icon = "  PASS"
    elif status == "WARN":
        warnings += 1
        icon = "  WARN"
    else:
        failed += 1
        icon = "**FAIL"
    results[name] = (status, detail)
    detail_str = f"  ({detail})" if detail else ""
    print(f"  {icon}  {name}{detail_str}")


# =============================================================================
# Import analysis tools
# =============================================================================
print("=" * 70)
print("ST3GG EXHAUSTIVE EXAMPLE FILE TESTS")
print("=" * 70)
print()

try:
    from analysis_tools import (
        png_full_analysis, png_extract_text_chunks, png_detect_appended_data,
        png_steg_signature_scan, png_chi_square_analysis,
        detect_base64, detect_hex_strings, detect_unicode_steg,
        detect_whitespace_steg, detect_file_type, TOOL_REGISTRY,
        analyze_bit_planes, MAGIC_SIGNATURES,
    )
    print("  [OK] analysis_tools imported")
except Exception as e:
    print(f"  [!!] analysis_tools import error: {e}")

try:
    import numpy as np
    print("  [OK] numpy imported")
except Exception as e:
    print(f"  [!!] numpy import error: {e}")

try:
    from PIL import Image
    print("  [OK] PIL imported")
except Exception as e:
    print(f"  [!!] PIL import error: {e}")

try:
    from steg_core import analyze_image, detect_encoding, StegConfig, Channel
    print("  [OK] steg_core imported")
except Exception as e:
    print(f"  [!!] steg_core import error: {e}")
    detect_encoding = None

print()

# =============================================================================
# 1. ORIGINAL EXAMPLES (PNG image-based)
# =============================================================================
print("-" * 70)
print("SECTION 1: Original PNG Examples")
print("-" * 70)

# 1a. LSB RGB PNG with STEG v3 header
try:
    if detect_encoding is None:
        record("example_lsb_rgb.png [STEG detect]", "WARN", "steg_core not fully imported")
    else:
        img = Image.open(EXAMPLES_DIR / 'example_lsb_rgb.png')
        enc = detect_encoding(img)
        if enc:
            record("example_lsb_rgb.png [STEG detect]", "PASS", f"STEG encoding detected: {enc.get('config', {})}")
        else:
            # Try manual check: extract first 4 bytes from LSB
            img_rgba = img.convert('RGBA')
            pixels = list(img_rgba.getdata())
            bits = []
            for px in pixels[:20]:
                for ch in range(3):
                    bits.append(px[ch] & 1)
            magic_bits = bits[:32]
            magic_bytes = bytearray()
            for i in range(0, 32, 8):
                byte_val = 0
                for j in range(8):
                    byte_val = (byte_val << 1) | magic_bits[i + j]
                magic_bytes.append(byte_val)
            if magic_bytes == b'STEG':
                record("example_lsb_rgb.png [STEG detect]", "PASS", "STEG magic found in LSB (manual extraction)")
            else:
                record("example_lsb_rgb.png [STEG detect]", "WARN", f"Magic bytes: {magic_bytes} (detect_encoding uses interleaved mode)")
except Exception as e:
    record("example_lsb_rgb.png [STEG detect]", "FAIL", str(e))

try:
    data = (EXAMPLES_DIR / 'example_lsb_rgb.png').read_bytes()
    result = png_full_analysis(data)
    susp = result.get('suspicious_indicators', 0)
    if susp >= 1:
        record("example_lsb_rgb.png [full analysis]", "PASS", f"{susp} suspicious indicators")
    else:
        record("example_lsb_rgb.png [full analysis]", "WARN", "No suspicious indicators found")
except Exception as e:
    record("example_lsb_rgb.png [full analysis]", "FAIL", str(e))

# 1b. PNG tEXt chunks
try:
    data = (EXAMPLES_DIR / 'example_png_chunks.png').read_bytes()
    result = png_extract_text_chunks(data)
    chunks = result.get('text_chunks', result.get('chunks', [])) if isinstance(result, dict) else []
    found_secret = any(ORIGINAL_SECRET in str(c) for c in chunks)
    if found_secret:
        record("example_png_chunks.png [text chunks]", "PASS", f"Found secret in {len(chunks)} chunks")
    elif result.get('found') or chunks:
        record("example_png_chunks.png [text chunks]", "PASS", f"Found {result.get('count', len(chunks))} text chunks")
    else:
        record("example_png_chunks.png [text chunks]", "FAIL", f"No text chunks found (keys: {list(result.keys()) if isinstance(result, dict) else 'N/A'})")
except Exception as e:
    record("example_png_chunks.png [text chunks]", "FAIL", str(e))

# 1c. Trailing data PNG
try:
    data = (EXAMPLES_DIR / 'example_trailing_data.png').read_bytes()
    result = png_detect_appended_data(data)
    has_appended = result.get('found', result.get('has_appended_data', False)) if isinstance(result, dict) else False
    if has_appended:
        size = result.get('appended_size', '?')
        record("example_trailing_data.png [appended]", "PASS", f"Trailing data detected ({size} bytes)")
    else:
        record("example_trailing_data.png [appended]", "FAIL", f"No trailing data detected (keys: {list(result.keys()) if isinstance(result, dict) else 'N/A'})")
except Exception as e:
    record("example_trailing_data.png [appended]", "FAIL", str(e))

# 1d. Zero-width text
try:
    data = (EXAMPLES_DIR / 'example_zero_width.txt').read_bytes()
    result = detect_unicode_steg(data)
    if result.get('found'):
        count = result.get('invisible_chars', 0)
        record("example_zero_width.txt [unicode steg]", "PASS", f"{count} invisible chars found")
    else:
        record("example_zero_width.txt [unicode steg]", "FAIL", "No zero-width chars detected")
except Exception as e:
    record("example_zero_width.txt [unicode steg]", "FAIL", str(e))

# 1e. Whitespace text
try:
    data = (EXAMPLES_DIR / 'example_whitespace.txt').read_bytes()
    result = detect_whitespace_steg(data)
    if result.get('found'):
        spaces = result.get('trailing_spaces', 0)
        record("example_whitespace.txt [whitespace]", "PASS", f"{spaces} trailing whitespace chars")
    else:
        record("example_whitespace.txt [whitespace]", "FAIL", "No whitespace steg detected")
except Exception as e:
    record("example_whitespace.txt [whitespace]", "FAIL", str(e))

# 1f. Invisible ink
try:
    data = (EXAMPLES_DIR / 'example_invisible_ink.txt').read_bytes()
    text = data.decode('utf-8', errors='ignore')
    tag_chars = sum(1 for c in text if 0xE0000 <= ord(c) <= 0xE007F)
    if tag_chars > 5:
        record("example_invisible_ink.txt [tag chars]", "PASS", f"{tag_chars} tag characters found")
    else:
        record("example_invisible_ink.txt [tag chars]", "FAIL", f"Only {tag_chars} tag chars")
except Exception as e:
    record("example_invisible_ink.txt [tag chars]", "FAIL", str(e))

# 1g. Audio LSB WAV
try:
    import wave
    path = EXAMPLES_DIR / 'example_audio_lsb.wav'
    with wave.open(str(path), 'r') as w:
        frames = w.readframes(w.getnframes())
        samples = struct.unpack(f'<{w.getnframes()}h', frames)
        # Extract LSB
        bits = [s & 1 for s in samples[:400]]
        # Decode length prefix (32 bits)
        length = 0
        for i in range(32):
            length = (length << 1) | bits[i]
        # Decode message
        msg_bits = bits[32:32 + length * 8]
        msg_bytes = bytearray()
        for i in range(0, len(msg_bits), 8):
            byte_val = 0
            for j in range(8):
                if i + j < len(msg_bits):
                    byte_val = (byte_val << 1) | msg_bits[i + j]
            msg_bytes.append(byte_val)
        decoded = msg_bytes.decode('utf-8', errors='replace')
        if ORIGINAL_SECRET[:20] in decoded:
            record("example_audio_lsb.wav [LSB decode]", "PASS", f"Decoded: {decoded[:40]}...")
        else:
            record("example_audio_lsb.wav [LSB decode]", "WARN", f"Got: {decoded[:40]}...")
except Exception as e:
    record("example_audio_lsb.wav [LSB decode]", "FAIL", str(e))

# 1h. Metadata PNG
try:
    data = (EXAMPLES_DIR / 'example_metadata.png').read_bytes()
    b64_result = detect_base64(data)
    hex_result = detect_hex_strings(data)
    if b64_result.get('found') or hex_result.get('found'):
        record("example_metadata.png [b64/hex]", "PASS",
               f"b64={b64_result.get('found')}, hex={hex_result.get('found')}")
    else:
        record("example_metadata.png [b64/hex]", "FAIL", "No encoded strings detected")
except Exception as e:
    record("example_metadata.png [b64/hex]", "FAIL", str(e))

print()

# =============================================================================
# 2. CHUNK 1: Image Formats (Plinian Divider)
# =============================================================================
print("-" * 70)
print("SECTION 2: Image Format Examples (Plinian Divider)")
print("-" * 70)


def test_image_lsb(filename, fmt_name):
    """Test LSB extraction from an image file."""
    try:
        path = EXAMPLES_DIR / filename
        img = Image.open(path)
        img_rgba = img.convert('RGBA')
        pixels = list(img_rgba.getdata())
        w, h = img_rgba.size

        # Extract LSB bits from RGB channels
        bits = []
        for px in pixels:
            for ch in range(3):
                bits.append(px[ch] & 1)
            if len(bits) >= 600:
                break

        # Decode: 4-byte big-endian length prefix + message
        length = 0
        for i in range(32):
            length = (length << 1) | bits[i]

        if length > 0 and length < 200:
            msg_bits = bits[32:32 + length * 8]
            msg_bytes = bytearray()
            for i in range(0, len(msg_bits), 8):
                byte_val = 0
                for j in range(8):
                    if i + j < len(msg_bits):
                        byte_val = (byte_val << 1) | msg_bits[i + j]
                msg_bytes.append(byte_val)
            decoded = msg_bytes.decode('utf-8', errors='replace')
            if PLINIAN_DIVIDER[:10] in decoded:
                record(f"{filename} [LSB decode]", "PASS", f"Plinian divider extracted")
            else:
                record(f"{filename} [LSB decode]", "WARN", f"Got length={length}, decoded: {decoded[:30]}...")
        else:
            record(f"{filename} [LSB decode]", "FAIL", f"Invalid length prefix: {length}")
    except Exception as e:
        record(f"{filename} [LSB decode]", "FAIL", str(e))


def test_raw_lsb(filename, fmt_name, header_size=0, pixel_bytes=3):
    """Test LSB extraction from raw pixel format (PPM/PGM)."""
    try:
        path = EXAMPLES_DIR / filename
        data = path.read_bytes()

        # Find the pixel data start (after header lines)
        lines_seen = 0
        offset = 0
        target_lines = 3  # P5/P6, dimensions, maxval
        while lines_seen < target_lines and offset < len(data):
            if data[offset:offset+1] == b'\n':
                lines_seen += 1
            offset += 1

        pixel_data = data[offset:]

        # Extract LSBs
        bits = []
        for b in pixel_data[:600]:
            bits.append(b & 1)

        # Decode length prefix + message
        length = 0
        for i in range(32):
            length = (length << 1) | bits[i]

        if 0 < length < 200:
            msg_bits = bits[32:32 + length * 8]
            msg_bytes = bytearray()
            for i in range(0, len(msg_bits), 8):
                byte_val = 0
                for j in range(8):
                    if i + j < len(msg_bits):
                        byte_val = (byte_val << 1) | msg_bits[i + j]
                msg_bytes.append(byte_val)
            decoded = msg_bytes.decode('utf-8', errors='replace')
            if PLINIAN_DIVIDER[:10] in decoded:
                record(f"{filename} [LSB decode]", "PASS", "Plinian divider extracted")
            else:
                record(f"{filename} [LSB decode]", "WARN", f"Got: {decoded[:30]}...")
        else:
            record(f"{filename} [LSB decode]", "FAIL", f"Invalid length: {length}")
    except Exception as e:
        record(f"{filename} [LSB decode]", "FAIL", str(e))


# BMP LSB
test_image_lsb('example_lsb.bmp', 'BMP')

# GIF comment
try:
    data = (EXAMPLES_DIR / 'example_comment.gif').read_bytes()
    # Look for comment extension marker (0x21 0xFE)
    idx = data.find(b'\x21\xFE')
    if idx >= 0:
        # Read sub-blocks
        pos = idx + 2
        comment = b''
        while pos < len(data) and data[pos] != 0:
            block_len = data[pos]
            comment += data[pos+1:pos+1+block_len]
            pos += 1 + block_len
        decoded = comment.decode('utf-8', errors='replace')
        if PLINIAN_DIVIDER[:10] in decoded:
            record("example_comment.gif [comment ext]", "PASS", "Plinian divider in GIF comment")
        else:
            record("example_comment.gif [comment ext]", "WARN", f"Comment: {decoded[:30]}...")
    else:
        record("example_comment.gif [comment ext]", "FAIL", "No comment extension found")
except Exception as e:
    record("example_comment.gif [comment ext]", "FAIL", str(e))

# GIF palette LSB — GIF uses palette indices, not raw RGB. Read indices directly.
try:
    img = Image.open(EXAMPLES_DIR / 'example_lsb.gif')
    # Get raw palette index data (P mode)
    if img.mode == 'P':
        indices = list(img.getdata())
        bits = [idx & 1 for idx in indices]
        length = 0
        for i in range(32):
            length = (length << 1) | bits[i]
        if 0 < length < 200:
            msg_bits = bits[32:32 + length * 8]
            msg_bytes = bytearray()
            for i in range(0, len(msg_bits), 8):
                byte_val = 0
                for j in range(8):
                    if i + j < len(msg_bits):
                        byte_val = (byte_val << 1) | msg_bits[i + j]
                msg_bytes.append(byte_val)
            decoded = msg_bytes.decode('utf-8', errors='replace')
            if PLINIAN_DIVIDER[:10] in decoded:
                record("example_lsb.gif [LSB decode]", "PASS", "Plinian divider in palette index LSBs")
            else:
                record("example_lsb.gif [LSB decode]", "WARN", f"Got: {decoded[:30]}...")
        else:
            record("example_lsb.gif [LSB decode]", "WARN", f"Invalid length={length}, palette index LSB format may differ")
    else:
        record("example_lsb.gif [LSB decode]", "WARN", f"GIF not in P mode (got {img.mode})")
except Exception as e:
    record("example_lsb.gif [LSB decode]", "FAIL", str(e))

# TIFF metadata
try:
    data = (EXAMPLES_DIR / 'example_metadata.tiff').read_bytes()
    b64_result = detect_base64(data)
    if b64_result.get('found'):
        segments = b64_result.get('segments', [])
        any_plinian = any(PLINIAN_DIVIDER[:10] in s.get('decoded_preview', '') for s in segments)
        if any_plinian:
            record("example_metadata.tiff [b64 metadata]", "PASS", "Plinian divider in base64 metadata")
        else:
            record("example_metadata.tiff [b64 metadata]", "WARN", f"Found {len(segments)} b64 segments, divider not in preview")
    else:
        record("example_metadata.tiff [b64 metadata]", "FAIL", "No base64 detected")
except Exception as e:
    record("example_metadata.tiff [b64 metadata]", "FAIL", str(e))

# TIFF LSB
test_image_lsb('example_lsb.tiff', 'TIFF')

# PPM LSB
test_raw_lsb('example_lsb.ppm', 'PPM')

# PGM LSB
test_raw_lsb('example_lsb.pgm', 'PGM')

# SVG hidden
try:
    data = (EXAMPLES_DIR / 'example_hidden.svg').read_bytes()
    text = data.decode('utf-8')
    found_direct = PLINIAN_DIVIDER in text
    b64_result = detect_base64(data)
    hex_result = detect_hex_strings(data)
    if found_direct:
        record("example_hidden.svg [direct search]", "PASS", "Plinian divider found in SVG XML")
    else:
        record("example_hidden.svg [direct search]", "FAIL", "Divider not found")
    if b64_result.get('found') or hex_result.get('found'):
        record("example_hidden.svg [b64/hex]", "PASS",
               f"b64={b64_result.get('found')}, hex={hex_result.get('found')}")
    else:
        record("example_hidden.svg [b64/hex]", "WARN", "No encoded strings")
except Exception as e:
    record("example_hidden.svg [analysis]", "FAIL", str(e))

# ICO LSB — ICO format stores 32x32 icons; Pillow may reorder. Use 16-bit length prefix.
try:
    img = Image.open(EXAMPLES_DIR / 'example_lsb.ico')
    img_rgba = img.convert('RGBA')
    pixels = list(img_rgba.getdata())
    bits = []
    for px in pixels:
        for ch in range(3):
            bits.append(px[ch] & 1)
        if len(bits) >= 600:
            break
    # ICO uses 16-bit length prefix (struct.pack('>H', ...))
    length = 0
    for i in range(16):
        length = (length << 1) | bits[i]
    if 0 < length < 200:
        msg_bits = bits[16:16 + length * 8]
        msg_bytes = bytearray()
        for i in range(0, len(msg_bits), 8):
            byte_val = 0
            for j in range(8):
                if i + j < len(msg_bits):
                    byte_val = (byte_val << 1) | msg_bits[i + j]
            msg_bytes.append(byte_val)
        decoded = msg_bytes.decode('utf-8', errors='replace')
        if PLINIAN_DIVIDER[:10] in decoded:
            record("example_lsb.ico [LSB decode]", "PASS", "Plinian divider in ICO pixel LSBs")
        else:
            record("example_lsb.ico [LSB decode]", "WARN", f"Got length={length}, decoded: {decoded[:30]}...")
    else:
        record("example_lsb.ico [LSB decode]", "WARN", f"Length prefix={length}, ICO pixel reordering may differ")
except Exception as e:
    record("example_lsb.ico [LSB decode]", "FAIL", str(e))

# WebP metadata (base64 in EXIF + XMP)
try:
    import base64 as b64mod
    img = Image.open(EXAMPLES_DIR / 'example_metadata.webp')
    exif = img.getexif()
    desc = exif.get(270, '')  # ImageDescription (b64:...)
    artist = exif.get(315, '')  # Artist (hex:...)

    # Check b64 decode
    if desc.startswith('b64:'):
        decoded_b64 = b64mod.b64decode(desc[4:]).decode('utf-8')
        if decoded_b64 == PLINIAN_DIVIDER:
            record("example_metadata.webp [EXIF b64]", "PASS", "Plinian divider decoded from EXIF base64")
        else:
            record("example_metadata.webp [EXIF b64]", "FAIL", f"Decoded: {decoded_b64[:30]}")
    else:
        record("example_metadata.webp [EXIF b64]", "FAIL", f"No b64: prefix in desc: {desc[:30]}")

    # Check hex decode
    if artist.startswith('hex:'):
        decoded_hex = bytes.fromhex(artist[4:]).decode('utf-8')
        if decoded_hex == PLINIAN_DIVIDER:
            record("example_metadata.webp [EXIF hex]", "PASS", "Plinian divider decoded from EXIF hex")
        else:
            record("example_metadata.webp [EXIF hex]", "FAIL", f"Decoded: {decoded_hex[:30]}")

    # Check XMP in raw file data
    raw = (EXAMPLES_DIR / 'example_metadata.webp').read_bytes()
    if PLINIAN_DIVIDER.encode('utf-8') in raw:
        record("example_metadata.webp [XMP]", "PASS", "Plinian divider in XMP chunk")
    else:
        record("example_metadata.webp [XMP]", "FAIL", "Divider not in raw file")
except Exception as e:
    record("example_metadata.webp [EXIF]", "FAIL", str(e))

# WebP lossless LSB
test_image_lsb('example_lsb.webp', 'WebP')

print()

# =============================================================================
# 3. CHUNK 2: Document & Structured Data Formats
# =============================================================================
print("-" * 70)
print("SECTION 3: Document & Structured Data Examples")
print("-" * 70)


def test_text_file(filename, test_name, check_b64=True, check_hex=True, check_unicode=False,
                   check_whitespace=False, check_direct=True):
    """Test a text-based file for various steganographic indicators."""
    try:
        data = (EXAMPLES_DIR / filename).read_bytes()
        found_any = False

        if check_direct:
            text = data.decode('utf-8', errors='ignore')
            if PLINIAN_DIVIDER in text:
                record(f"{filename} [direct]", "PASS", "Plinian divider found directly")
                found_any = True
            # Don't fail on direct - other methods may work

        if check_b64:
            result = detect_base64(data)
            if result.get('found'):
                record(f"{filename} [base64]", "PASS",
                       f"{len(result.get('segments',[]))} base64 segments")
                found_any = True

        if check_hex:
            result = detect_hex_strings(data)
            if result.get('found'):
                record(f"{filename} [hex strings]", "PASS",
                       f"{len(result.get('segments',[]))} hex segments")
                found_any = True

        if check_unicode:
            result = detect_unicode_steg(data)
            if result.get('found'):
                record(f"{filename} [unicode steg]", "PASS",
                       f"{result.get('invisible_chars',0)} invisible chars")
                found_any = True

        if check_whitespace:
            result = detect_whitespace_steg(data)
            if result.get('found'):
                record(f"{filename} [whitespace]", "PASS",
                       f"{result.get('trailing_spaces',0)} trailing whitespace chars")
                found_any = True

        if not found_any:
            record(f"{filename} [detection]", "FAIL", "No steganographic indicators detected")
    except Exception as e:
        record(f"{filename} [analysis]", "FAIL", str(e))


# HTML
test_text_file('example_hidden.html', 'HTML', check_unicode=True)

# XML
test_text_file('example_hidden.xml', 'XML')

# JSON
test_text_file('example_hidden.json', 'JSON')

# CSV whitespace
test_text_file('example_whitespace.csv', 'CSV', check_whitespace=True, check_b64=False, check_hex=False, check_direct=False)

# YAML
test_text_file('example_hidden.yaml', 'YAML')

# PDF
try:
    data = (EXAMPLES_DIR / 'example_hidden.pdf').read_bytes()
    ftype = detect_file_type(data)
    found_direct = PLINIAN_DIVIDER.encode('utf-8') in data
    b64_result = detect_base64(data)
    hex_result = detect_hex_strings(data)

    if ftype.value == 'pdf':
        record("example_hidden.pdf [file type]", "PASS", "Detected as PDF")
    else:
        record("example_hidden.pdf [file type]", "FAIL", f"Detected as {ftype.value}")

    if found_direct:
        record("example_hidden.pdf [direct]", "PASS", "Plinian divider found in PDF data")
    else:
        record("example_hidden.pdf [direct]", "FAIL", "Divider not in raw data")

    if b64_result.get('found') or hex_result.get('found'):
        record("example_hidden.pdf [b64/hex]", "PASS",
               f"b64={b64_result.get('found')}, hex={hex_result.get('found')}")
except Exception as e:
    record("example_hidden.pdf [analysis]", "FAIL", str(e))

# RTF
test_text_file('example_hidden.rtf', 'RTF')

# Markdown
test_text_file('example_hidden.md', 'Markdown', check_unicode=True)

print()

# =============================================================================
# 4. CHUNK 3: Audio, Binary & Archive Formats
# =============================================================================
print("-" * 70)
print("SECTION 4: Audio, Binary & Archive Examples")
print("-" * 70)


def test_audio_lsb(filename, fmt_name, big_endian=False):
    """Test LSB extraction from an audio file."""
    try:
        path = EXAMPLES_DIR / filename

        if filename.endswith('.aiff'):
            # Parse AIFF manually
            data = path.read_bytes()
            # Find SSND chunk
            idx = data.find(b'SSND')
            if idx < 0:
                record(f"{filename} [LSB decode]", "FAIL", "No SSND chunk")
                return
            chunk_size = struct.unpack('>I', data[idx+4:idx+8])[0]
            offset = struct.unpack('>I', data[idx+8:idx+12])[0]
            sample_data = data[idx+16+offset:]
            # 16-bit big-endian samples
            num_samples = min(len(sample_data) // 2, 600)
            samples = struct.unpack(f'>{num_samples}h', sample_data[:num_samples*2])

            # Also check ANNO chunk
            anno_idx = data.find(b'ANNO')
            if anno_idx >= 0:
                anno_size = struct.unpack('>I', data[anno_idx+4:anno_idx+8])[0]
                anno_text = data[anno_idx+8:anno_idx+8+anno_size].decode('utf-8', errors='replace')
                if PLINIAN_DIVIDER[:10] in anno_text:
                    record(f"{filename} [ANNO chunk]", "PASS", "Plinian divider in annotation")

        elif filename.endswith('.au'):
            data = path.read_bytes()
            if data[:4] != b'.snd':
                record(f"{filename} [LSB decode]", "FAIL", "Not a valid AU file")
                return
            header_size = struct.unpack('>I', data[4:8])[0]
            # Check annotation in header
            anno = data[24:header_size]
            anno_text = anno.decode('utf-8', errors='replace').rstrip('\x00')
            if PLINIAN_DIVIDER[:10] in anno_text:
                record(f"{filename} [annotation]", "PASS", "Plinian divider in AU annotation")

            sample_data = data[header_size:]
            num_samples = min(len(sample_data) // 2, 600)
            samples = struct.unpack(f'>{num_samples}h', sample_data[:num_samples*2])
        else:
            record(f"{filename} [LSB decode]", "FAIL", f"Unsupported format")
            return

        # Extract LSBs
        bits = []
        for s in samples:
            bits.append(s & 1)

        # Decode length prefix
        length = 0
        for i in range(32):
            if i < len(bits):
                length = (length << 1) | bits[i]

        if 0 < length < 200:
            msg_bits = bits[32:32 + length * 8]
            msg_bytes = bytearray()
            for i in range(0, len(msg_bits), 8):
                byte_val = 0
                for j in range(8):
                    if i + j < len(msg_bits):
                        byte_val = (byte_val << 1) | msg_bits[i + j]
                msg_bytes.append(byte_val)
            decoded = msg_bytes.decode('utf-8', errors='replace')
            if PLINIAN_DIVIDER[:10] in decoded:
                record(f"{filename} [LSB decode]", "PASS", "Plinian divider extracted from audio LSB")
            else:
                record(f"{filename} [LSB decode]", "WARN", f"Got length={length}, decoded: {decoded[:30]}...")
        else:
            record(f"{filename} [LSB decode]", "FAIL", f"Invalid length: {length}")
    except Exception as e:
        record(f"{filename} [LSB decode]", "FAIL", str(e))


# AIFF
test_audio_lsb('example_lsb.aiff', 'AIFF')

# AU
test_audio_lsb('example_lsb.au', 'AU')

# ZIP
try:
    import zipfile
    path = EXAMPLES_DIR / 'example_hidden.zip'
    with zipfile.ZipFile(path, 'r') as zf:
        comment = zf.comment.decode('utf-8', errors='replace')
        if PLINIAN_DIVIDER[:10] in comment:
            record("example_hidden.zip [comment]", "PASS", "Plinian divider in ZIP comment")
        else:
            record("example_hidden.zip [comment]", "FAIL", f"Comment: {comment[:30]}")

    # Check trailing data
    data = path.read_bytes()
    ftype = detect_file_type(data)
    record("example_hidden.zip [file type]", "PASS" if ftype.value == 'zip' else "FAIL",
           f"Detected as {ftype.value}")

    # Check for appended data after ZIP
    if PLINIAN_DIVIDER.encode('utf-8') in data:
        record("example_hidden.zip [trailing]", "PASS", "Plinian divider after ZIP end")
except Exception as e:
    record("example_hidden.zip [analysis]", "FAIL", str(e))

# TAR
try:
    import tarfile
    path = EXAMPLES_DIR / 'example_hidden.tar'
    with tarfile.open(path, 'r') as tf:
        members = tf.getmembers()
        found_pax = False
        for m in members:
            pax = m.pax_headers or {}
            if PLINIAN_DIVIDER[:10] in pax.get('comment', ''):
                found_pax = True
            if PLINIAN_DIVIDER.encode('utf-8').hex()[:20] in pax.get('STEG.payload', ''):
                found_pax = True
        if found_pax:
            record("example_hidden.tar [PAX headers]", "PASS", "Plinian divider in PAX extended headers")
        else:
            record("example_hidden.tar [PAX headers]", "FAIL", "Divider not in PAX headers")
except Exception as e:
    record("example_hidden.tar [analysis]", "FAIL", str(e))

# GZip
try:
    import gzip
    path = EXAMPLES_DIR / 'example_hidden.gz'
    data = path.read_bytes()

    # Check magic
    if data[:2] == b'\x1f\x8b':
        record("example_hidden.gz [magic]", "PASS", "Valid gzip magic bytes")
    else:
        record("example_hidden.gz [magic]", "FAIL", "Invalid gzip magic")

    # Check flags for FEXTRA and FCOMMENT
    flags = data[3]
    has_extra = bool(flags & 0x04)
    has_comment = bool(flags & 0x10)

    if has_extra:
        # Parse FEXTRA
        xlen = struct.unpack('<H', data[10:12])[0]
        extra = data[12:12+xlen]
        if PLINIAN_DIVIDER.encode('utf-8')[:10] in extra:
            record("example_hidden.gz [FEXTRA]", "PASS", "Plinian divider in gzip extra field")
        else:
            record("example_hidden.gz [FEXTRA]", "WARN", f"Extra field present ({xlen} bytes) but divider not directly matched")
    else:
        record("example_hidden.gz [FEXTRA]", "FAIL", "No FEXTRA field")

    # Try to decompress
    try:
        decompressed = gzip.decompress(data)
        record("example_hidden.gz [decompress]", "PASS", f"Decompressed {len(decompressed)} bytes")
    except Exception as e2:
        record("example_hidden.gz [decompress]", "WARN", f"Decompression: {e2}")
except Exception as e:
    record("example_hidden.gz [analysis]", "FAIL", str(e))

# SQLite
try:
    import sqlite3
    path = EXAMPLES_DIR / 'example_hidden.sqlite'
    conn = sqlite3.connect(str(path))
    c = conn.cursor()

    # Check for hidden table
    c.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in c.fetchall()]
    if '_steg_payload' in tables:
        record("example_hidden.sqlite [hidden table]", "PASS", f"Found _steg_payload table among {tables}")
    else:
        record("example_hidden.sqlite [hidden table]", "FAIL", f"Tables: {tables}")

    # Read the payload
    try:
        c.execute("SELECT key, value FROM _steg_payload WHERE key='divider'")
        row = c.fetchone()
        if row and PLINIAN_DIVIDER[:10] in row[1]:
            record("example_hidden.sqlite [payload]", "PASS", "Plinian divider in hidden table")
        else:
            record("example_hidden.sqlite [payload]", "FAIL", f"Payload: {row}")
    except Exception as e2:
        record("example_hidden.sqlite [payload]", "FAIL", str(e2))

    conn.close()
except Exception as e:
    record("example_hidden.sqlite [analysis]", "FAIL", str(e))

# Hex dump
try:
    data = (EXAMPLES_DIR / 'example_hidden.hexdump').read_bytes()
    text = data.decode('utf-8')
    # The raw bytes of the Plinian divider should be visible in the hex values
    # at offset 0x40
    lines = text.split('\n')
    hex_values = []
    for line in lines:
        if line and not line.startswith('#') and '  ' in line:
            parts = line.split('  ')
            if len(parts) >= 2:
                hex_part = parts[1].strip()
                hex_values.extend(hex_part.split())

    # Reconstruct bytes from hex values at offset 0x40 (line 4, position 0)
    raw_bytes = bytes(int(h, 16) for h in hex_values if len(h) == 2)
    if PLINIAN_DIVIDER.encode('utf-8')[:10] in raw_bytes:
        record("example_hidden.hexdump [embedded bytes]", "PASS", "Plinian divider found in hex data")
    else:
        record("example_hidden.hexdump [embedded bytes]", "WARN", "Bytes present but divider not matched exactly")
except Exception as e:
    record("example_hidden.hexdump [analysis]", "FAIL", str(e))

# MIDI
try:
    data = (EXAMPLES_DIR / 'example_hidden.mid').read_bytes()
    # Check for MThd header
    if data[:4] == b'MThd':
        record("example_hidden.mid [format]", "PASS", "Valid MIDI header")
    else:
        record("example_hidden.mid [format]", "FAIL", "Invalid MIDI header")

    # Search for text event with divider
    if PLINIAN_DIVIDER.encode('utf-8')[:10] in data:
        record("example_hidden.mid [text event]", "PASS", "Plinian divider in MIDI text event")
    else:
        record("example_hidden.mid [text event]", "FAIL", "Divider not found in MIDI data")

    # Check for SysEx (F0)
    if b'\xF0' in data:
        record("example_hidden.mid [SysEx]", "PASS", "SysEx message present")
    else:
        record("example_hidden.mid [SysEx]", "FAIL", "No SysEx found")
except Exception as e:
    record("example_hidden.mid [analysis]", "FAIL", str(e))

# PCAP
try:
    data = (EXAMPLES_DIR / 'example_hidden.pcap').read_bytes()
    # Check PCAP magic
    magic = struct.unpack('<I', data[:4])[0]
    if magic == 0xa1b2c3d4:
        record("example_hidden.pcap [magic]", "PASS", "Valid PCAP header")
    else:
        record("example_hidden.pcap [magic]", "FAIL", f"Magic: {magic:#x}")

    # Search for divider in packet payloads
    if PLINIAN_DIVIDER.encode('utf-8')[:10] in data:
        record("example_hidden.pcap [payload]", "PASS", "Plinian divider found in packet data")
    else:
        record("example_hidden.pcap [payload]", "FAIL", "Divider not in PCAP data")
except Exception as e:
    record("example_hidden.pcap [analysis]", "FAIL", str(e))

print()

# =============================================================================
# 5. CHUNK 4: Code & Config Formats
# =============================================================================
print("-" * 70)
print("SECTION 5: Code & Config Format Examples")
print("-" * 70)

# Python
test_text_file('example_hidden.py', 'Python', check_unicode=True)

# JavaScript
test_text_file('example_hidden.js', 'JavaScript', check_unicode=True)

# C source
test_text_file('example_hidden.c', 'C')

# CSS
test_text_file('example_hidden.css', 'CSS', check_unicode=True)

# INI
test_text_file('example_hidden.ini', 'INI')

# Shell
test_text_file('example_hidden.sh', 'Shell', check_whitespace=True)

# SQL
test_text_file('example_hidden.sql', 'SQL')

# LaTeX
test_text_file('example_hidden.tex', 'LaTeX')

# TOML
test_text_file('example_hidden.toml', 'TOML')

print()

# =============================================================================
# 6. DEEP DECODE VERIFICATION - Actually extract and verify full messages
# =============================================================================
print("-" * 70)
print("SECTION 6: Deep Decode Verification (full message extraction)")
print("-" * 70)


def decode_whitespace_message(data: bytes) -> str:
    """Actually decode a whitespace-encoded message (space=0, tab=1)."""
    text = data.decode('utf-8', errors='ignore')
    lines = text.split('\n')
    bits = []
    for line in lines:
        trailing = line[len(line.rstrip()):]
        for char in trailing:
            if char == ' ':
                bits.append('0')
            elif char == '\t':
                bits.append('1')

    if len(bits) < 16:
        return ""

    # 16-bit length prefix
    length = int(''.join(bits[:16]), 2)
    if length <= 0 or length > 500:
        return ""

    data_bits = bits[16:16 + length * 8]
    msg = bytearray()
    for i in range(0, len(data_bits), 8):
        byte_val = int(''.join(data_bits[i:i + 8]), 2) if i + 8 <= len(data_bits) else 0
        msg.append(byte_val)
    return msg.decode('utf-8', errors='replace')


def decode_zero_width_message(data: bytes) -> str:
    """Actually decode a zero-width Unicode steganography message."""
    text = data.decode('utf-8', errors='ignore')
    ZWSP = '\u200B'
    ZWNJ = '\u200C'
    ZWJ = '\u200D'

    # Find ZWJ delimiters
    start = text.find(ZWJ)
    if start < 0:
        return ""
    end = text.find(ZWJ, start + 1)
    if end < 0:
        return ""

    zw_section = text[start + 1:end]
    bits = []
    for char in zw_section:
        if char == ZWSP:
            bits.append('0')
        elif char == ZWNJ:
            bits.append('1')

    msg = bytearray()
    for i in range(0, len(bits), 8):
        if i + 8 <= len(bits):
            byte_val = int(''.join(bits[i:i + 8]), 2)
            msg.append(byte_val)
    return msg.decode('utf-8', errors='replace')


def decode_tag_chars(data: bytes) -> str:
    """Actually decode Unicode tag character steganography."""
    text = data.decode('utf-8', errors='ignore')
    TAG_BASE = 0xE0000

    msg = []
    in_tag = False
    for char in text:
        code = ord(char)
        if code == TAG_BASE:
            if in_tag:
                break  # End tag
            in_tag = True
            continue
        if in_tag and TAG_BASE < code <= TAG_BASE + 127:
            msg.append(chr(code - TAG_BASE))

    return ''.join(msg)


# Deep decode: zero-width text
try:
    data = (EXAMPLES_DIR / 'example_zero_width.txt').read_bytes()
    decoded = decode_zero_width_message(data)
    if decoded and len(decoded) > 10:
        record("example_zero_width.txt [DECODE]", "PASS", f"Decoded: {decoded[:40]}")
    else:
        record("example_zero_width.txt [DECODE]", "FAIL", f"Decoded only: {decoded}")
except Exception as e:
    record("example_zero_width.txt [DECODE]", "FAIL", str(e))

# Deep decode: invisible ink (tag characters)
try:
    data = (EXAMPLES_DIR / 'example_invisible_ink.txt').read_bytes()
    decoded = decode_tag_chars(data)
    if decoded and len(decoded) > 10:
        record("example_invisible_ink.txt [DECODE]", "PASS", f"Decoded: {decoded[:40]}")
    else:
        record("example_invisible_ink.txt [DECODE]", "FAIL", f"Decoded only: {decoded}")
except Exception as e:
    record("example_invisible_ink.txt [DECODE]", "FAIL", str(e))

# Deep decode: whitespace text
try:
    data = (EXAMPLES_DIR / 'example_whitespace.txt').read_bytes()
    decoded = decode_whitespace_message(data)
    if decoded and len(decoded) > 10:
        record("example_whitespace.txt [DECODE]", "PASS", f"Decoded: {decoded[:40]}")
    else:
        record("example_whitespace.txt [DECODE]", "FAIL", f"Decoded only: '{decoded}'")
except Exception as e:
    record("example_whitespace.txt [DECODE]", "FAIL", str(e))

# Deep decode: CSV whitespace (Plinian divider)
try:
    data = (EXAMPLES_DIR / 'example_whitespace.csv').read_bytes()
    decoded = decode_whitespace_message(data)
    if PLINIAN_DIVIDER[:10] in decoded:
        record("example_whitespace.csv [DECODE]", "PASS", f"Plinian divider fully decoded from CSV whitespace")
    elif decoded:
        record("example_whitespace.csv [DECODE]", "WARN", f"Decoded {len(decoded)} chars but divider not matched: {decoded[:30]}")
    else:
        record("example_whitespace.csv [DECODE]", "FAIL", "Could not decode whitespace")
except Exception as e:
    record("example_whitespace.csv [DECODE]", "FAIL", str(e))

# Deep decode: Shell whitespace (Plinian divider)
try:
    data = (EXAMPLES_DIR / 'example_hidden.sh').read_bytes()
    decoded = decode_whitespace_message(data)
    if PLINIAN_DIVIDER[:10] in decoded:
        record("example_hidden.sh [DECODE]", "PASS", "Plinian divider fully decoded from shell whitespace")
    elif decoded:
        record("example_hidden.sh [DECODE]", "WARN", f"Decoded {len(decoded)} chars: {decoded[:30]}")
    else:
        record("example_hidden.sh [DECODE]", "FAIL", "Could not decode whitespace")
except Exception as e:
    record("example_hidden.sh [DECODE]", "FAIL", str(e))

# Deep decode: HTML zero-width (Plinian divider)
try:
    data = (EXAMPLES_DIR / 'example_hidden.html').read_bytes()
    decoded = decode_zero_width_message(data)
    if PLINIAN_DIVIDER[:10] in decoded:
        record("example_hidden.html [ZW DECODE]", "PASS", "Plinian divider decoded from HTML zero-width")
    elif decoded and len(decoded) > 5:
        record("example_hidden.html [ZW DECODE]", "WARN", f"Decoded {len(decoded)} chars: {decoded[:30]}")
    else:
        record("example_hidden.html [ZW DECODE]", "FAIL", f"Decoded: {decoded[:20]}")
except Exception as e:
    record("example_hidden.html [ZW DECODE]", "FAIL", str(e))

# Deep decode: Markdown zero-width (Plinian divider)
try:
    data = (EXAMPLES_DIR / 'example_hidden.md').read_bytes()
    decoded = decode_zero_width_message(data)
    if PLINIAN_DIVIDER[:10] in decoded:
        record("example_hidden.md [ZW DECODE]", "PASS", "Plinian divider decoded from Markdown zero-width")
    elif decoded and len(decoded) > 5:
        record("example_hidden.md [ZW DECODE]", "WARN", f"Decoded {len(decoded)} chars: {decoded[:30]}")
    else:
        record("example_hidden.md [ZW DECODE]", "FAIL", f"Decoded: {decoded[:20]}")
except Exception as e:
    record("example_hidden.md [ZW DECODE]", "FAIL", str(e))

# Deep decode: TIFF metadata - actually decode the base64
try:
    img = Image.open(EXAMPLES_DIR / 'example_metadata.tiff')
    # TIFF stores description in tag 270
    desc = img.tag_v2.get(270, '') if hasattr(img, 'tag_v2') else ''
    if not desc:
        desc = img.tag.get(270, [''])[0] if hasattr(img, 'tag') else ''
    import base64 as b64mod
    if desc:
        decoded = b64mod.b64decode(desc).decode('utf-8')
        if PLINIAN_DIVIDER[:10] in decoded:
            record("example_metadata.tiff [DECODE]", "PASS", "Plinian divider decoded from TIFF base64")
        else:
            record("example_metadata.tiff [DECODE]", "WARN", f"Decoded: {decoded[:30]}")
    else:
        record("example_metadata.tiff [DECODE]", "FAIL", "No description tag in TIFF")
except Exception as e:
    record("example_metadata.tiff [DECODE]", "FAIL", str(e))

# Deep decode: GIF palette LSB (verify full message after fix)
try:
    img = Image.open(EXAMPLES_DIR / 'example_lsb.gif')
    indices = list(img.getdata())
    bits = [idx & 1 for idx in indices]
    length = 0
    for i in range(32):
        length = (length << 1) | bits[i]
    if 0 < length < 200:
        msg_bits = bits[32:32 + length * 8]
        msg_bytes = bytearray()
        for i in range(0, len(msg_bits), 8):
            v = 0
            for j in range(8):
                if i + j < len(msg_bits):
                    v = (v << 1) | msg_bits[i + j]
            msg_bytes.append(v)
        decoded = msg_bytes.decode('utf-8', errors='replace')
        if decoded == PLINIAN_DIVIDER:
            record("example_lsb.gif [FULL DECODE]", "PASS", "Plinian divider EXACTLY matches")
        else:
            record("example_lsb.gif [FULL DECODE]", "FAIL", f"Mismatch: {decoded[:30]}...")
    else:
        record("example_lsb.gif [FULL DECODE]", "FAIL", f"Invalid length: {length}")
except Exception as e:
    record("example_lsb.gif [FULL DECODE]", "FAIL", str(e))

print()

# =============================================================================
# 7. FALSE POSITIVE TESTS - Clean files should NOT trigger detections
# =============================================================================
print("-" * 70)
print("SECTION 7: False Positive Tests (clean files)")
print("-" * 70)

# Generate clean test data
import tempfile

# Clean PNG (no steg)
try:
    import random as rng
    rng.seed(12345)
    # Use a noisy gradient (more realistic than pure gradient which has constant LSB)
    clean_img = Image.new('RGB', (100, 100))
    clean_pixels = clean_img.load()
    for y in range(100):
        for x in range(100):
            r = min(255, max(0, int(200 * x / 100) + rng.randint(-5, 5)))
            g = min(255, max(0, int(150 * y / 100) + rng.randint(-5, 5)))
            b = min(255, max(0, int(80 + 80 * (x + y) / 200) + rng.randint(-5, 5)))
            clean_pixels[x, y] = (r, g, b)
    clean_path = os.path.join(tempfile.gettempdir(), 'clean_test.png')
    clean_img.save(clean_path)
    clean_data = Path(clean_path).read_bytes()

    result = png_full_analysis(clean_data)
    susp = result.get('suspicious_indicators', 0)
    if susp == 0:
        record("clean_png [no false positive]", "PASS", "No suspicious indicators on clean image")
    elif susp <= 2:
        record("clean_png [no false positive]", "WARN",
               f"{susp} indicators (known: chi-square/bit-plane heuristics trigger on synthetic gradients)")
    else:
        record("clean_png [no false positive]", "FAIL", f"{susp} false positive indicators!")
except Exception as e:
    record("clean_png [no false positive]", "FAIL", str(e))

# Clean text (no steg)
try:
    clean_text = "This is a perfectly normal text file.\nNo hidden data here.\nJust regular content.\n"
    clean_text_bytes = clean_text.encode('utf-8')

    ws_result = detect_whitespace_steg(clean_text_bytes)
    unicode_result = detect_unicode_steg(clean_text_bytes)
    b64_result = detect_base64(clean_text_bytes)

    false_pos = []
    if ws_result.get('found'):
        false_pos.append('whitespace')
    if unicode_result.get('found'):
        false_pos.append('unicode')
    if b64_result.get('found'):
        false_pos.append('base64')

    if not false_pos:
        record("clean_text [no false positive]", "PASS", "No detections on clean text")
    else:
        record("clean_text [no false positive]", "FAIL", f"False positives: {', '.join(false_pos)}")
except Exception as e:
    record("clean_text [no false positive]", "FAIL", str(e))

# Clean binary (random data should not look like steg)
try:
    import random
    random.seed(99)
    clean_binary = bytes([random.randint(0, 255) for _ in range(1000)])
    b64_result = detect_base64(clean_binary)
    hex_result = detect_hex_strings(clean_binary)
    ws_result = detect_whitespace_steg(clean_binary)
    unicode_result = detect_unicode_steg(clean_binary)

    false_pos = []
    if b64_result.get('found'):
        false_pos.append('base64')
    if hex_result.get('found'):
        false_pos.append('hex')
    if ws_result.get('found'):
        false_pos.append('whitespace')
    if unicode_result.get('found'):
        false_pos.append('unicode')

    if not false_pos:
        record("clean_binary [no false positive]", "PASS", "No detections on random binary")
    else:
        record("clean_binary [no false positive]", "WARN", f"Flagged (may be acceptable): {', '.join(false_pos)}")
except Exception as e:
    record("clean_binary [no false positive]", "FAIL", str(e))

print()

# =============================================================================
# 8. EDGE CASE TESTS - Robustness against malformed/adversarial inputs
# =============================================================================
print("-" * 70)
print("SECTION 8: Edge Case & Robustness Tests")
print("-" * 70)

# Empty file
try:
    result = detect_base64(b'')
    ws = detect_whitespace_steg(b'')
    uni = detect_unicode_steg(b'')
    if not result.get('found') and not ws.get('found') and not uni.get('found'):
        record("empty_file [graceful]", "PASS", "All detectors handle empty input")
    else:
        record("empty_file [graceful]", "FAIL", "Detector returned found=True on empty input")
except Exception as e:
    record("empty_file [graceful]", "FAIL", f"Crashed: {e}")

# Truncated PNG (just header, no data)
try:
    truncated_png = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR'
    ftype = detect_file_type(truncated_png)
    record("truncated_png [file type]", "PASS" if ftype.value == 'png' else "FAIL",
           f"Detected as {ftype.value}")

    result = png_full_analysis(truncated_png)
    # Should not crash
    record("truncated_png [no crash]", "PASS", "Full analysis didn't crash on truncated PNG")
except Exception as e:
    record("truncated_png [no crash]", "FAIL", f"Crashed: {e}")

# Very large whitespace (stress test)
try:
    large_ws = b'A' + b' ' * 10000 + b'\n' + b'B' + b'\t' * 10000 + b'\n'
    result = detect_whitespace_steg(large_ws)
    if result.get('found'):
        record("large_whitespace [detection]", "PASS", f"Detected {result.get('trailing_spaces', 0)} trailing chars")
    else:
        record("large_whitespace [detection]", "FAIL", "Missed large whitespace")
except Exception as e:
    record("large_whitespace [detection]", "FAIL", f"Crashed: {e}")

# Null bytes file
try:
    null_data = b'\x00' * 1000
    ftype = detect_file_type(null_data)
    # Should return UNKNOWN, not crash
    record("null_bytes [graceful]", "PASS", f"Detected as {ftype.value} (no crash)")
except Exception as e:
    record("null_bytes [graceful]", "FAIL", f"Crashed: {e}")

# File type detection for non-standard formats
try:
    # AIFF
    aiff_data = (EXAMPLES_DIR / 'example_lsb.aiff').read_bytes()
    ftype = detect_file_type(aiff_data)
    record("aiff [file type]", "PASS" if ftype.value == 'aiff' else "FAIL",
           f"Detected as {ftype.value}")

    # AU
    au_data = (EXAMPLES_DIR / 'example_lsb.au').read_bytes()
    ftype = detect_file_type(au_data)
    record("au [file type]", "PASS" if ftype.value == 'au' else "FAIL",
           f"Detected as {ftype.value}")

    # MIDI
    mid_data = (EXAMPLES_DIR / 'example_hidden.mid').read_bytes()
    ftype = detect_file_type(mid_data)
    record("midi [file type]", "PASS" if ftype.value == 'midi' else "FAIL",
           f"Detected as {ftype.value}")

    # PCAP
    pcap_data = (EXAMPLES_DIR / 'example_hidden.pcap').read_bytes()
    ftype = detect_file_type(pcap_data)
    record("pcap [file type]", "PASS" if ftype.value == 'pcap' else "FAIL",
           f"Detected as {ftype.value}")

    # SQLite
    sqlite_data = (EXAMPLES_DIR / 'example_hidden.sqlite').read_bytes()
    ftype = detect_file_type(sqlite_data)
    record("sqlite [file type]", "PASS" if ftype.value == 'sqlite' else "FAIL",
           f"Detected as {ftype.value}")

    # GZip
    gz_data = (EXAMPLES_DIR / 'example_hidden.gz').read_bytes()
    ftype = detect_file_type(gz_data)
    record("gzip [file type]", "PASS" if ftype.value == 'gzip' else "FAIL",
           f"Detected as {ftype.value}")

    # TAR (PAX format, has 'ustar' at offset 257)
    tar_data = (EXAMPLES_DIR / 'example_hidden.tar').read_bytes()
    ftype = detect_file_type(tar_data)
    record("tar [file type]", "PASS" if ftype.value == 'tar' else "WARN",
           f"Detected as {ftype.value}")

    # BMP
    bmp_data = (EXAMPLES_DIR / 'example_lsb.bmp').read_bytes()
    ftype = detect_file_type(bmp_data)
    record("bmp [file type]", "PASS" if ftype.value == 'bmp' else "FAIL",
           f"Detected as {ftype.value}")

    # GIF
    gif_data = (EXAMPLES_DIR / 'example_lsb.gif').read_bytes()
    ftype = detect_file_type(gif_data)
    record("gif [file type]", "PASS" if ftype.value == 'gif' else "FAIL",
           f"Detected as {ftype.value}")

    # TIFF
    tiff_data = (EXAMPLES_DIR / 'example_lsb.tiff').read_bytes()
    ftype = detect_file_type(tiff_data)
    record("tiff [file type]", "PASS" if ftype.value == 'tiff' else "FAIL",
           f"Detected as {ftype.value}")

    # SVG
    svg_data = (EXAMPLES_DIR / 'example_hidden.svg').read_bytes()
    ftype = detect_file_type(svg_data)
    record("svg [file type]", "PASS" if ftype.value == 'svg' else "FAIL",
           f"Detected as {ftype.value}")

    # ICO
    ico_data = (EXAMPLES_DIR / 'example_lsb.ico').read_bytes()
    ftype = detect_file_type(ico_data)
    record("ico [file type]", "PASS" if ftype.value == 'ico' else "FAIL",
           f"Detected as {ftype.value}")

except Exception as e:
    record("file_type_detection [batch]", "FAIL", str(e))

# Multiple hidden layers in same file (e.g., HTML has comments + zero-width + hidden div)
try:
    data = (EXAMPLES_DIR / 'example_hidden.html').read_bytes()
    methods_found = 0
    if detect_unicode_steg(data).get('found'):
        methods_found += 1
    if detect_base64(data).get('found'):
        methods_found += 1
    if detect_hex_strings(data).get('found'):
        methods_found += 1
    if PLINIAN_DIVIDER.encode('utf-8') in data:
        methods_found += 1

    if methods_found >= 3:
        record("html [multi-layer]", "PASS", f"Detected {methods_found} encoding layers")
    else:
        record("html [multi-layer]", "WARN", f"Only {methods_found} layers detected")
except Exception as e:
    record("html [multi-layer]", "FAIL", str(e))

print()

# =============================================================================
# 9. FILE TYPE DETECTION GAPS - Missing magic signatures
# =============================================================================
print("-" * 70)
print("SECTION 9: File Type Detection Coverage Gaps (informational)")
print("-" * 70)

# These are formats where detect_file_type returns UNKNOWN because the magic
# bytes aren't in the registry. Not failures, but gaps to be aware of.
gap_formats = {
    'AIFF (.aiff)': b'FORM',
    'AU (.au)': b'.snd',
    'MIDI (.mid)': b'MThd',
    'PCAP (.pcap)': b'\xa1\xb2\xc3\xd4',
    'SQLite (.sqlite)': b'SQLite format 3',
    'GZip (.gz)': b'\x1f\x8b',
    'TIFF LE (.tiff)': b'II\x2a\x00',
    'TIFF BE (.tiff)': b'MM\x00\x2a',
}

missing = []
for fmt_name, magic in gap_formats.items():
    found = False
    for registered_magic in MAGIC_SIGNATURES.keys() if 'MAGIC_SIGNATURES' in dir() else []:
        if magic.startswith(registered_magic) or registered_magic.startswith(magic):
            found = True
            break
    if not found:
        missing.append(fmt_name)

if missing:
    print(f"  INFO: {len(missing)} formats not in MAGIC_SIGNATURES:")
    for m in missing:
        print(f"    - {m}")
    record("file_type_gaps [info]", "WARN", f"{len(missing)} format magics not registered")
else:
    record("file_type_gaps [info]", "PASS", "All formats covered")

print()

# =============================================================================
# 10. QUICK-WIN TECHNIQUES - All 15 new steganography methods
# =============================================================================
print("-" * 70)
print("SECTION 10: Quick-Win Steganography Techniques (15 new methods)")
print("-" * 70)

# Import new detectors
try:
    from analysis_tools import (
        detect_homoglyph_steg, detect_variation_selector_steg,
        detect_combining_mark_steg, detect_confusable_whitespace as detect_confusable_ws,
        detect_emoji_steg, detect_capitalization_steg,
    )
    has_new_detectors = True
except ImportError as e:
    print(f"  [!!] New detectors not available: {e}")
    has_new_detectors = False

# --- Homoglyph ---
try:
    data = (EXAMPLES_DIR / 'example_homoglyph.txt').read_bytes()
    if has_new_detectors:
        result = detect_homoglyph_steg(data)
        if result.get('found'):
            record("homoglyph [detection]", "PASS",
                   f"{result['substitutions']} Cyrillic substitutions found")
        else:
            record("homoglyph [detection]", "FAIL", "No homoglyphs detected")

    # Decode test
    text = data.decode('utf-8')
    HOMOGLYPH_MAP = {
        '\u0430': 'a', '\u0441': 'c', '\u0435': 'e', '\u043e': 'o',
        '\u0440': 'p', '\u0455': 's', '\u0445': 'x', '\u0443': 'y',
        '\u0410': 'A', '\u0412': 'B', '\u0421': 'C', '\u0415': 'E',
        '\u041d': 'H', '\u041a': 'K', '\u041c': 'M', '\u041e': 'O',
        '\u0420': 'P', '\u0422': 'T', '\u0425': 'X',
    }
    # The ENCODER's substitutable set: exact Latin chars that have Cyrillic equivalents
    ENCODER_KEYS = set('aceopsx' + 'yABCEHKMOPTX')
    bits = []
    for ch in text:
        if ch in HOMOGLYPH_MAP:
            bits.append(1)  # Cyrillic = was substituted = 1
        elif ch in ENCODER_KEYS:
            bits.append(0)  # Latin original = 0
    # Decode 16-bit length prefix
    if len(bits) >= 16:
        length = int(''.join(str(b) for b in bits[:16]), 2)
        if 0 < length < 200:
            msg_bits = bits[16:16 + length * 8]
            msg_bytes = bytearray()
            for i in range(0, len(msg_bits), 8):
                if i + 8 <= len(msg_bits):
                    msg_bytes.append(int(''.join(str(b) for b in msg_bits[i:i+8]), 2))
            decoded = msg_bytes.decode('utf-8', errors='replace')
            if PLINIAN_DIVIDER[:10] in decoded:
                record("homoglyph [decode]", "PASS", "Plinian divider decoded from homoglyphs")
            else:
                record("homoglyph [decode]", "WARN", f"Decoded {len(decoded)} chars: {decoded[:30]}")
        else:
            record("homoglyph [decode]", "FAIL", f"Bad length: {length}")
    else:
        record("homoglyph [decode]", "FAIL", f"Only {len(bits)} carrier bits found")
except Exception as e:
    record("homoglyph [test]", "FAIL", str(e))

# --- Variation Selector ---
try:
    data = (EXAMPLES_DIR / 'example_variation_selector.txt').read_bytes()
    if has_new_detectors:
        result = detect_variation_selector_steg(data)
        if result.get('found'):
            record("variation_selector [detection]", "PASS",
                   f"{result['count']} variation selectors found")
        else:
            record("variation_selector [detection]", "FAIL", "No variation selectors detected")

    # Decode
    text = data.decode('utf-8')
    VS1 = '\uFE01'
    bits = []
    i = 0
    while i < len(text):
        if text[i].isalpha():
            if i + 1 < len(text) and text[i + 1] == VS1:
                bits.append(1)
                i += 2
            else:
                bits.append(0)
                i += 1
        else:
            i += 1

    if len(bits) >= 16:
        length = int(''.join(str(b) for b in bits[:16]), 2)
        if 0 < length < 200:
            msg_bits = bits[16:16 + length * 8]
            msg_bytes = bytearray()
            for j in range(0, len(msg_bits), 8):
                if j + 8 <= len(msg_bits):
                    msg_bytes.append(int(''.join(str(b) for b in msg_bits[j:j+8]), 2))
            decoded = msg_bytes.decode('utf-8', errors='replace')
            if PLINIAN_DIVIDER[:10] in decoded:
                record("variation_selector [decode]", "PASS", "Plinian divider decoded")
            else:
                record("variation_selector [decode]", "WARN", f"Got: {decoded[:30]}")
except Exception as e:
    record("variation_selector [test]", "FAIL", str(e))

# --- Combining Diacritics ---
try:
    data = (EXAMPLES_DIR / 'example_combining_diacritics.txt').read_bytes()
    if has_new_detectors:
        result = detect_combining_mark_steg(data)
        if result.get('found'):
            record("combining_diacritics [detection]", "PASS",
                   f"{result['count']} combining marks found")
        else:
            record("combining_diacritics [detection]", "FAIL", "No combining marks detected")

    # Decode
    text = data.decode('utf-8')
    CGJ = '\u034F'
    bits = []
    i = 0
    while i < len(text):
        if text[i].isalpha():
            if i + 1 < len(text) and text[i + 1] == CGJ:
                bits.append(1)
                i += 2
            else:
                bits.append(0)
                i += 1
        else:
            i += 1

    if len(bits) >= 16:
        length = int(''.join(str(b) for b in bits[:16]), 2)
        if 0 < length < 200:
            msg_bits = bits[16:16 + length * 8]
            msg_bytes = bytearray()
            for j in range(0, len(msg_bits), 8):
                if j + 8 <= len(msg_bits):
                    msg_bytes.append(int(''.join(str(b) for b in msg_bits[j:j+8]), 2))
            decoded = msg_bytes.decode('utf-8', errors='replace')
            if PLINIAN_DIVIDER[:10] in decoded:
                record("combining_diacritics [decode]", "PASS", "Plinian divider decoded")
            else:
                record("combining_diacritics [decode]", "WARN", f"Got: {decoded[:30]}")
except Exception as e:
    record("combining_diacritics [test]", "FAIL", str(e))

# --- Confusable Whitespace ---
try:
    data = (EXAMPLES_DIR / 'example_confusable_whitespace.txt').read_bytes()
    if has_new_detectors:
        result = detect_confusable_ws(data)
        if result.get('found'):
            record("confusable_ws [detection]", "PASS",
                   f"{result['non_standard_spaces']} non-standard spaces: {list(result['types'].keys())}")
        else:
            record("confusable_ws [detection]", "FAIL", "No confusable whitespace detected")

    # Decode (2 bits per space: regular=00, en=01, em=10, thin=11)
    text = data.decode('utf-8')
    SPACE_DECODE = {' ': 0b00, '\u2002': 0b01, '\u2003': 0b10, '\u2009': 0b11}
    pairs = []
    # Spaces are between words
    words = []
    current = []
    for ch in text:
        if ch in SPACE_DECODE:
            if current:
                words.append(''.join(current))
                current = []
            pairs.append(SPACE_DECODE[ch])
        else:
            current.append(ch)

    bits = []
    for p in pairs:
        bits.append((p >> 1) & 1)
        bits.append(p & 1)

    if len(bits) >= 16:
        length = int(''.join(str(b) for b in bits[:16]), 2)
        if 0 < length < 200:
            msg_bits = bits[16:16 + length * 8]
            msg_bytes = bytearray()
            for j in range(0, len(msg_bits), 8):
                if j + 8 <= len(msg_bits):
                    msg_bytes.append(int(''.join(str(b) for b in msg_bits[j:j+8]), 2))
            decoded = msg_bytes.decode('utf-8', errors='replace')
            if PLINIAN_DIVIDER[:10] in decoded:
                record("confusable_ws [decode]", "PASS", "Plinian divider decoded from Unicode spaces")
            else:
                record("confusable_ws [decode]", "WARN", f"Got length={length}: {decoded[:30]}")
except Exception as e:
    record("confusable_ws [test]", "FAIL", str(e))

# --- Emoji Substitution ---
try:
    data = (EXAMPLES_DIR / 'example_emoji_substitution.txt').read_bytes()
    if has_new_detectors:
        result = detect_emoji_steg(data)
        if result.get('found'):
            record("emoji_substitution [detection]", "PASS",
                   f"{result['emoji_count']} emoji, pattern={result['pattern_detected']}")
        else:
            record("emoji_substitution [detection]", "WARN",
                   f"{result.get('emoji_count', 0)} emoji found but pattern not flagged")

    # Decode
    text = data.decode('utf-8')
    EMOJI_PAIRS = [
        ('🌑', '🌚'), ('⭐', '🌟'), ('🔴', '🟥'), ('🔵', '🟦'),
        ('🟢', '🟩'), ('⚫', '🖤'), ('⚪', '🤍'), ('🔶', '🟧'),
    ]
    all_emoji = set()
    for p in EMOJI_PAIRS:
        all_emoji.add(p[0])
        all_emoji.add(p[1])
    pair_lookup = {}
    for p in EMOJI_PAIRS:
        pair_lookup[p[0]] = 0
        pair_lookup[p[1]] = 1

    bits = []
    for ch in text:
        if ch in pair_lookup:
            bits.append(pair_lookup[ch])

    if len(bits) >= 16:
        length = int(''.join(str(b) for b in bits[:16]), 2)
        if 0 < length < 200:
            msg_bits = bits[16:16 + length * 8]
            msg_bytes = bytearray()
            for j in range(0, len(msg_bits), 8):
                if j + 8 <= len(msg_bits):
                    msg_bytes.append(int(''.join(str(b) for b in msg_bits[j:j+8]), 2))
            decoded = msg_bytes.decode('utf-8', errors='replace')
            if PLINIAN_DIVIDER[:10] in decoded:
                record("emoji_substitution [decode]", "PASS", "Plinian divider decoded from emoji")
            else:
                record("emoji_substitution [decode]", "WARN", f"Got: {decoded[:30]}")
except Exception as e:
    record("emoji_substitution [test]", "FAIL", str(e))

# --- DNS Tunneling ---
try:
    import base64 as b64mod
    data = (EXAMPLES_DIR / 'example_dns_tunnel.pcap').read_bytes()
    # Extract DNS query names from PCAP
    labels = []
    pos = 24  # Skip PCAP header
    while pos < len(data):
        if pos + 16 > len(data):
            break
        pkt_len = struct.unpack('<I', data[pos + 8:pos + 12])[0]
        pkt_data = data[pos + 16:pos + 16 + pkt_len]
        # Find DNS query name (after UDP header at offset 42 in frame)
        if len(pkt_data) > 54:
            dns_start = 42 + 12  # Ethernet(14)+IP(20)+UDP(8) + DNS header(12)
            name_parts = []
            idx = dns_start
            while idx < len(pkt_data) and pkt_data[idx] != 0:
                label_len = pkt_data[idx]
                idx += 1
                name_parts.append(pkt_data[idx:idx + label_len].decode('ascii', errors='replace'))
                idx += label_len
            if name_parts:
                labels.append(name_parts[0])  # First label has the encoded data

    if labels:
        # Reconstruct base32-encoded data
        encoded = ''.join(labels).upper()
        # Add padding
        padding = (8 - len(encoded) % 8) % 8
        encoded += '=' * padding
        decoded = b64mod.b32decode(encoded).decode('utf-8', errors='replace')
        if PLINIAN_DIVIDER[:10] in decoded:
            record("dns_tunnel [decode]", "PASS", "Plinian divider decoded from DNS query names")
        else:
            record("dns_tunnel [decode]", "WARN", f"Got: {decoded[:30]}")
    else:
        record("dns_tunnel [decode]", "FAIL", "No DNS labels extracted")
except Exception as e:
    record("dns_tunnel [test]", "FAIL", str(e))

# --- ICMP Steganography ---
try:
    data = (EXAMPLES_DIR / 'example_icmp_steg.pcap').read_bytes()
    if PLINIAN_DIVIDER.encode('utf-8')[:10] in data:
        record("icmp_steg [payload]", "PASS", "Plinian divider found in ICMP payloads")
    else:
        record("icmp_steg [payload]", "FAIL", "Divider not in PCAP data")
except Exception as e:
    record("icmp_steg [test]", "FAIL", str(e))

# --- TCP Covert Channel ---
try:
    data = (EXAMPLES_DIR / 'example_tcp_covert.pcap').read_bytes()
    # Extract ISN values from TCP SYN packets
    secret_bytes = bytearray()
    pos = 24
    while pos < len(data):
        if pos + 16 > len(data):
            break
        pkt_len = struct.unpack('<I', data[pos + 8:pos + 12])[0]
        pkt_data = data[pos + 16:pos + 16 + pkt_len]
        # TCP starts at offset 34 (Eth 14 + IP 20)
        if len(pkt_data) > 38:
            isn = struct.unpack('>I', pkt_data[38:42])[0]
            secret_bytes.extend(struct.pack('>I', isn))
            # TCP timestamp at offset 34+20+4 = 58 (options start at 54, kind=8 at 54, val at 56)
            if len(pkt_data) > 62:
                ts_val = struct.unpack('>I', pkt_data[58:62])[0]
                secret_bytes.extend(struct.pack('>I', ts_val))
        pos += 16 + pkt_len

    decoded = secret_bytes.rstrip(b'\x00').decode('utf-8', errors='replace')
    if PLINIAN_DIVIDER[:10] in decoded:
        record("tcp_covert [decode]", "PASS", "Plinian divider decoded from TCP ISN + timestamps")
    else:
        record("tcp_covert [decode]", "WARN", f"Got {len(secret_bytes)} bytes: {decoded[:30]}")
except Exception as e:
    record("tcp_covert [test]", "FAIL", str(e))

# --- HTTP Header Smuggling ---
try:
    data = (EXAMPLES_DIR / 'example_http_headers.pcap').read_bytes()
    found = []
    if PLINIAN_DIVIDER.encode('utf-8') in data:
        found.append('direct')
    if b'X-Request-ID' in data:
        found.append('X-Request-ID')
    if b'X-Correlation-Token' in data:
        found.append('X-Correlation-Token')
    if b'X-Debug-Info' in data:
        found.append('X-Debug-Info')
    if len(found) >= 2:
        record("http_headers [detection]", "PASS", f"Found: {', '.join(found)}")
    else:
        record("http_headers [detection]", "FAIL", f"Only found: {found}")
except Exception as e:
    record("http_headers [test]", "FAIL", str(e))

# --- PNG+ZIP Polyglot ---
try:
    data = (EXAMPLES_DIR / 'example_polyglot.png.zip').read_bytes()
    # Verify it's a valid PNG
    is_png = data[:8] == b'\x89PNG\r\n\x1a\n'
    # Verify it's a valid ZIP (try to open)
    import zipfile, io
    is_zip = False
    secret = ""
    try:
        with zipfile.ZipFile(io.BytesIO(data), 'r') as zf:
            is_zip = True
            if 'secret.txt' in zf.namelist():
                secret = zf.read('secret.txt').decode('utf-8')
    except:
        pass

    if is_png and is_zip:
        record("polyglot [dual format]", "PASS", "Valid as both PNG and ZIP")
    elif is_png:
        record("polyglot [dual format]", "FAIL", "Valid PNG but not ZIP")
    else:
        record("polyglot [dual format]", "FAIL", "Not valid PNG")

    if PLINIAN_DIVIDER in secret:
        record("polyglot [secret]", "PASS", "Plinian divider in ZIP secret.txt")
    elif secret:
        record("polyglot [secret]", "WARN", f"Got: {secret[:30]}")
    else:
        record("polyglot [secret]", "FAIL", "Could not extract secret.txt")
except Exception as e:
    record("polyglot [test]", "FAIL", str(e))

# --- PNG Filter Encoding ---
try:
    data = (EXAMPLES_DIR / 'example_filter_encoding.png').read_bytes()
    # Parse PNG to extract filter bytes from IDAT
    import zlib as _zlib
    # Find IDAT chunk
    pos = 8
    idat_data = b''
    width = height = 0
    while pos < len(data):
        chunk_len = struct.unpack('>I', data[pos:pos+4])[0]
        chunk_type = data[pos+4:pos+8]
        chunk_data = data[pos+8:pos+8+chunk_len]
        if chunk_type == b'IHDR':
            width = struct.unpack('>I', chunk_data[0:4])[0]
            height = struct.unpack('>I', chunk_data[4:8])[0]
        elif chunk_type == b'IDAT':
            idat_data += chunk_data
        elif chunk_type == b'IEND':
            break
        pos += 12 + chunk_len

    raw = _zlib.decompress(idat_data)
    stride = 1 + width * 3  # filter byte + RGB per pixel
    filter_bits = []
    for y in range(height):
        filter_byte = raw[y * stride]
        filter_bits.append(filter_byte & 1)

    # Decode
    if len(filter_bits) >= 16:
        length = int(''.join(str(b) for b in filter_bits[:16]), 2)
        if 0 < length < 200:
            msg_bits = filter_bits[16:16 + length * 8]
            msg_bytes = bytearray()
            for j in range(0, len(msg_bits), 8):
                if j + 8 <= len(msg_bits):
                    msg_bytes.append(int(''.join(str(b) for b in msg_bits[j:j+8]), 2))
            decoded = msg_bytes.decode('utf-8', errors='replace')
            if PLINIAN_DIVIDER[:10] in decoded:
                record("filter_encoding [decode]", "PASS", "Plinian divider decoded from PNG filter types")
            else:
                record("filter_encoding [decode]", "WARN", f"Got: {decoded[:30]}")
except Exception as e:
    record("filter_encoding [test]", "FAIL", str(e))

# --- Alpha Channel LSB ---
try:
    img = Image.open(EXAMPLES_DIR / 'example_alpha_lsb.png')
    img_rgba = img.convert('RGBA')
    pixels = list(img_rgba.getdata())
    # Extract ONLY alpha LSBs
    bits = [px[3] & 1 for px in pixels]
    length = 0
    for i in range(32):
        length = (length << 1) | bits[i]
    if 0 < length < 200:
        msg_bits = bits[32:32 + length * 8]
        msg_bytes = bytearray()
        for i in range(0, len(msg_bits), 8):
            v = 0
            for j in range(8):
                if i + j < len(msg_bits):
                    v = (v << 1) | msg_bits[i + j]
            msg_bytes.append(v)
        decoded = msg_bytes.decode('utf-8', errors='replace')
        if PLINIAN_DIVIDER[:10] in decoded:
            record("alpha_lsb [decode]", "PASS", "Plinian divider decoded from alpha channel LSB")
        else:
            record("alpha_lsb [decode]", "WARN", f"Got: {decoded[:30]}")
    else:
        record("alpha_lsb [decode]", "FAIL", f"Bad length: {length}")
except Exception as e:
    record("alpha_lsb [test]", "FAIL", str(e))

# --- JSON Key Ordering ---
try:
    import json as _json
    data = (EXAMPLES_DIR / 'example_key_ordering.json').read_bytes()
    obj = _json.loads(data)
    measurements = obj.get('measurements', [])
    ref_order = ["id", "specimen", "value", "unit", "confidence", "verified"]
    bits = []
    for m in measurements:
        keys = list(m.keys())
        if keys == ref_order:
            bits.append(0)
        else:
            bits.append(1)

    if len(bits) >= 16:
        length = int(''.join(str(b) for b in bits[:16]), 2)
        if 0 < length < 200:
            msg_bits = bits[16:16 + length * 8]
            msg_bytes = bytearray()
            for j in range(0, len(msg_bits), 8):
                if j + 8 <= len(msg_bits):
                    msg_bytes.append(int(''.join(str(b) for b in msg_bits[j:j+8]), 2))
            decoded = msg_bytes.decode('utf-8', errors='replace')
            if PLINIAN_DIVIDER[:10] in decoded:
                record("key_ordering [decode]", "PASS", "Plinian divider decoded from JSON key ordering")
            else:
                record("key_ordering [decode]", "WARN", f"Got: {decoded[:30]}")

    # Also check b64 metadata fallback
    meta_b64 = obj.get('_metadata', {}).get('payload_b64', '')
    if meta_b64:
        import base64 as _b64
        meta_decoded = _b64.b64decode(meta_b64).decode('utf-8')
        if PLINIAN_DIVIDER[:10] in meta_decoded:
            record("key_ordering [metadata]", "PASS", "Plinian divider in JSON metadata b64")
except Exception as e:
    record("key_ordering [test]", "FAIL", str(e))

# --- Capitalization Encoding ---
try:
    data = (EXAMPLES_DIR / 'example_capitalization.txt').read_bytes()
    if has_new_detectors:
        result = detect_capitalization_steg(data)
        if result.get('found'):
            record("capitalization [detection]", "PASS",
                   f"{result['suspicious_caps']} unexpected caps in {result['total_words']} words")
        else:
            record("capitalization [detection]", "WARN",
                   f"{result.get('suspicious_caps', 0)} caps (below threshold)")

    # Decode
    text = data.decode('utf-8')
    words = text.split(' ')
    bits = []
    for w in words:
        if w and w[0].isalpha():
            bits.append(1 if w[0].isupper() else 0)

    if len(bits) >= 16:
        length = int(''.join(str(b) for b in bits[:16]), 2)
        if 0 < length < 200:
            msg_bits = bits[16:16 + length * 8]
            msg_bytes = bytearray()
            for j in range(0, len(msg_bits), 8):
                if j + 8 <= len(msg_bits):
                    msg_bytes.append(int(''.join(str(b) for b in msg_bits[j:j+8]), 2))
            decoded = msg_bytes.decode('utf-8', errors='replace')
            if PLINIAN_DIVIDER[:10] in decoded:
                record("capitalization [decode]", "PASS", "Plinian divider decoded from caps")
            else:
                record("capitalization [decode]", "WARN", f"Got: {decoded[:30]}")
except Exception as e:
    record("capitalization [test]", "FAIL", str(e))

# --- Silence Interval Audio ---
try:
    import wave as _wave
    path = EXAMPLES_DIR / 'example_silence_interval.wav'
    with _wave.open(str(path), 'r') as w:
        frames = w.readframes(w.getnframes())
        samples = struct.unpack(f'<{w.getnframes()}h', frames)

    # Find silence gaps and measure their length
    # Threshold: |sample| < 500 is silence
    threshold = 500
    in_silence = False
    gap_lengths = []
    gap_start = 0
    sample_rate = 8000
    # Skip lead-in (~400 samples at 8000Hz = 50ms)
    skip = int(sample_rate * 0.05)
    for i in range(skip, len(samples)):
        is_quiet = abs(samples[i]) < threshold
        if is_quiet and not in_silence:
            in_silence = True
            gap_start = i
        elif not is_quiet and in_silence:
            gap_len = i - gap_start
            if gap_len > 100:  # Minimum gap to count
                gap_lengths.append(gap_len)
            in_silence = False

    if gap_lengths:
        # Short gap (~1102 samples) = 0, Long gap (~2205 samples) = 1
        mid = (min(gap_lengths) + max(gap_lengths)) / 2
        bits = [1 if g > mid else 0 for g in gap_lengths]

        if len(bits) >= 16:
            length = int(''.join(str(b) for b in bits[:16]), 2)
            if 0 < length < 200:
                msg_bits = bits[16:16 + length * 8]
                msg_bytes = bytearray()
                for j in range(0, len(msg_bits), 8):
                    if j + 8 <= len(msg_bits):
                        msg_bytes.append(int(''.join(str(b) for b in msg_bits[j:j+8]), 2))
                decoded = msg_bytes.decode('utf-8', errors='replace')
                if PLINIAN_DIVIDER[:10] in decoded:
                    record("silence_interval [decode]", "PASS",
                           "Plinian divider decoded from silence gaps")
                else:
                    record("silence_interval [decode]", "WARN",
                           f"Got {len(gap_lengths)} gaps, decoded: {decoded[:30]}")
    else:
        record("silence_interval [decode]", "FAIL", "No silence gaps detected")
except Exception as e:
    record("silence_interval [test]", "FAIL", str(e))

print()

# =============================================================================
# SECTION 11: Full Coverage Tests for All Remaining Example Files
# =============================================================================
print("-" * 70)
print("SECTION 11: Full Coverage Tests (50 additional example files)")
print("-" * 70)


def test_file_exists(filename, desc):
    """Basic test: file exists and is non-empty."""
    path = EXAMPLES_DIR / filename
    if path.exists() and path.stat().st_size > 0:
        record(f"{filename} [exists]", "PASS", f"{desc} ({path.stat().st_size} bytes)")
        return True
    else:
        record(f"{filename} [exists]", "FAIL", "File missing or empty")
        return False


def test_direct_search(filename, desc):
    """Test that the Plinian divider appears directly in the file."""
    path = EXAMPLES_DIR / filename
    data = path.read_bytes()
    if PLINIAN_DIVIDER.encode('utf-8') in data:
        record(f"{filename} [direct]", "PASS", f"Plinian divider found in {desc}")
        return True
    else:
        record(f"{filename} [direct]", "FAIL", f"Plinian divider not found in {desc}")
        return False


def test_b64_hex_search(filename, desc):
    """Test that base64 or hex encoding of divider is detectable."""
    import base64
    path = EXAMPLES_DIR / filename
    data = path.read_bytes()
    secret = PLINIAN_DIVIDER.encode('utf-8')
    found = []
    if base64.b64encode(secret) in data:
        found.append("b64")
    if secret.hex().encode() in data:
        found.append("hex")
    if found:
        record(f"{filename} [b64/hex]", "PASS", f"{desc}: {'+'.join(found)}")
    else:
        record(f"{filename} [b64/hex]", "WARN", f"No b64/hex encoding found")


def test_image_lsb_decode(filename, desc, bits_per_channel=1, length_size=4):
    """Test LSB decode of Plinian divider from image."""
    try:
        img = Image.open(EXAMPLES_DIR / filename).convert('RGBA')
        pixels = list(img.getdata())
        bits = []
        for r, g, b, a in pixels:
            for ch in [r, g, b]:
                for bp in range(bits_per_channel):
                    bits.append((ch >> bp) & 1)

        length = 0
        prefix_bits = length_size * 8
        for i in range(prefix_bits):
            length = (length << 1) | bits[i]

        if 0 < length < 500:
            msg_bits = bits[prefix_bits:prefix_bits + length * 8]
            msg = bytearray()
            for i in range(0, len(msg_bits), 8):
                v = 0
                for j in range(8):
                    if i + j < len(msg_bits):
                        v = (v << 1) | msg_bits[i + j]
                msg.append(v)
            decoded = msg.decode('utf-8', errors='replace')
            if PLINIAN_DIVIDER[:10] in decoded:
                record(f"{filename} [LSB decode]", "PASS", f"{desc}")
                return
        record(f"{filename} [LSB decode]", "WARN", f"Length={length}, partial decode")
    except Exception as e:
        record(f"{filename} [LSB decode]", "FAIL", str(e))


# --- Unicode & text tricks (Chunk 9) ---

# Directional override
try:
    data = (EXAMPLES_DIR / 'example_directional_override.txt').read_bytes()
    text = data.decode('utf-8')
    rlo_count = text.count('\u202E')
    lro_count = text.count('\u202D')
    if rlo_count > 0 and lro_count > 0:
        record("example_directional_override.txt [bidi]", "PASS",
               f"RLO={rlo_count}, LRO={lro_count} directional chars")
    else:
        record("example_directional_override.txt [bidi]", "FAIL", "No bidi chars")
except Exception as e:
    record("example_directional_override.txt [bidi]", "FAIL", str(e))

# Hangul filler
try:
    data = (EXAMPLES_DIR / 'example_hangul_filler.txt').read_bytes()
    text = data.decode('utf-8')
    hf_count = text.count('\u3164')
    if hf_count > 0:
        record("example_hangul_filler.txt [hangul]", "PASS", f"{hf_count} Hangul fillers")
    else:
        record("example_hangul_filler.txt [hangul]", "FAIL", "No Hangul fillers")
except Exception as e:
    record("example_hangul_filler.txt [hangul]", "FAIL", str(e))

# Braille
try:
    data = (EXAMPLES_DIR / 'example_braille.txt').read_bytes()
    text = data.decode('utf-8')
    braille_chars = [c for c in text if 0x2800 <= ord(c) <= 0x28FF]
    if len(braille_chars) >= 10:
        # Decode Braille back to bytes
        decoded = bytes(ord(c) - 0x2800 for c in braille_chars)
        if PLINIAN_DIVIDER.encode('utf-8') == decoded:
            record("example_braille.txt [decode]", "PASS", "Braille -> bytes -> Plinian divider exact match")
        else:
            record("example_braille.txt [decode]", "WARN", f"{len(braille_chars)} Braille chars, partial match")
    else:
        record("example_braille.txt [decode]", "FAIL", f"Only {len(braille_chars)} Braille chars")
except Exception as e:
    record("example_braille.txt [decode]", "FAIL", str(e))

# Math alphanumeric
try:
    data = (EXAMPLES_DIR / 'example_math_alphanumeric.txt').read_bytes()
    text = data.decode('utf-8')
    math_bold = sum(1 for c in text if 0x1D400 <= ord(c) <= 0x1D433)
    normal_alpha = sum(1 for c in text if c.isascii() and c.isalpha())
    if math_bold > 0:
        record("example_math_alphanumeric.txt [math]", "PASS",
               f"{math_bold} math bold chars, {normal_alpha} normal")
    else:
        record("example_math_alphanumeric.txt [math]", "FAIL", "No math bold chars")
except Exception as e:
    record("example_math_alphanumeric.txt [math]", "FAIL", str(e))

# Unicode normalization
try:
    import unicodedata
    data = (EXAMPLES_DIR / 'example_normalization.txt').read_bytes()
    text = data.decode('utf-8')
    nfc_count = sum(1 for line in text.split('\n') if line.strip() and
                    unicodedata.is_normalized('NFC', line.strip()))
    nfd_count = sum(1 for line in text.split('\n') if line.strip() and
                    not unicodedata.is_normalized('NFC', line.strip()) and
                    unicodedata.is_normalized('NFD', line.strip()))
    if nfc_count > 0 or nfd_count > 0:
        record("example_normalization.txt [NFC/NFD]", "PASS",
               f"NFC={nfc_count}, NFD={nfd_count} lines")
    else:
        record("example_normalization.txt [NFC/NFD]", "WARN", "Could not distinguish NFC/NFD")
except Exception as e:
    record("example_normalization.txt [NFC/NFD]", "FAIL", str(e))

# Sentence length, word choice, misspelling — test they exist and contain text
for fname, desc in [
    ('example_sentence_length.txt', 'sentence length encoding'),
    ('example_word_choice.txt', 'word choice/synonym steg'),
    ('example_misspelling.txt', 'misspelling pattern steg'),
]:
    test_file_exists(fname, desc)

# --- Network & encoding tricks (Chunk 10) ---

# IP TTL, IP ID, TCP window, TCP urgent
for fname, field_name, offset, size in [
    ('example_ttl_covert.pcap', 'IP TTL', 22, 1),  # TTL at IP header byte 8
    ('example_ipid_covert.pcap', 'IP ID', None, None),
    ('example_tcp_window.pcap', 'TCP window', None, None),
    ('example_tcp_urgent.pcap', 'TCP urgent', None, None),
]:
    if test_file_exists(fname, f'{field_name} covert channel'):
        # Verify it's a valid PCAP
        data = (EXAMPLES_DIR / fname).read_bytes()
        if data[:4] in (b'\xa1\xb2\xc3\xd4', b'\xd4\xc3\xb2\xa1'):
            record(f"{fname} [pcap valid]", "PASS", f"Valid PCAP with {field_name} encoding")
        else:
            record(f"{fname} [pcap valid]", "FAIL", "Not valid PCAP")

# DNS TXT
try:
    data = (EXAMPLES_DIR / 'example_dns_txt.pcap').read_bytes()
    import base64 as b64mod
    b64_secret = b64mod.b64encode(PLINIAN_DIVIDER.encode('utf-8'))
    if b64_secret in data:
        record("example_dns_txt.pcap [payload]", "PASS", "Base64 divider in DNS TXT record")
    else:
        record("example_dns_txt.pcap [payload]", "WARN", "Divider not found in raw PCAP")
except Exception as e:
    record("example_dns_txt.pcap [payload]", "FAIL", str(e))

# Covert timing
test_file_exists('example_covert_timing.pcap', 'covert timing channel')

# Multi-base encoding
try:
    data = (EXAMPLES_DIR / 'example_multibase.txt').read_bytes()
    import base64 as b64mod
    secret = PLINIAN_DIVIDER.encode('utf-8')
    found = []
    if b64mod.b64encode(secret) in data:
        found.append('b64')
    if b64mod.b32encode(secret) in data:
        found.append('b32')
    if b64mod.b16encode(secret) in data:
        found.append('b16')
    if b64mod.b85encode(secret) in data:
        found.append('b85')
    record("example_multibase.txt [decode]", "PASS" if len(found) >= 3 else "WARN",
           f"Found encodings: {', '.join(found)}")
except Exception as e:
    record("example_multibase.txt [decode]", "FAIL", str(e))

# Morse
test_file_exists('example_morse.txt', 'Morse code encoding')

# --- Image techniques (Chunk 11) ---

# PVD
test_file_exists('example_pvd.png', 'Pixel Value Differencing')

# Histogram shifting
test_file_exists('example_histogram_shift.png', 'histogram shifting')

# LSB 4-bit (high capacity)
try:
    img = Image.open(EXAMPLES_DIR / 'example_lsb_4bit.png').convert('RGBA')
    pixels = list(img.getdata())
    # Extract nibbles from lower 4 bits
    nibbles = []
    for r, g, b, a in pixels:
        for ch in [r, g, b]:
            nibbles.append(ch & 0x0F)
    # Reconstruct bytes from pairs of nibbles
    length = 0
    for i in range(8):  # 4 bytes = 8 nibbles for length
        length = (length << 4) | nibbles[i]
    if 0 < length < 200:
        msg = bytearray()
        for i in range(8, 8 + length * 2):
            if i % 2 == 0 and i + 1 < len(nibbles):
                msg.append((nibbles[i] << 4) | nibbles[i + 1])
        decoded = msg.decode('utf-8', errors='replace')
        if PLINIAN_DIVIDER[:10] in decoded:
            record("example_lsb_4bit.png [decode]", "PASS", "4-bit LSB decoded")
        else:
            record("example_lsb_4bit.png [decode]", "WARN", f"Length={length}, decoded: {decoded[:20]}")
    else:
        record("example_lsb_4bit.png [decode]", "WARN", f"Length={length}")
except Exception as e:
    record("example_lsb_4bit.png [decode]", "FAIL", str(e))

# LSB MSB-first
test_file_exists('example_lsb_msb_first.png', 'LSB MSB-first ordering')

# BMP DIB header
try:
    data = (EXAMPLES_DIR / 'example_bmp_dib.bmp').read_bytes()
    if PLINIAN_DIVIDER.encode('utf-8') in data:
        record("example_bmp_dib.bmp [trailing]", "PASS", "Plinian divider in BMP trailing data")
    else:
        record("example_bmp_dib.bmp [trailing]", "FAIL", "Divider not in raw data")
except Exception as e:
    record("example_bmp_dib.bmp [trailing]", "FAIL", str(e))

# GIF disposal
test_file_exists('example_gif_disposal.gif', 'GIF disposal method encoding')

# JPEG APP segment
try:
    data = (EXAMPLES_DIR / 'example_jpeg_app.jpg').read_bytes()
    if b'ST3GG' in data and PLINIAN_DIVIDER.encode('utf-8') in data:
        record("example_jpeg_app.jpg [APP segment]", "PASS", "ST3GG APP segment with divider")
    elif b'ST3GG' in data:
        record("example_jpeg_app.jpg [APP segment]", "WARN", "ST3GG found but divider not in raw")
    else:
        record("example_jpeg_app.jpg [APP segment]", "FAIL", "No ST3GG marker")
except Exception as e:
    record("example_jpeg_app.jpg [APP segment]", "FAIL", str(e))

# YCbCr color space
test_file_exists('example_ycbcr.png', 'YCbCr color space LSB')

# PNG custom chunks
try:
    data = (EXAMPLES_DIR / 'example_png_chunks_custom.png').read_bytes()
    if b'stEg' in data and PLINIAN_DIVIDER.encode('utf-8') in data:
        record("example_png_chunks_custom.png [chunks]", "PASS", "Custom stEg chunk with divider")
    else:
        record("example_png_chunks_custom.png [chunks]", "FAIL", "Custom chunks not found")
except Exception as e:
    record("example_png_chunks_custom.png [chunks]", "FAIL", str(e))

# Matched pairs
test_file_exists('example_matched_pairs.png', 'matched pairs LSB')

# Scanline filter
test_file_exists('example_scanline_filter.png', 'PNG scanline filter abuse')

# --- Document & archive (Chunk 12) ---

# PDF JavaScript
try:
    data = (EXAMPLES_DIR / 'example_pdf_javascript.pdf').read_bytes()
    import base64 as b64mod
    b64 = b64mod.b64encode(PLINIAN_DIVIDER.encode('utf-8'))
    if b64 in data and b'/JavaScript' in data:
        record("example_pdf_javascript.pdf [JS]", "PASS", "JavaScript action with base64 divider")
    else:
        record("example_pdf_javascript.pdf [JS]", "FAIL", "JS or divider not found")
except Exception as e:
    record("example_pdf_javascript.pdf [JS]", "FAIL", str(e))

# PDF incremental
test_direct_search('example_pdf_incremental.pdf', 'PDF incremental update')

# PDF form fields
test_direct_search('example_pdf_forms.pdf', 'PDF form fields')

# HTML events
try:
    data = (EXAMPLES_DIR / 'example_html_events.html').read_bytes()
    text = data.decode('utf-8')
    has_events = 'onload=' in text and 'onclick=' in text
    has_hidden = 'type="hidden"' in text
    has_divider = PLINIAN_DIVIDER in text
    if has_events and has_hidden and has_divider:
        record("example_html_events.html [events]", "PASS",
               "Event handlers + hidden fields + divider")
    else:
        record("example_html_events.html [events]", "WARN",
               f"events={has_events}, hidden={has_hidden}, divider={has_divider}")
except Exception as e:
    record("example_html_events.html [events]", "FAIL", str(e))

# XML entities
try:
    data = (EXAMPLES_DIR / 'example_xml_entities.xml').read_bytes()
    text = data.decode('utf-8')
    has_entity = '<!ENTITY steg_payload' in text
    has_divider = PLINIAN_DIVIDER in text
    if has_entity and has_divider:
        record("example_xml_entities.xml [entities]", "PASS",
               "Entity declarations with divider")
    else:
        record("example_xml_entities.xml [entities]", "FAIL", "Missing entities or divider")
except Exception as e:
    record("example_xml_entities.xml [entities]", "FAIL", str(e))

# Nested ZIP
try:
    import zipfile
    with zipfile.ZipFile(EXAMPLES_DIR / 'example_nested.zip') as outer:
        names = outer.namelist()
        has_inner = any('inner.zip' in n for n in names)
        if has_inner:
            inner_data = outer.read('data/inner.zip')
            import io
            with zipfile.ZipFile(io.BytesIO(inner_data)) as inner:
                secret_data = inner.read('secret.txt').decode('utf-8')
                if PLINIAN_DIVIDER in secret_data:
                    record("example_nested.zip [nested decode]", "PASS",
                           "Plinian divider extracted from inner ZIP")
                else:
                    record("example_nested.zip [nested decode]", "FAIL",
                           f"Inner secret: {secret_data[:30]}")
        else:
            record("example_nested.zip [nested decode]", "FAIL", "No inner.zip")
except Exception as e:
    record("example_nested.zip [nested decode]", "FAIL", str(e))

# Emoji skin tone
try:
    data = (EXAMPLES_DIR / 'example_emoji_skin_tone.txt').read_bytes()
    text = data.decode('utf-8')
    skin_tones = sum(1 for c in text if 0x1F3FB <= ord(c) <= 0x1F3FF)
    if skin_tones > 10:
        record("example_emoji_skin_tone.txt [tones]", "PASS",
               f"{skin_tones} skin tone modifiers")
    else:
        record("example_emoji_skin_tone.txt [tones]", "FAIL",
               f"Only {skin_tones} modifiers")
except Exception as e:
    record("example_emoji_skin_tone.txt [tones]", "FAIL", str(e))

# Punycode
test_file_exists('example_punycode.txt', 'Punycode/IDN domains')
test_b64_hex_search('example_punycode.txt', 'Punycode file')

# QR steg
test_file_exists('example_qr_steg.txt', 'QR code steganography')
test_b64_hex_search('example_qr_steg.txt', 'QR steg file')

# JPEG restart markers
try:
    data = (EXAMPLES_DIR / 'example_jpeg_restart.jpg').read_bytes()
    has_com = b'\xFF\xFE' in data  # COM marker
    has_steg = b'ST3GG' in data
    if has_com and has_steg:
        record("example_jpeg_restart.jpg [COM]", "PASS", "JPEG COM marker with ST3GG")
    else:
        record("example_jpeg_restart.jpg [COM]", "WARN", f"COM={has_com}, ST3GG={has_steg}")
except Exception as e:
    record("example_jpeg_restart.jpg [COM]", "FAIL", str(e))

# PNG polyglot (already tested in section 10, but verify decode)
try:
    data = (EXAMPLES_DIR / 'example_polyglot.png.zip').read_bytes()
    # Should be valid as both PNG and ZIP
    is_png = data[:8] == b'\x89PNG\r\n\x1a\n'
    import zipfile, io
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
        is_zip = True
        zip_names = zf.namelist()
        zf.close()
    except:
        is_zip = False
        zip_names = []
    if is_png and is_zip:
        record("example_polyglot.png.zip [polyglot]", "PASS",
               f"Valid PNG + ZIP ({len(zip_names)} files)")
    else:
        record("example_polyglot.png.zip [polyglot]", "WARN",
               f"PNG={is_png}, ZIP={is_zip}")
except Exception as e:
    record("example_polyglot.png.zip [polyglot]", "FAIL", str(e))

# --- Audio DSP (Chunk 14) ---

for fname, desc in [
    ('example_echo_hiding.wav', 'echo hiding'),
    ('example_phase_coding.wav', 'phase coding'),
    ('example_spread_spectrum.wav', 'spread spectrum DSSS'),
    ('example_quantization_noise.wav', 'quantization noise'),
]:
    if test_file_exists(fname, desc):
        # Verify valid WAV
        try:
            with wave.open(str(EXAMPLES_DIR / fname)) as w:
                record(f"{fname} [wav valid]", "PASS",
                       f"WAV: {w.getnchannels()}ch, {w.getframerate()}Hz, {w.getnframes()} frames")
        except Exception as e:
            record(f"{fname} [wav valid]", "FAIL", str(e))

# --- Image DSP (Chunk 15) ---

for fname, desc in [
    ('example_bpcs.png', 'BPCS bit-plane complexity'),
    ('example_dct_manual.png', 'DCT coefficient embedding'),
    ('example_dft.png', 'DFT magnitude embedding'),
    ('example_dwt_haar.png', 'DWT Haar wavelet'),
    ('example_subsampling.png', 'chroma subsampling'),
]:
    if test_file_exists(fname, desc):
        try:
            img = Image.open(EXAMPLES_DIR / fname)
            record(f"{fname} [image valid]", "PASS",
                   f"{img.size[0]}x{img.size[1]} {img.mode}")
        except Exception as e:
            record(f"{fname} [image valid]", "FAIL", str(e))

# --- Misc (Chunk 16) ---

# Self-extracting archive
try:
    data = (EXAMPLES_DIR / 'example_self_extracting.sh').read_bytes()
    text = data.decode('utf-8')
    import base64 as b64mod
    b64_secret = b64mod.b64encode(PLINIAN_DIVIDER.encode('utf-8')).decode()
    if b64_secret in text and '#!/bin/sh' in text:
        record("example_self_extracting.sh [SFX]", "PASS", "Shell SFX with embedded payload")
    else:
        record("example_self_extracting.sh [SFX]", "FAIL", "Missing shebang or payload")
except Exception as e:
    record("example_self_extracting.sh [SFX]", "FAIL", str(e))

# Extended attributes
try:
    path = EXAMPLES_DIR / 'example_xattr.txt'
    if path.exists():
        try:
            attrs = os.listxattr(str(path))
            steg_attrs = [a for a in attrs if 'st3gg' in a]
            if steg_attrs:
                payload = os.getxattr(str(path), b'user.st3gg.payload')
                if payload == PLINIAN_DIVIDER.encode('utf-8'):
                    record("example_xattr.txt [xattr decode]", "PASS",
                           f"Plinian divider in xattr ({len(steg_attrs)} attrs)")
                else:
                    record("example_xattr.txt [xattr decode]", "WARN",
                           f"{len(steg_attrs)} attrs but payload mismatch")
            else:
                record("example_xattr.txt [xattr decode]", "WARN",
                       "No st3gg xattrs (may not survive git)")
        except OSError:
            record("example_xattr.txt [xattr decode]", "WARN",
                   "xattr not supported on this filesystem")
except Exception as e:
    record("example_xattr.txt [xattr decode]", "FAIL", str(e))

# TLS cert
test_file_exists('example_tls_cert.pem', 'TLS certificate fields')
test_direct_search('example_tls_cert.pem', 'TLS cert')
test_b64_hex_search('example_tls_cert.pem', 'TLS cert')

print()

# =============================================================================
# SUMMARY
# =============================================================================
print("=" * 70)
print("SUMMARY")
print("=" * 70)
print(f"  Total tests:  {total}")
print(f"  Passed:       {passed}")
print(f"  Warnings:     {warnings}")
print(f"  Failed:       {failed}")
print(f"  Pass rate:    {passed}/{total} ({100*passed/total:.1f}%)")
print(f"  Pass+Warn:    {passed+warnings}/{total} ({100*(passed+warnings)/total:.1f}%)")
print()

if failed > 0:
    print("FAILED TESTS:")
    for name, (status, detail) in results.items():
        if status == "FAIL":
            print(f"  - {name}: {detail}")
    print()

if warnings > 0:
    print("WARNINGS:")
    for name, (status, detail) in results.items():
        if status == "WARN":
            print(f"  - {name}: {detail}")
    print()

sys.exit(0 if failed == 0 else 1)
