#!/usr/bin/env python3
"""
STEGOSAURUS WRECKS - NiceGUI Web Interface
Ultimate steganography suite with hacker aesthetic

Run with: python webui.py
"""

from nicegui import ui, app
from fastapi import Request
from fastapi.responses import JSONResponse
from PIL import Image
import io
import base64
import tempfile
import os
from pathlib import Path
from typing import Optional
import asyncio
import json

# Import our steg modules
import steg_core
from steg_core import (
    encode, decode, create_config, calculate_capacity,
    analyze_image, detect_encoding, CHANNEL_PRESETS,
    Channel, StegConfig, EncodingStrategy, _extract_bit_units,
    _bits_array_to_bytes, _generate_pixel_indices
)
import crypto
import numpy as np
import re
import string

# ============== THEME / STYLING ==============

DARK_CSS = """
:root {
    --primary: #00ff41;
    --primary-dim: #00aa2a;
    --primary-glow: rgba(0, 255, 65, 0.4);
    --secondary: #00d4ff;
    --accent: #ff00ff;
    --warning: #ffd000;
    --error: #ff3333;
    --bg-dark: #0a0a0a;
    --bg-card: #0d1117;
    --bg-hover: #161b22;
    --text: #00ff41;
    --text-dim: #555;
    --border: #30363d;
}

body {
    background: var(--bg-dark) !important;
    font-family: 'JetBrains Mono', 'Fira Code', 'Courier New', monospace !important;
}

.q-card {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
}

.nicegui-content {
    background: var(--bg-dark) !important;
}

/* Matrix scanline effect - subtler */
.matrix-bg {
    background: repeating-linear-gradient(
        0deg,
        transparent,
        transparent 2px,
        rgba(0, 255, 65, 0.015) 2px,
        rgba(0, 255, 65, 0.015) 4px
    );
    pointer-events: none;
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    z-index: 9999;
}

/* Glow effect for headers */
.glow {
    text-shadow: 0 0 10px var(--primary), 0 0 20px var(--primary-glow);
}

/* Cyber border animation */
@keyframes border-pulse {
    0%, 100% { border-color: var(--primary); box-shadow: 0 0 5px var(--primary-glow); }
    50% { border-color: var(--secondary); box-shadow: 0 0 15px rgba(0, 212, 255, 0.3); }
}

@keyframes glow-pulse {
    0%, 100% { opacity: 0.6; }
    50% { opacity: 1; }
}

.cyber-border {
    border: 1px solid var(--primary) !important;
    animation: border-pulse 3s infinite;
}

/* Status indicators */
.status-success { color: var(--primary) !important; }
.status-error { color: var(--error) !important; }
.status-warning { color: var(--warning) !important; }
.status-info { color: var(--secondary) !important; }

/* Custom scrollbar */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: var(--bg-dark); }
::-webkit-scrollbar-thumb { background: var(--primary-dim); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--primary); }

/* File upload area - MODERNIZED */
.drop-zone {
    border: 1px solid var(--border) !important;
    background: linear-gradient(135deg, rgba(0, 255, 65, 0.03) 0%, rgba(0, 212, 255, 0.03) 100%) !important;
    transition: all 0.3s ease;
    padding: 16px;
    text-align: center;
    cursor: pointer;
    border-radius: 8px;
    position: relative;
    overflow: hidden;
}

.drop-zone::before {
    content: '';
    position: absolute;
    top: 0;
    left: -100%;
    width: 100%;
    height: 100%;
    background: linear-gradient(90deg, transparent, rgba(0, 255, 65, 0.1), transparent);
    transition: left 0.5s ease;
}

.drop-zone:hover {
    border-color: var(--primary) !important;
    background: linear-gradient(135deg, rgba(0, 255, 65, 0.08) 0%, rgba(0, 212, 255, 0.05) 100%) !important;
    box-shadow: 0 0 20px rgba(0, 255, 65, 0.15), inset 0 0 30px rgba(0, 255, 65, 0.05);
}

.drop-zone:hover::before {
    left: 100%;
}

/* Terminal style output */
.terminal {
    background: #000 !important;
    border: 1px solid var(--border) !important;
    font-family: 'JetBrains Mono', monospace !important;
    color: var(--primary) !important;
    padding: 16px !important;
    white-space: pre-wrap;
    overflow-x: auto;
    border-radius: 6px;
}

/* Button overrides for cooler look */
.q-btn {
    text-transform: uppercase !important;
    letter-spacing: 1px !important;
    font-weight: 600 !important;
}

/* Input fields */
.q-field--dark .q-field__control {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 6px !important;
}

.q-field--dark .q-field__control:hover {
    border-color: var(--primary-dim) !important;
}

.q-field--focused .q-field__control {
    border-color: var(--primary) !important;
    box-shadow: 0 0 10px var(--primary-glow) !important;
}

/* Select dropdowns */
.q-menu {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
}

/* Tabs styling */
.q-tab--active {
    color: var(--primary) !important;
    text-shadow: 0 0 10px var(--primary-glow);
}

.q-tab:hover {
    color: var(--secondary) !important;
}

/* Switches */
.q-toggle__track {
    background: var(--border) !important;
}

.q-toggle--active .q-toggle__track {
    background: var(--primary-dim) !important;
}

/* Image preview container */
.image-preview {
    border: 1px solid var(--border);
    border-radius: 8px;
    overflow: hidden;
    background: #000;
}

/* Stats/info boxes */
.info-box {
    background: linear-gradient(135deg, var(--bg-card) 0%, var(--bg-hover) 100%);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 12px;
}

.info-box:hover {
    border-color: var(--primary-dim);
}

/* Section headers */
.section-header {
    font-size: 14px;
    font-weight: 700;
    letter-spacing: 2px;
    text-transform: uppercase;
    margin-bottom: 12px;
    display: flex;
    align-items: center;
    gap: 8px;
}

.section-header::after {
    content: '';
    flex: 1;
    height: 1px;
    background: linear-gradient(90deg, var(--border), transparent);
}

/* Capacity meter */
.capacity-meter {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 12px;
    margin: 8px 0;
}

.capacity-bar-outer {
    background: var(--bg-dark);
    border-radius: 4px;
    height: 6px;
    overflow: hidden;
    margin: 8px 0;
}

.capacity-bar-inner {
    height: 100%;
    border-radius: 4px;
    transition: width 0.3s ease, background 0.3s ease;
}

/* Notification styling */
.q-notification {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
}

/* 🪆 MATRYOSHKA MODE - Easter egg activation zone (stealth) */
.matryoshka-trigger {
    position: fixed;
    bottom: 0;
    left: 0;
    width: 12px;
    height: 12px;
    z-index: 99999;
    opacity: 0;
    background: transparent;
    pointer-events: auto !important;
}

.matryoshka-trigger:hover {
    opacity: 0;
}

/* Matryoshka mode indicator */
.matryoshka-active {
    animation: matryoshka-glow 2s ease-in-out infinite;
}

@keyframes matryoshka-glow {
    0%, 100% { box-shadow: 0 0 5px #ff00ff, 0 0 10px #ff00ff; }
    50% { box-shadow: 0 0 20px #ff00ff, 0 0 40px #ff00ff, 0 0 60px #ff00ff; }
}

/* Nested results tree styling */
.matryoshka-tree {
    font-family: monospace;
    padding: 12px;
    background: #000;
    border: 1px solid var(--accent);
    border-radius: 6px;
}

.matryoshka-layer {
    padding-left: 20px;
    border-left: 2px solid var(--accent);
    margin-left: 10px;
}

.matryoshka-layer-0 { border-color: #ff00ff; }
.matryoshka-layer-1 { border-color: #ff66ff; }
.matryoshka-layer-2 { border-color: #ff99ff; }
.matryoshka-layer-3 { border-color: #ffccff; }
"""

BANNER_ASCII = """
███████╗████████╗███████╗ ██████╗  ██████╗ ███████╗ █████╗ ██╗   ██╗██████╗ ██╗   ██╗███████╗
██╔════╝╚══██╔══╝██╔════╝██╔════╝ ██╔═══██╗██╔════╝██╔══██╗██║   ██║██╔══██╗██║   ██║██╔════╝
███████╗   ██║   █████╗  ██║  ███╗██║   ██║███████╗███████║██║   ██║██████╔╝██║   ██║███████╗
╚════██║   ██║   ██╔══╝  ██║   ██║██║   ██║╚════██║██╔══██║██║   ██║██╔══██╗██║   ██║╚════██║
███████║   ██║   ███████╗╚██████╔╝╚██████╔╝███████║██║  ██║╚██████╔╝██║  ██║╚██████╔╝███████║
╚══════╝   ╚═╝   ╚══════╝ ╚═════╝  ╚═════╝ ╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚══════╝
                         W R E C K S   v3.0
"""

STEGO_ASCII = """
       __
      /  '-.
     / .-. |  STEGOSAURUS
    /.'   \\|    WRECKS
   //   |\\  \\
  ||   | \\  |  >> LSB Suite <<
 /||   |  \\ |
/ ||__/   \\/
\\  --'   |\\_\\
 '._____.' \\/
"""


# ============== STATE MANAGEMENT ==============

class AppState:
    """Global application state"""
    def __init__(self):
        # Encode state
        self.carrier_image: Optional[Image.Image] = None
        self.carrier_path: Optional[str] = None
        self.encoded_image: Optional[Image.Image] = None
        self.encode_file_data: Optional[bytes] = None
        self.encode_file_name: Optional[str] = None
        self.encode_result: Optional[Image.Image] = None
        # Decode state
        self.decode_image: Optional[Image.Image] = None
        self.detected_config: Optional[dict] = None
        self.extracted_file: Optional[bytes] = None
        self.extracted_filename: Optional[str] = None
        # Analyze state
        self.analyze_image: Optional[Image.Image] = None
        # General
        self.advanced_mode: bool = False
        self.capacity_info: dict = {}
        # UI state - track active tab across reloads
        self.active_tab: str = 'encode'
        # 🪆 MATRYOSHKA MODE - Russian nesting doll steganography
        self.matryoshka_mode: bool = False
        self.matryoshka_depth: int = 3  # Default depth (1-11)
        # Store nested decode results
        self.matryoshka_results: list = []
        # Matryoshka encoding - carrier images (outermost first)
        self.matryoshka_carriers: list = []  # List of (Image, filename) tuples
        self.matryoshka_encode_result: Optional[Image.Image] = None

state = AppState()


def generate_blank_image(width: int = 1024, height: int = 1024, color: str = 'noise') -> Image.Image:
    """Generate a blank or noise image for steganography"""
    import numpy as np

    if color == 'noise':
        # Random noise - best for hiding data
        pixels = np.random.randint(0, 256, (height, width, 4), dtype=np.uint8)
        pixels[:, :, 3] = 255  # Full alpha
        return Image.fromarray(pixels, 'RGBA')
    elif color == 'black':
        return Image.new('RGBA', (width, height), (0, 0, 0, 255))
    elif color == 'white':
        return Image.new('RGBA', (width, height), (255, 255, 255, 255))
    else:
        # Gradient - looks nicer
        pixels = np.zeros((height, width, 4), dtype=np.uint8)
        for y in range(height):
            for x in range(width):
                pixels[y, x] = [
                    int(255 * x / width),
                    int(255 * y / height),
                    128,
                    255
                ]
        return Image.fromarray(pixels, 'RGBA')


# ============== HELPER FUNCTIONS ==============

def image_to_base64(img: Image.Image, format: str = "PNG") -> str:
    """Convert PIL Image to base64 string for display"""
    buffer = io.BytesIO()
    img.save(buffer, format=format)
    return base64.b64encode(buffer.getvalue()).decode()


def base64_to_image(b64: str) -> Image.Image:
    """Convert base64 string to PIL Image"""
    # Handle data URL format
    if ',' in b64:
        b64 = b64.split(',')[1]
    data = base64.b64decode(b64)
    return Image.open(io.BytesIO(data))


def format_size(size_bytes: int) -> str:
    """Format bytes to human readable"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


# ============== SMART DECODE / APERI'SOLVE STYLE ==============

def detect_coherent_text(data: bytes, min_printable_ratio: float = 0.85) -> dict:
    """
    Detect if data looks like coherent readable text.
    Returns analysis dict with confidence and detected text preview.
    Properly handles Unicode text, not just ASCII.
    """
    if not data or len(data) == 0:
        return {"is_text": False, "confidence": 0, "preview": "", "reason": "empty"}

    # Try UTF-8 decode
    try:
        text = data.decode('utf-8', errors='strict')
    except:
        try:
            text = data.decode('latin-1', errors='replace')
        except:
            return {"is_text": False, "confidence": 0, "preview": "", "reason": "decode_failed"}

    if len(text) == 0:
        return {"is_text": False, "confidence": 0, "preview": "", "reason": "empty_text"}

    # Calculate printable character ratio - Unicode aware
    # Count chars that are NOT control characters as printable
    # Control chars: 0x00-0x1F (except \t, \n, \r), 0x7F, 0x80-0x9F
    def is_printable_unicode(c):
        code = ord(c)
        # Whitespace is fine
        if c in '\t\n\r ':
            return True
        # ASCII control chars
        if code <= 0x1F or code == 0x7F:
            return False
        # C1 control chars
        if 0x80 <= code <= 0x9F:
            return False
        # Everything else (printable ASCII, Latin-1 supplement, Unicode) is OK
        return True

    printable_count = sum(1 for c in text[:500] if is_printable_unicode(c))
    printable_ratio = printable_count / min(len(text), 500)

    # Check for null bytes in first 100 chars (binary indicator)
    null_count = text[:100].count('\x00')
    has_nulls = null_count > 2

    # Check for common words (English)
    common_words = ['the', 'and', 'is', 'in', 'to', 'of', 'a', 'for', 'on', 'that',
                    'this', 'with', 'are', 'be', 'as', 'at', 'by', 'or', 'an', 'it',
                    'from', 'was', 'have', 'has', 'not', 'but', 'what', 'all', 'were',
                    'flag', 'ctf', 'secret', 'hidden', 'password', 'key', 'message']
    text_lower = text.lower()
    word_matches = sum(1 for w in common_words if w in text_lower)

    # Check for repeated patterns (often indicates noise)
    is_repetitive = False
    if len(text) > 20:
        first_20 = text[:20]
        repetition = text.count(first_20)
        is_repetitive = repetition > 2

    # Calculate entropy (lower = more structured/text-like)
    char_freq = {}
    for c in text[:500]:  # Sample first 500 chars
        char_freq[c] = char_freq.get(c, 0) + 1
    total = sum(char_freq.values())
    entropy = -sum((f/total) * np.log2(f/total) for f in char_freq.values() if f > 0)

    # Score calculation
    confidence = 0

    # Printable ratio is crucial
    if printable_ratio >= 0.95:
        confidence += 40
    elif printable_ratio >= 0.85:
        confidence += 25
    elif printable_ratio >= 0.70:
        confidence += 10

    # Word matches boost confidence
    confidence += min(30, word_matches * 5)

    # Low entropy (structured text) is good
    if entropy < 4.5:
        confidence += 15
    elif entropy < 5.5:
        confidence += 5

    # Penalties
    if has_nulls:
        confidence -= 30
    if len(text) > 20 and is_repetitive:
        confidence -= 20

    # Clean preview - keep Unicode, only replace control chars
    preview_text = text[:200]
    preview_clean = ''.join(c if is_printable_unicode(c) else '·' for c in preview_text)

    is_text = confidence >= 35 and printable_ratio >= min_printable_ratio

    return {
        "is_text": is_text,
        "confidence": max(0, min(100, confidence)),
        "preview": preview_clean,
        "printable_ratio": printable_ratio,
        "entropy": entropy,
        "word_matches": word_matches,
        "reason": "looks_like_text" if is_text else "binary_data"
    }


def extract_raw_lsb(image: Image.Image, channels: list, bits: int = 1,
                    bit_offset: int = 0, max_bytes: int = 4096,
                    strategy: EncodingStrategy = EncodingStrategy.INTERLEAVED,
                    seed: int = None) -> bytes:
    """
    Extract raw LSB data without requiring STEG header.
    For blind extraction like Aperi'Solve does.

    Args:
        image: PIL Image to extract from
        channels: List of Channel enums to extract from
        bits: Bits per channel (1-8)
        bit_offset: Bit offset within each channel
        max_bytes: Maximum bytes to extract
        strategy: Encoding strategy used (SEQUENTIAL, INTERLEAVED, SPREAD, RANDOMIZED)
        seed: Random seed for RANDOMIZED strategy
    """
    img = image.convert("RGBA")
    pixels = np.array(img, dtype=np.uint8)
    height, width = pixels.shape[:2]
    total_pixels = height * width
    flat_pixels = pixels.reshape(-1, 4)

    # Create simple extraction config
    channel_indices = np.array([c.value for c in channels], dtype=np.uint8)
    num_channels = len(channels)

    # Calculate how many units we need
    bits_needed = max_bytes * 8
    units_needed = bits_needed // bits
    if bits_needed % bits:
        units_needed += 1

    bit_mask = ((1 << bits) - 1) << bit_offset
    result = np.zeros(units_needed, dtype=np.uint8)

    if strategy == EncodingStrategy.INTERLEAVED:
        # Cycle through channels at each pixel
        pixels_needed = (units_needed + num_channels - 1) // num_channels
        pixel_indices = _generate_pixel_indices(total_pixels, min(pixels_needed, total_pixels), strategy, seed)

        unit_idx = 0
        for pix_idx in pixel_indices:
            for ch in channel_indices:
                if unit_idx >= units_needed:
                    break
                value = flat_pixels[pix_idx, ch]
                result[unit_idx] = (value & bit_mask) >> bit_offset
                unit_idx += 1
            if unit_idx >= units_needed:
                break

    elif strategy == EncodingStrategy.SEQUENTIAL:
        # Fill each channel completely before moving to next
        unit_idx = 0
        for ch in channel_indices:
            pixels_for_channel = min(total_pixels, units_needed - unit_idx)
            pixel_indices = _generate_pixel_indices(total_pixels, pixels_for_channel, strategy, seed)
            for pix_idx in pixel_indices:
                if unit_idx >= units_needed:
                    break
                value = flat_pixels[pix_idx, ch]
                result[unit_idx] = (value & bit_mask) >> bit_offset
                unit_idx += 1
            if unit_idx >= units_needed:
                break

    elif strategy == EncodingStrategy.SPREAD:
        # Spread evenly across image
        pixels_needed = (units_needed + num_channels - 1) // num_channels
        pixel_indices = _generate_pixel_indices(total_pixels, min(pixels_needed, total_pixels), strategy, seed)

        unit_idx = 0
        for pix_idx in pixel_indices:
            for ch in channel_indices:
                if unit_idx >= units_needed:
                    break
                value = flat_pixels[pix_idx, ch]
                result[unit_idx] = (value & bit_mask) >> bit_offset
                unit_idx += 1
            if unit_idx >= units_needed:
                break

    elif strategy == EncodingStrategy.RANDOMIZED:
        # Pseudo-random order (seeded for reproducibility)
        pixels_needed = (units_needed + num_channels - 1) // num_channels
        pixel_indices = _generate_pixel_indices(total_pixels, min(pixels_needed, total_pixels), strategy, seed or 42)

        unit_idx = 0
        for pix_idx in pixel_indices:
            for ch in channel_indices:
                if unit_idx >= units_needed:
                    break
                value = flat_pixels[pix_idx, ch]
                result[unit_idx] = (value & bit_mask) >> bit_offset
                unit_idx += 1
            if unit_idx >= units_needed:
                break

    # Convert to bytes
    return _bits_array_to_bytes(result, bits, bits_needed)[:max_bytes]


def smart_scan_image(image: Image.Image, password: str = None) -> list:
    """
    Aperi'Solve-style multi-config scan.
    Tries multiple channel/bit/strategy combinations and reports findings.
    """
    results = []

    # Base channel/bit configurations (ordered by likelihood)
    base_configs = [
        # Common single channels - 1 bit
        {"name": "R", "channels": [Channel.R], "bits": 1},
        {"name": "G", "channels": [Channel.G], "bits": 1},
        {"name": "B", "channels": [Channel.B], "bits": 1},
        {"name": "A", "channels": [Channel.A], "bits": 1},
        # Common single channels - 2 bit
        {"name": "R-2bit", "channels": [Channel.R], "bits": 2},
        {"name": "G-2bit", "channels": [Channel.G], "bits": 2},
        {"name": "B-2bit", "channels": [Channel.B], "bits": 2},
        {"name": "A-2bit", "channels": [Channel.A], "bits": 2},
        # RGB combos - 1 and 2 bit
        {"name": "RGB", "channels": [Channel.R, Channel.G, Channel.B], "bits": 1},
        {"name": "RGB-2bit", "channels": [Channel.R, Channel.G, Channel.B], "bits": 2},
        # RGBA - 1 and 2 bit
        {"name": "RGBA", "channels": [Channel.R, Channel.G, Channel.B, Channel.A], "bits": 1},
        {"name": "RGBA-2bit", "channels": [Channel.R, Channel.G, Channel.B, Channel.A], "bits": 2},
        # Two channel combos - 1 bit
        {"name": "RG", "channels": [Channel.R, Channel.G], "bits": 1},
        {"name": "RB", "channels": [Channel.R, Channel.B], "bits": 1},
        {"name": "GB", "channels": [Channel.G, Channel.B], "bits": 1},
        {"name": "RA", "channels": [Channel.R, Channel.A], "bits": 1},
        {"name": "GA", "channels": [Channel.G, Channel.A], "bits": 1},
        {"name": "BA", "channels": [Channel.B, Channel.A], "bits": 1},
        # Two channel combos - 2 bit
        {"name": "RG-2bit", "channels": [Channel.R, Channel.G], "bits": 2},
        {"name": "RB-2bit", "channels": [Channel.R, Channel.B], "bits": 2},
        {"name": "GB-2bit", "channels": [Channel.G, Channel.B], "bits": 2},
        {"name": "RA-2bit", "channels": [Channel.R, Channel.A], "bits": 2},
        {"name": "GA-2bit", "channels": [Channel.G, Channel.A], "bits": 2},
        {"name": "BA-2bit", "channels": [Channel.B, Channel.A], "bits": 2},
        # Higher bit depths (4-bit)
        {"name": "R-4bit", "channels": [Channel.R], "bits": 4},
        {"name": "RGB-4bit", "channels": [Channel.R, Channel.G, Channel.B], "bits": 4},
    ]

    # All encoding strategies to try
    strategies_to_try = [
        {"name": "interleaved", "strategy": EncodingStrategy.INTERLEAVED},
        {"name": "sequential", "strategy": EncodingStrategy.SEQUENTIAL},
        {"name": "spread", "strategy": EncodingStrategy.SPREAD},
        {"name": "randomized", "strategy": EncodingStrategy.RANDOMIZED},
    ]

    # Generate all combinations of base configs and strategies
    configs_to_try = []
    for base in base_configs:
        for strat in strategies_to_try:
            # Interleaved is default, so omit suffix for cleaner names
            if strat["strategy"] == EncodingStrategy.INTERLEAVED:
                name = base["name"]
            else:
                name = f"{base['name']}-{strat['name']}"
            configs_to_try.append({
                "name": name,
                "channels": base["channels"],
                "bits": base["bits"],
                "strategy": strat["strategy"],
            })

    # First check for STEG header (our own format)
    detection = detect_encoding(image)
    if detection:
        results.append({
            "name": f"STEG-HEADER ({detection['config']['channels']})",
            "channels": detection['config']['channels'],
            "bits": detection['config']['bits_per_channel'],
            "has_header": True,
            "is_text": True,
            "confidence": 95,
            "preview": f"[STEG v3 detected - {format_size(detection['original_length'])}]",
            "payload_size": detection['original_length'],
            "status": "STEG_DETECTED",
            "can_decode": True,
        })

    # Scan each config
    for cfg in configs_to_try:
        try:
            raw_data = extract_raw_lsb(
                image,
                channels=cfg["channels"],
                bits=cfg["bits"],
                max_bytes=2048,  # Sample first 2KB
                strategy=cfg["strategy"]
            )

            # Check for STEG magic at start
            has_magic = raw_data[:4] == b'STEG'

            # Decrypt if password provided
            data_to_check = raw_data
            if password and not has_magic:
                try:
                    data_to_check = crypto.decrypt(raw_data, password)
                except:
                    pass  # Decryption failed, use raw

            # Analyze for coherent text
            text_analysis = detect_coherent_text(data_to_check)

            # Determine status
            if has_magic:
                status = "STEG_HEADER"
            elif text_analysis["is_text"] and text_analysis["confidence"] >= 50:
                status = "TEXT_FOUND"
            elif text_analysis["is_text"]:
                status = "POSSIBLE_TEXT"
            elif text_analysis["printable_ratio"] > 0.5:
                status = "MIXED_DATA"
            else:
                status = "BINARY/NOISE"

            results.append({
                "name": cfg["name"],
                "channels": [c.name for c in cfg["channels"]],
                "bits": cfg["bits"],
                "strategy": cfg["strategy"].value,
                "has_header": has_magic,
                "is_text": text_analysis["is_text"],
                "confidence": text_analysis["confidence"],
                "preview": text_analysis["preview"][:100] if text_analysis["preview"] else raw_data[:50].hex(),
                "printable_ratio": text_analysis.get("printable_ratio", 0),
                "entropy": text_analysis.get("entropy", 8),
                "status": status,
                "can_decode": has_magic or text_analysis["is_text"],
                "raw_data": raw_data if (has_magic or text_analysis["confidence"] >= 30) else None,
            })

        except Exception as e:
            results.append({
                "name": cfg["name"],
                "channels": [c.name for c in cfg["channels"]],
                "bits": cfg["bits"],
                "strategy": cfg["strategy"].value,
                "has_header": False,
                "is_text": False,
                "confidence": 0,
                "preview": f"Error: {str(e)[:50]}",
                "status": "ERROR",
                "can_decode": False,
            })

    # Sort by confidence (highest first), then by whether text was found
    results.sort(key=lambda x: (
        x.get("has_header", False),  # STEG headers first
        x.get("status") == "TEXT_FOUND",
        x.get("confidence", 0)
    ), reverse=True)

    return results


# ============== 🪆 MATRYOSHKA MODE - RECURSIVE STEG ==============

def is_image_data(data: bytes) -> bool:
    """Check if bytes look like an image file"""
    if len(data) < 8:
        return False
    # PNG magic bytes
    if data[:8] == b'\x89PNG\r\n\x1a\n':
        return True
    # JPEG magic bytes
    if data[:2] == b'\xff\xd8':
        return True
    # GIF magic bytes
    if data[:6] in (b'GIF87a', b'GIF89a'):
        return True
    # BMP magic bytes
    if data[:2] == b'BM':
        return True
    return False


# Valid file extensions for file format detection
VALID_FILE_EXTENSIONS = {
    # Images
    'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp', 'ico', 'svg', 'tiff', 'tif',
    # Documents
    'txt', 'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'odt', 'rtf',
    # Code
    'py', 'js', 'ts', 'html', 'css', 'json', 'xml', 'yaml', 'yml', 'md', 'csv',
    'java', 'c', 'cpp', 'h', 'hpp', 'rs', 'go', 'rb', 'php', 'sh', 'bash',
    # Archives
    'zip', 'tar', 'gz', 'bz2', '7z', 'rar',
    # Media
    'mp3', 'mp4', 'wav', 'avi', 'mkv', 'mov', 'flac', 'ogg',
    # Other
    'bin', 'dat', 'exe', 'dll', 'so', 'key', 'pem', 'crt',
}


def extract_file_from_data(data: bytes) -> tuple:
    """
    Extract filename and file data from encoded bytes.
    Returns (filename, file_data) or (None, data) if not a file format.

    File format: <length_byte><filename><file_data>
    Where length_byte is the length of the filename (1-100 bytes).
    """
    if len(data) < 3:
        return (None, data)

    fname_len = data[0]

    # Filename length must be reasonable (3-100 chars for "a.b" to reasonable max)
    if fname_len < 3 or fname_len > 100:
        return (None, data)

    # Must have enough data for filename + at least 1 byte of content
    if len(data) < fname_len + 2:
        return (None, data)

    try:
        filename = data[1:1+fname_len].decode('utf-8')
    except UnicodeDecodeError:
        return (None, data)

    # Validate filename structure
    if '.' not in filename:
        return (None, data)

    # Check for invalid characters (only allow alphanumeric, ., -, _, space)
    if not re.match(r'^[\w\-. ]+$', filename):
        return (None, data)

    # Filename must not start with . or space
    if filename[0] in '. ':
        return (None, data)

    # Extract and validate extension
    ext = filename.rsplit('.', 1)[-1].lower()
    if ext not in VALID_FILE_EXTENSIONS:
        return (None, data)

    # All checks passed - this looks like a real file
    file_data = data[1+fname_len:]
    return (filename, file_data)


def matryoshka_decode(image: Image.Image, max_depth: int = 3, password: str = None,
                      current_depth: int = 0) -> list:
    """
    🪆 Recursively decode nested steganographic images.

    Args:
        image: The image to decode
        max_depth: Maximum recursion depth (1-11)
        password: Optional decryption password
        current_depth: Current recursion level (internal)

    Returns:
        List of extraction results at each layer
    """
    results = []
    layer_info = {
        "depth": current_depth,
        "type": "unknown",
        "filename": None,
        "data_size": 0,
        "preview": "",
        "has_nested": False,
        "nested_results": [],
    }

    if current_depth >= max_depth:
        layer_info["type"] = "max_depth_reached"
        layer_info["preview"] = f"⚠️ Max depth ({max_depth}) reached"
        results.append(layer_info)
        return results

    try:
        # Try auto-decode first (looks for STEG header)
        try:
            data = decode(image, None)
            layer_info["type"] = "steg_header"
        except:
            # If no STEG header, try smart scan
            scan_results = smart_scan_image(image, password)
            best_result = None
            for r in scan_results:
                if r.get("status") in ["STEG_DETECTED", "STEG_HEADER", "TEXT_FOUND"]:
                    best_result = r
                    break

            if best_result and best_result.get("raw_data"):
                data = best_result["raw_data"]
                layer_info["type"] = f"smart_scan_{best_result['name']}"
            else:
                layer_info["type"] = "no_data_found"
                layer_info["preview"] = "No hidden data detected"
                results.append(layer_info)
                return results

        # Decrypt if password provided
        if password:
            try:
                data = crypto.decrypt(data, password)
            except:
                pass  # Decryption failed, use raw data

        layer_info["data_size"] = len(data)

        # Check if it's a file
        filename, file_data = extract_file_from_data(data)

        if filename:
            layer_info["filename"] = filename
            layer_info["data_size"] = len(file_data)

            # Check if the extracted file is an image
            if is_image_data(file_data):
                layer_info["type"] = "nested_image"
                layer_info["has_nested"] = True

                # Recursively decode the nested image
                try:
                    nested_img = Image.open(io.BytesIO(file_data))
                    nested_results = matryoshka_decode(
                        nested_img,
                        max_depth=max_depth,
                        password=password,
                        current_depth=current_depth + 1
                    )
                    layer_info["nested_results"] = nested_results
                    layer_info["preview"] = f"🪆 Found nested image: {filename}"
                except Exception as e:
                    layer_info["preview"] = f"📁 Image file: {filename} (failed to recurse: {e})"
            else:
                layer_info["type"] = "file"
                # Try to show preview of text files
                ext = filename.split('.')[-1].lower() if '.' in filename else ''
                if ext in ['txt', 'md', 'json', 'xml', 'html', 'css', 'js', 'py', 'csv']:
                    try:
                        layer_info["preview"] = file_data[:200].decode('utf-8')
                    except:
                        layer_info["preview"] = f"📁 Binary file: {filename}"
                else:
                    layer_info["preview"] = f"📁 File: {filename} ({format_size(len(file_data))})"
        else:
            # Raw data - check if it's an image
            if is_image_data(data):
                layer_info["type"] = "nested_image_raw"
                layer_info["has_nested"] = True

                try:
                    nested_img = Image.open(io.BytesIO(data))
                    nested_results = matryoshka_decode(
                        nested_img,
                        max_depth=max_depth,
                        password=password,
                        current_depth=current_depth + 1
                    )
                    layer_info["nested_results"] = nested_results
                    layer_info["preview"] = "🪆 Found raw nested image data"
                except Exception as e:
                    layer_info["preview"] = f"Image data (failed to recurse: {e})"
            else:
                # Try as text
                try:
                    text = data.decode('utf-8')
                    layer_info["type"] = "text"
                    layer_info["preview"] = text[:300]
                except:
                    layer_info["type"] = "binary"
                    layer_info["preview"] = f"Binary data: {data[:50].hex()}..."

        # Store raw data for download
        layer_info["raw_data"] = file_data if filename else data

    except Exception as e:
        layer_info["type"] = "error"
        layer_info["preview"] = f"Error: {str(e)}"

    results.append(layer_info)
    return results


def matryoshka_encode(payload: bytes, carriers: list, config = None,
                      password: str = None) -> tuple:
    """
    🪆 Recursively encode nested steganographic images.

    Creates a "Russian nesting doll" of hidden data, encoding the payload
    into the innermost carrier, then that result into the next carrier, etc.

    Args:
        payload: The data to hide (innermost secret)
        carriers: List of (Image, filename) tuples - innermost carrier FIRST
        config: StegConfig to use for all layers (or None for auto)
        password: Optional encryption password

    Returns:
        Tuple of (final_image, layer_info_list)
    """
    if not carriers:
        raise ValueError("At least one carrier image is required")

    if config is None:
        config = create_config(channels='RGBA', bits=2)  # Default: good capacity

    layer_info = []
    current_data = payload

    # Encode from innermost to outermost
    for i, (carrier_img, carrier_name) in enumerate(carriers):
        layer_num = i + 1

        # Calculate capacity
        capacity = _calculate_capacity_bytes(carrier_img, config)
        data_size = len(current_data)

        layer_info.append({
            'layer': layer_num,
            'carrier': carrier_name,
            'capacity': capacity,
            'payload_size': data_size,
            'fits': data_size <= capacity
        })

        if data_size > capacity:
            raise ValueError(f"Layer {layer_num} ({carrier_name}): payload {data_size} bytes exceeds capacity {capacity} bytes")

        # Encrypt if password provided (only innermost layer or all?)
        data_to_encode = current_data
        if password and i == 0:  # Only encrypt the innermost payload
            data_to_encode = crypto.encrypt(current_data, password)

        # Encode current data into this carrier
        encoded_img = encode(carrier_img, data_to_encode, config)

        # If there are more carriers, convert this to PNG bytes for next layer
        if i < len(carriers) - 1:
            buffer = io.BytesIO()
            encoded_img.save(buffer, format='PNG')
            current_data = buffer.getvalue()
            layer_info[-1]['output_size'] = len(current_data)
        else:
            # Final layer - return the image
            layer_info[-1]['output_size'] = 'final'

    return encoded_img, layer_info


def _calculate_capacity_bytes(image: Image.Image, config) -> int:
    """Calculate byte capacity for an image with given config (simplified, returns int)"""
    width, height = image.size
    channels = len(config.channels)
    bits = config.bits_per_channel
    # Account for STEG header overhead (~48 bytes)
    raw_capacity = (width * height * channels * bits) // 8
    return max(0, raw_capacity - 64)  # Reserve space for header


# ============== UI COMPONENTS ==============

def create_header():
    """Create the main header with ASCII art"""
    with ui.column().classes('w-full items-center'):
        ui.html(f'<pre style="color: #00ff00; font-size: 8px; line-height: 1.1; text-align: center;">{BANNER_ASCII}</pre>', sanitize=False)
        ui.label('🦕 Ultimate LSB Steganography Suite 🦕').classes('text-cyan-400 text-lg')


def create_channel_selector(advanced: bool = False):
    """Create channel selection UI"""
    if advanced:
        # All 15 presets
        options = list(CHANNEL_PRESETS.keys())
    else:
        # Simple options
        options = ['RGB', 'RGBA', 'R', 'G', 'B']
    return options


def create_capacity_display(capacity_label: ui.label, image: Image.Image, config_dict: dict):
    """Update capacity display"""
    if image is None:
        capacity_label.set_text('No image loaded')
        return

    config = create_config(**config_dict)
    cap = calculate_capacity(image, config)

    text = f"📊 Capacity: {cap['human']} ({cap['usable_bytes']:,} bytes)"
    capacity_label.set_text(text)
    state.capacity_info = cap


def create_file_picker(element_id: str, accept: str, endpoint: str, tab: str = 'encode'):
    """Create a custom file picker that works with Python 3.9

    Returns tuple of (html, javascript) - call ui.html() for html and ui.add_body_html() for js
    Args:
        element_id: Unique ID for the element
        accept: File types to accept
        endpoint: API endpoint to POST to
        tab: Tab name to restore after reload ('encode', 'decode', 'analyze')
    """
    # Cleaner accept display
    accept_display = accept.replace(',', ' · ').replace('.', '').upper() if accept != '*' else 'ANY FILE'

    html = f"""
    <div class="drop-zone" id="{element_id}_zone" onclick="document.getElementById('{element_id}').click()">
        <div style="color: #00ff41; font-size: 13px; font-weight: 500;">
            <span style="opacity: 0.7;">↑</span> DROP FILE OR CLICK TO BROWSE
        </div>
        <div style="color: #555; font-size: 11px; margin-top: 6px; letter-spacing: 1px;">{accept_display}</div>
        <input type="file" id="{element_id}" accept="{accept}" style="display: none;"
            onchange="handleFileSelect_{element_id}(this.files[0])">
    </div>
    """

    js = f"""
    <script>
        function handleFileSelect_{element_id}(file) {{
            if (!file) return;
            const reader = new FileReader();
            reader.onload = async function(e) {{
                const base64 = e.target.result;
                try {{
                    const response = await fetch('{endpoint}', {{
                        method: 'POST',
                        headers: {{'Content-Type': 'application/json'}},
                        body: JSON.stringify({{data: base64, filename: file.name, tab: '{tab}'}})
                    }});
                    const result = await response.json();
                    if (result.success) {{
                        // Reload with hash to preserve tab state
                        window.location.hash = '{tab}';
                        window.location.reload();
                    }} else {{
                        alert('Upload failed: ' + result.error);
                    }}
                }} catch (err) {{
                    alert('Upload error: ' + err.message);
                }}
            }};
            reader.readAsDataURL(file);
        }}

        // Drag and drop support - wait for DOM
        setTimeout(function() {{
            const zone = document.getElementById('{element_id}_zone');
            if (!zone) return;
            zone.addEventListener('dragover', (e) => {{
                e.preventDefault();
                zone.style.borderColor = '#00ffff';
                zone.style.background = 'rgba(0, 255, 255, 0.1)';
            }});
            zone.addEventListener('dragleave', (e) => {{
                zone.style.borderColor = '#00ff00';
                zone.style.background = 'rgba(0, 255, 0, 0.05)';
            }});
            zone.addEventListener('drop', (e) => {{
                e.preventDefault();
                zone.style.borderColor = '#00ff00';
                zone.style.background = 'rgba(0, 255, 0, 0.05)';
                if (e.dataTransfer.files.length > 0) {{
                    handleFileSelect_{element_id}(e.dataTransfer.files[0]);
                }}
            }});
        }}, 100);
    </script>
    """
    return html, js


# ============== API ENDPOINTS FOR FILE UPLOADS ==============

@app.post('/api/upload/carrier')
async def upload_carrier(request: Request):
    """Handle carrier image upload"""
    try:
        body = await request.json()
        b64_data = body.get('data', '')
        filename = body.get('filename', 'image.png')
        tab = body.get('tab', 'encode')

        state.carrier_image = base64_to_image(b64_data)
        state.carrier_path = filename
        state.active_tab = tab
        return JSONResponse({'success': True, 'filename': filename})
    except Exception as e:
        return JSONResponse({'success': False, 'error': str(e)})


@app.post('/api/upload/payload')
async def upload_payload(request: Request):
    """Handle payload file upload"""
    try:
        body = await request.json()
        b64_data = body.get('data', '')
        filename = body.get('filename', 'file.bin')
        tab = body.get('tab', 'encode')

        # Decode base64 data
        if ',' in b64_data:
            b64_data = b64_data.split(',')[1]
        state.encode_file_data = base64.b64decode(b64_data)
        state.encode_file_name = filename
        state.active_tab = tab
        return JSONResponse({'success': True, 'filename': filename})
    except Exception as e:
        return JSONResponse({'success': False, 'error': str(e)})


@app.post('/api/upload/decode')
async def upload_decode(request: Request):
    """Handle decode image upload"""
    try:
        body = await request.json()
        b64_data = body.get('data', '')
        filename = body.get('filename', 'image.png')
        tab = body.get('tab', 'decode')

        state.decode_image = base64_to_image(b64_data)
        state.active_tab = tab

        # Try auto-detection
        detection = detect_encoding(state.decode_image)
        state.detected_config = detection

        return JSONResponse({
            'success': True,
            'filename': filename,
            'detected': detection is not None,
            'config': detection['config'] if detection else None,
            'payload_size': detection['original_length'] if detection else 0
        })
    except Exception as e:
        return JSONResponse({'success': False, 'error': str(e)})


@app.post('/api/upload/analyze')
async def upload_analyze(request: Request):
    """Handle analyze image upload"""
    try:
        body = await request.json()
        b64_data = body.get('data', '')
        filename = body.get('filename', 'image.png')
        tab = body.get('tab', 'analyze')

        state.analyze_image = base64_to_image(b64_data)
        state.active_tab = tab
        return JSONResponse({'success': True, 'filename': filename})
    except Exception as e:
        return JSONResponse({'success': False, 'error': str(e)})


@app.post('/api/matryoshka/toggle')
async def toggle_matryoshka(request: Request):
    """🪆 Toggle Matryoshka mode"""
    try:
        body = await request.json()
        active = body.get('active', False)
        state.matryoshka_mode = active
        return JSONResponse({
            'success': True,
            'matryoshka_active': state.matryoshka_mode,
            'depth': state.matryoshka_depth
        })
    except Exception as e:
        return JSONResponse({'success': False, 'error': str(e)})


@app.post('/api/matryoshka/decode')
async def matryoshka_decode_api(request: Request):
    """🪆 Perform recursive Matryoshka decode"""
    try:
        body = await request.json()
        depth = body.get('depth', state.matryoshka_depth)
        password = body.get('password', None)

        if state.decode_image is None:
            return JSONResponse({'success': False, 'error': 'No image loaded'})

        results = matryoshka_decode(state.decode_image, max_depth=depth, password=password)
        state.matryoshka_results = results

        # Flatten results for JSON response
        def flatten_results(res_list, level=0):
            flat = []
            for r in res_list:
                flat.append({
                    'depth': r.get('depth', level),
                    'type': r.get('type', 'unknown'),
                    'filename': r.get('filename'),
                    'data_size': r.get('data_size', 0),
                    'preview': r.get('preview', '')[:500],
                    'has_nested': r.get('has_nested', False),
                })
                if r.get('nested_results'):
                    flat.extend(flatten_results(r['nested_results'], level + 1))
            return flat

        flat_results = flatten_results(results)

        return JSONResponse({
            'success': True,
            'layers_found': len(flat_results),
            'results': flat_results
        })
    except Exception as e:
        return JSONResponse({'success': False, 'error': str(e)})


@app.post('/api/matryoshka/add_carrier')
async def add_matryoshka_carrier(request: Request):
    """🪆 Add a carrier image to the Matryoshka stack"""
    try:
        body = await request.json()
        b64_data = body.get('data', '')
        filename = body.get('filename', 'carrier.png')

        img = base64_to_image(b64_data)
        state.matryoshka_carriers.append((img, filename))

        # Calculate capacity for this carrier
        config = create_config(channels='RGBA', bits=2)
        capacity = _calculate_capacity_bytes(img, config)

        return JSONResponse({
            'success': True,
            'carrier_count': len(state.matryoshka_carriers),
            'filename': filename,
            'dimensions': f"{img.size[0]}x{img.size[1]}",
            'capacity': capacity
        })
    except Exception as e:
        return JSONResponse({'success': False, 'error': str(e)})


@app.post('/api/matryoshka/clear_carriers')
async def clear_matryoshka_carriers():
    """🪆 Clear all Matryoshka carrier images"""
    state.matryoshka_carriers = []
    state.matryoshka_encode_result = None
    return JSONResponse({'success': True, 'carrier_count': 0})


@app.post('/api/matryoshka/encode')
async def matryoshka_encode_api(request: Request):
    """🪆 Perform recursive Matryoshka encode"""
    try:
        body = await request.json()
        password = body.get('password')
        channels = body.get('channels', 'RGBA')
        bits = body.get('bits', 2)

        if not state.matryoshka_carriers:
            return JSONResponse({'success': False, 'error': 'No carrier images added'})

        # Get payload - either from encode_file_data or encode_text
        if state.encode_file_data:
            payload = state.encode_file_data
            # Prepend filename if available
            if state.encode_file_name:
                fn_bytes = state.encode_file_name.encode('utf-8')
                payload = bytes([len(fn_bytes)]) + fn_bytes + payload
        elif hasattr(state, 'encode_text') and state.encode_text:
            payload = state.encode_text.encode('utf-8')
        else:
            return JSONResponse({'success': False, 'error': 'No payload to encode. Upload a file or enter text first.'})

        config = create_config(channels=channels, bits=bits)

        # Carriers are stored outermost-first in UI, but we need innermost-first for encoding
        # So reverse the list
        carriers_reversed = list(reversed(state.matryoshka_carriers))

        result_img, layer_info = matryoshka_encode(
            payload=payload,
            carriers=carriers_reversed,
            config=config,
            password=password
        )

        state.matryoshka_encode_result = result_img

        # Convert result to base64 for preview
        buffer = io.BytesIO()
        result_img.save(buffer, format='PNG')
        result_b64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

        return JSONResponse({
            'success': True,
            'layers': len(state.matryoshka_carriers),
            'layer_info': layer_info,
            'result_b64': f"data:image/png;base64,{result_b64}"
        })
    except Exception as e:
        return JSONResponse({'success': False, 'error': str(e)})


@app.get('/api/matryoshka/download')
async def download_matryoshka_result():
    """🪆 Download the Matryoshka encoded result"""
    if state.matryoshka_encode_result is None:
        return JSONResponse({'success': False, 'error': 'No result to download'})

    buffer = io.BytesIO()
    state.matryoshka_encode_result.save(buffer, format='PNG')
    buffer.seek(0)

    return Response(
        content=buffer.getvalue(),
        media_type='image/png',
        headers={'Content-Disposition': 'attachment; filename="matryoshka_encoded.png"'}
    )


# ============== MAIN PAGE ==============

@ui.page('/')
async def main_page():
    # Add custom CSS
    ui.add_head_html(f'<style>{DARK_CSS}</style>')
    ui.add_head_html('<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">')

    # Matrix scanline overlay
    ui.html('<div class="matrix-bg"></div>', sanitize=False)

    with ui.column().classes('w-full max-w-6xl mx-auto p-4 gap-4'):
        create_header()

        # Tab navigation
        with ui.tabs().classes('w-full') as tabs:
            encode_tab = ui.tab('ENCODE', icon='lock').classes('text-green-400')
            decode_tab = ui.tab('DECODE', icon='lock_open').classes('text-cyan-400')
            analyze_tab = ui.tab('ANALYZE', icon='search').classes('text-yellow-400')
            # 🪆 Hidden Matryoshka tab - revealed by easter egg
            matryoshka_tab = ui.tab('🪆 MATRYOSHKA', icon='auto_awesome').classes('text-pink-400')
            matryoshka_tab.props('id="matryoshka-tab"')
            matryoshka_tab.style('display: none;')  # Hidden until activated

        # Determine initial tab from state (set by API) or URL hash
        tab_map = {
            'encode': encode_tab,
            'decode': decode_tab,
            'analyze': analyze_tab,
            'matryoshka': matryoshka_tab,
        }
        initial_tab = tab_map.get(state.active_tab, encode_tab)

        with ui.tab_panels(tabs, value=initial_tab).classes('w-full') as panels:

            # ==================== ENCODE PANEL ====================
            with ui.tab_panel(encode_tab):
                await create_encode_panel()

            # ==================== DECODE PANEL ====================
            with ui.tab_panel(decode_tab):
                await create_decode_panel()

            # ==================== ANALYZE PANEL ====================
            with ui.tab_panel(analyze_tab):
                await create_analyze_panel()

            # ==================== MATRYOSHKA PANEL ====================
            with ui.tab_panel(matryoshka_tab):
                await create_matryoshka_panel()

        # JavaScript to read URL hash on load and sync tabs
        ui.add_body_html("""
        <script>
            // On page load, check URL hash and click the correct tab
            document.addEventListener('DOMContentLoaded', function() {
                const hash = window.location.hash.replace('#', '');
                if (hash) {
                    // Find and click the tab button
                    const tabButtons = document.querySelectorAll('.q-tab');
                    tabButtons.forEach(btn => {
                        if (btn.textContent.trim().toLowerCase().includes(hash.toLowerCase())) {
                            btn.click();
                        }
                    });
                }
            });

            // Update hash when tab changes
            document.addEventListener('click', function(e) {
                const tab = e.target.closest('.q-tab');
                if (tab) {
                    const tabName = tab.textContent.trim().toLowerCase();
                    if (['encode', 'decode', 'analyze'].includes(tabName)) {
                        window.location.hash = tabName;
                    }
                }
            });
        </script>
        """)

        # Footer
        ui.html('<div style="text-align: center; color: #666; margin-top: 20px;">.-.-.-.-<={LOVE PLINY}=>-.-.-.-.</div>', sanitize=False)

        # 🪆 MATRYOSHKA MODE - Easter egg trigger zone (bottom-left pixel)
        ui.html('<div class="matryoshka-trigger" id="matryoshka-trigger" title="🪆"></div>', sanitize=False)

        # Simple mode indicator (shown when active)
        ui.html('''
            <div id="matryoshka-indicator" class="hidden" style="
                position: fixed; bottom: 20px; right: 20px; z-index: 9999;
                background: linear-gradient(135deg, #1a0020 0%, #0d0015 100%);
                border: 2px solid #ff00ff; border-radius: 8px; padding: 8px 16px;
                cursor: pointer;
            " onclick="deactivateMatryoshka()">
                <span style="color: #ff00ff; font-weight: bold;">🪆 MATRYOSHKA MODE</span>
                <span style="color: #ff99ff; font-size: 10px; margin-left: 8px;">click to deactivate</span>
            </div>
        ''', sanitize=False)

        # JavaScript to handle easter egg activation
        ui.add_body_html("""
        <script>
            // 🪆 Matryoshka Mode Easter Egg
            let matryoshkaActive = false;

            function activateMatryoshka() {
                matryoshkaActive = true;

                // Show the hidden tab
                const tab = document.getElementById('matryoshka-tab');
                if (tab) {
                    tab.style.display = '';
                    // Click the tab to switch to it
                    setTimeout(() => tab.click(), 100);
                }

                // Show indicator
                const indicator = document.getElementById('matryoshka-indicator');
                if (indicator) indicator.classList.remove('hidden');

                document.body.classList.add('matryoshka-active');

                // Send activation to backend
                fetch('/api/matryoshka/toggle', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({active: true})
                });

                console.log('🪆 MATRYOSHKA MODE ACTIVATED 🪆');
            }

            function deactivateMatryoshka() {
                matryoshkaActive = false;

                // Hide the tab
                const tab = document.getElementById('matryoshka-tab');
                if (tab) tab.style.display = 'none';

                // Hide indicator
                const indicator = document.getElementById('matryoshka-indicator');
                if (indicator) indicator.classList.add('hidden');

                document.body.classList.remove('matryoshka-active');

                // Switch back to encode tab
                const encodeTab = document.querySelector('.q-tab');
                if (encodeTab) encodeTab.click();

                fetch('/api/matryoshka/toggle', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({active: false})
                });

                console.log('🪆 Matryoshka mode deactivated');
            }

            (function() {
                let attempts = 0;
                const maxAttempts = 50;

                function setupMatryoshka() {
                    const trigger = document.getElementById('matryoshka-trigger');

                    if (!trigger) {
                        attempts++;
                        if (attempts < maxAttempts) {
                            setTimeout(setupMatryoshka, 100);
                        }
                        return;
                    }

                    console.log('🪆 Matryoshka trigger initialized');

                    trigger.addEventListener('click', function(e) {
                        e.preventDefault();
                        e.stopPropagation();

                        if (!matryoshkaActive) {
                            activateMatryoshka();
                        } else {
                            deactivateMatryoshka();
                        }
                    });

                    // Touch events for mobile
                    trigger.addEventListener('touchend', function(e) {
                        e.preventDefault();
                        trigger.click();
                    });
                }

                if (document.readyState === 'loading') {
                    document.addEventListener('DOMContentLoaded', setupMatryoshka);
                } else {
                    setTimeout(setupMatryoshka, 500);
                }
            })();

            // 🪆 Matryoshka carrier upload handler
            function addMatryoshkaCarrier(file) {
                if (!file) return;
                const reader = new FileReader();
                reader.onload = async function(e) {
                    const base64 = e.target.result;
                    try {
                        const response = await fetch('/api/matryoshka/add_carrier', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({data: base64, filename: file.name})
                        });
                        const result = await response.json();
                        if (result.success) {
                            // Reload to refresh carrier list
                            window.location.reload();
                        } else {
                            alert('Failed to add carrier: ' + result.error);
                        }
                    } catch (err) {
                        alert('Upload error: ' + err.message);
                    }
                };
                reader.readAsDataURL(file);
            }
        </script>
        """)


async def create_encode_panel():
    """Create the encoding interface"""

    # Use global state for persistence
    global state

    with ui.row().classes('w-full gap-4'):
        # Left column - Image upload and preview
        with ui.column().classes('w-1/2 gap-2'):
            ui.label('📷 CARRIER IMAGE').classes('text-green-400 text-lg font-bold')

            # Show current image if loaded
            if state.carrier_image:
                b64 = image_to_base64(state.carrier_image)
                ui.image(f'data:image/png;base64,{b64}').classes('w-full max-h-64 object-contain')
                w, h = state.carrier_image.size
                ui.label(f'{state.carrier_path or "Generated"} | {w}x{h}').classes('text-green-400 text-sm')

                # Show capacity
                try:
                    config = create_config(channels='RGB', bits=1)
                    cap = calculate_capacity(state.carrier_image, config)
                    ui.label(f"📊 Capacity: {cap['human']} ({cap['usable_bytes']:,} bytes)").classes('text-cyan-400')
                except:
                    pass
            else:
                ui.image().classes('w-full max-h-64 object-contain')
                ui.label('No image loaded').classes('text-gray-500 text-sm')
                ui.label('📊 Capacity: --').classes('text-cyan-400')

            # Custom file picker - uses API endpoint
            picker_html, picker_js = create_file_picker('encode_carrier', '.png,.PNG,image/png', '/api/upload/carrier', tab='encode')
            ui.html(picker_html, sanitize=False)
            ui.add_body_html(picker_js)

            # Generate image buttons
            ui.label('Or generate a carrier:').classes('text-gray-500 text-sm mt-2')

            # Size selector for generated images
            with ui.row().classes('gap-2 items-center'):
                gen_size_select = ui.select(
                    options=['512x512', '1024x1024', '2048x2048', '4096x4096'],
                    value='1024x1024',
                    label='Size'
                ).props('dense').classes('w-24')

            with ui.row().classes('gap-2'):
                async def gen_image(color: str):
                    size_str = gen_size_select.value or '1024x1024'
                    w, h = map(int, size_str.split('x'))
                    state.carrier_image = generate_blank_image(w, h, color)
                    state.carrier_path = f'{color}_{size_str}.png'
                    state.active_tab = 'encode'
                    ui.notify(f'Generated {color} image ({size_str})', type='positive')
                    await asyncio.sleep(0.3)
                    await ui.run_javascript('window.location.hash = "encode"; window.location.reload();')

                ui.button('🎲 Noise', on_click=lambda: gen_image('noise')).props('dense').classes('text-xs')
                ui.button('⬛ Black', on_click=lambda: gen_image('black')).props('dense').classes('text-xs')
                ui.button('🌈 Gradient', on_click=lambda: gen_image('gradient')).props('dense').classes('text-xs')
                ui.button('⬜ White', on_click=lambda: gen_image('white')).props('dense').classes('text-xs')

        # Right column - Data and settings
        with ui.column().classes('w-1/2 gap-2'):
            ui.label('📝 PAYLOAD DATA').classes('text-green-400 text-lg font-bold')

            # Data source toggle
            with ui.row().classes('gap-2'):
                data_source = ui.toggle(
                    {
                        'text': '💬 Text',
                        'file': '📁 File',
                    },
                    value='text'
                ).classes('w-full')

            # Text input
            text_container = ui.column().classes('w-full')
            with text_container:
                text_input = ui.textarea(
                    label='Secret message',
                    placeholder='Enter your hidden message here...'
                ).classes('w-full').props('rows=6 dark')

            # File upload for payload
            file_container = ui.column().classes('w-full hidden')
            with file_container:
                if state.encode_file_data and state.encode_file_name:
                    ui.label(f'📄 {state.encode_file_name} ({format_size(len(state.encode_file_data))})').classes('text-green-400')
                else:
                    ui.label('No file selected').classes('text-gray-500')

                payload_html, payload_js = create_file_picker('encode_payload', '*', '/api/upload/payload', tab='encode')
                ui.html(payload_html, sanitize=False)
                ui.add_body_html(payload_js)

            def toggle_data_source():
                if data_source.value == 'text':
                    text_container.classes(remove='hidden')
                    file_container.classes(add='hidden')
                else:
                    text_container.classes(add='hidden')
                    file_container.classes(remove='hidden')

            data_source.on('update:model-value', toggle_data_source)

            ui.separator().classes('my-2')

            # ===== ENCODING SETTINGS =====
            ui.label('⚙️ ENCODING SETTINGS').classes('text-green-400 text-lg font-bold')

            # Advanced mode toggle
            advanced_toggle = ui.switch('🔧 Advanced Mode').classes('text-cyan-400')

            # Basic settings (always visible)
            with ui.row().classes('w-full gap-4'):
                channel_select = ui.select(
                    label='Channels',
                    options=['RGB', 'RGBA', 'R', 'G', 'B'],
                    value='RGB'
                ).classes('w-1/2')

                bits_select = ui.select(
                    label='Bits/Channel',
                    options=[1, 2],
                    value=1
                ).classes('w-1/2')

            # Live capacity display
            capacity_display = ui.html('', sanitize=False).classes('w-full')

            def update_capacity_display():
                """Update capacity display based on current settings"""
                if state.carrier_image is None:
                    capacity_display.set_content(
                        '<div style="color: #666; padding: 8px; border: 1px solid #333; border-radius: 4px;">'
                        '📊 Capacity: Load an image to see capacity'
                        '</div>'
                    )
                    return

                try:
                    if advanced_toggle.value:
                        ch = adv_channel_select.value or 'RGB'
                        b = adv_bits_select.value or 1
                    else:
                        ch = channel_select.value or 'RGB'
                        b = bits_select.value or 1

                    config = create_config(channels=ch, bits=b)
                    cap = calculate_capacity(state.carrier_image, config)

                    # Calculate fill percentage if we have data
                    data_size = 0
                    if data_source.value == 'text' and text_input.value:
                        data_size = len(text_input.value.encode('utf-8'))
                    elif data_source.value == 'file' and state.encode_file_data:
                        data_size = len(state.encode_file_data) + len(state.encode_file_name or '') + 1

                    # Don't cap at 100% - we need to detect overflow!
                    fill_pct = (data_size / max(1, cap['usable_bytes'])) * 100
                    bar_width = min(100, fill_pct)

                    if fill_pct > 100:
                        color = '#ff3333'
                        bar_color = '#ff3333'
                        status = 'OVER CAPACITY'
                        icon = '⛔'
                    elif fill_pct > 80:
                        color = '#ffd000'
                        bar_color = '#ffd000'
                        status = 'NEARLY FULL'
                        icon = '⚠️'
                    elif fill_pct > 0:
                        color = '#00ff41'
                        bar_color = '#00ff41'
                        status = 'READY'
                        icon = '✓'
                    else:
                        color = '#555'
                        bar_color = '#333'
                        status = 'NO DATA'
                        icon = '○'

                    capacity_display.set_content(
                        f'<div class="capacity-meter">'
                        f'<div style="display: flex; justify-content: space-between; align-items: center;">'
                        f'<span style="color: #00ff41; font-size: 12px; font-weight: 600;">CAPACITY</span>'
                        f'<span style="color: #888; font-size: 11px;">{cap["usable_bytes"]:,} bytes</span>'
                        f'</div>'
                        f'<div class="capacity-bar-outer">'
                        f'<div class="capacity-bar-inner" style="width: {bar_width:.1f}%; background: {bar_color};"></div>'
                        f'</div>'
                        f'<div style="display: flex; justify-content: space-between; align-items: center; font-size: 11px;">'
                        f'<span style="color: {color};">{icon} {status}</span>'
                        f'<span style="color: #888;">{format_size(data_size)} / {cap["human"]} ({fill_pct:.1f}%)</span>'
                        f'</div>'
                        f'</div>'
                    )

                    # Store capacity for encode check
                    state.capacity_info = cap

                except Exception as e:
                    capacity_display.set_content(f'<div style="color: #ff3333;">Error: {e}</div>')

            # Update capacity on various changes
            if state.carrier_image:
                update_capacity_display()

            # Advanced settings (hidden by default)
            advanced_container = ui.column().classes('w-full hidden gap-2')
            with advanced_container:
                ui.label('🎯 Channel & Bit Configuration').classes('text-yellow-400 text-sm')

                with ui.row().classes('w-full gap-4'):
                    # All channel presets
                    adv_channel_select = ui.select(
                        label='All Channel Presets',
                        options=list(CHANNEL_PRESETS.keys()),
                        value='RGB'
                    ).classes('w-1/2')

                    # Full bits range
                    adv_bits_select = ui.select(
                        label='Bits (1-8)',
                        options=list(range(1, 9)),
                        value=1
                    ).classes('w-1/2')

                with ui.row().classes('w-full gap-4'):
                    strategy_select = ui.select(
                        label='Strategy',
                        options=['interleaved', 'sequential', 'spread', 'randomized'],
                        value='interleaved'
                    ).classes('w-1/2')

                    bit_offset_select = ui.select(
                        label='Bit Offset (0=LSB, 7=MSB)',
                        options=list(range(8)),
                        value=0
                    ).classes('w-1/2')

                ui.separator().classes('my-2')
                ui.label('🎲 Randomization').classes('text-yellow-400 text-sm')

                with ui.row().classes('w-full gap-4'):
                    seed_input = ui.number(
                        label='Random Seed (manual)',
                        value=None,
                        placeholder='Optional'
                    ).classes('w-1/2')

                    seed_password = ui.input(
                        label='Or derive seed from password',
                        placeholder='Enter passphrase...'
                    ).classes('w-1/2')

                def derive_seed_from_password():
                    """Derive a numeric seed from password hash"""
                    if seed_password.value:
                        import hashlib
                        hash_bytes = hashlib.sha256(seed_password.value.encode()).digest()
                        derived = int.from_bytes(hash_bytes[:4], 'big')
                        seed_input.value = derived
                        ui.notify(f'Derived seed: {derived}', type='info')

                ui.button('🔑 Derive Seed', on_click=derive_seed_from_password).props('dense').classes('text-xs')

                ui.separator().classes('my-2')
                ui.label('🛡️ Stealth & Obfuscation').classes('text-yellow-400 text-sm')

                with ui.row().classes('w-full gap-4'):
                    compress_toggle = ui.switch('Compress data', value=True).classes('w-1/2')
                    invert_toggle = ui.switch('XOR invert bits', value=False).classes('w-1/2')

                ui.html(
                    '<div style="color: #666; font-size: 11px; margin-top: 4px;">'
                    '• Compression reduces payload size but adds header bytes<br>'
                    '• XOR invert flips all bits for additional obfuscation'
                    '</div>', sanitize=False
                )

                ui.separator().classes('my-2')
                ui.label('📊 Encoding Statistics').classes('text-yellow-400 text-sm')

                stats_display = ui.html('', sanitize=False)

                def update_stats():
                    """Show encoding statistics preview"""
                    if state.carrier_image is None:
                        stats_display.set_content('<div style="color: #666;">Load carrier to see stats</div>')
                        return

                    w, h = state.carrier_image.size
                    total_pixels = w * h

                    ch = adv_channel_select.value or 'RGB'
                    b = adv_bits_select.value or 1
                    num_channels = len(CHANNEL_PRESETS.get(ch, []))

                    bits_per_pixel = num_channels * b
                    total_bits = total_pixels * bits_per_pixel
                    total_bytes = total_bits // 8

                    # Estimate pixels modified for a 1KB payload
                    sample_payload = 1024 * 8  # 1KB in bits
                    pixels_for_1kb = sample_payload // bits_per_pixel if bits_per_pixel else 0

                    stats_display.set_content(
                        f'<div style="font-family: monospace; font-size: 11px; color: #888;">'
                        f'Image: {w}x{h} = {total_pixels:,} pixels<br>'
                        f'Channels: {ch} ({num_channels} channels)<br>'
                        f'Bits/pixel: {bits_per_pixel} ({b} bits × {num_channels} ch)<br>'
                        f'Raw capacity: {total_bytes:,} bytes<br>'
                        f'Pixels for 1KB: ~{pixels_for_1kb:,} ({pixels_for_1kb/total_pixels*100:.2f}% of image)'
                        f'</div>'
                    )

                # Initial stats update
                update_stats()

                # Update stats when settings change
                adv_channel_select.on('update:model-value', lambda: (update_stats(), update_capacity_display()))
                adv_bits_select.on('update:model-value', lambda: (update_stats(), update_capacity_display()))

            def toggle_advanced():
                if advanced_toggle.value:
                    advanced_container.classes(remove='hidden')
                    # Sync values
                    adv_channel_select.value = channel_select.value
                    adv_bits_select.value = bits_select.value
                    update_stats()
                    update_capacity_display()
                else:
                    advanced_container.classes(add='hidden')
                    update_capacity_display()

            advanced_toggle.on('update:model-value', toggle_advanced)

            # Also update capacity when basic settings change
            channel_select.on('update:model-value', update_capacity_display)
            bits_select.on('update:model-value', update_capacity_display)

            # Encryption settings
            ui.separator().classes('my-2')
            ui.label('🔐 ENCRYPTION').classes('text-green-400 text-lg font-bold')

            encrypt_toggle = ui.switch('Enable Encryption').classes('text-cyan-400')

            encrypt_container = ui.column().classes('w-full hidden gap-2')
            with encrypt_container:
                password_input = ui.input(
                    label='Password',
                    password=True,
                    password_toggle_button=True
                ).classes('w-full')

                crypto_methods = crypto.get_available_methods()
                encrypt_method = ui.select(
                    label='Method',
                    options=crypto_methods,
                    value=crypto_methods[0] if crypto_methods else 'xor'
                ).classes('w-full')

            def toggle_encrypt():
                if encrypt_toggle.value:
                    encrypt_container.classes(remove='hidden')
                else:
                    encrypt_container.classes(add='hidden')

            encrypt_toggle.on('update:model-value', toggle_encrypt)

    ui.separator().classes('my-4')

    # ENCODE BUTTON & OUTPUT
    with ui.row().classes('w-full justify-center gap-4'):
        async def do_encode():
            if state.carrier_image is None:
                ui.notify('Please upload or generate a carrier image first', type='negative')
                return

            # Get data to encode
            if data_source.value == 'text':
                if not text_input.value:
                    ui.notify('Please enter some text to hide', type='negative')
                    return
                data = text_input.value.encode('utf-8')
            else:
                if not state.encode_file_data:
                    ui.notify('Please upload a file to hide', type='negative')
                    return
                # Prepend filename for extraction
                filename_bytes = state.encode_file_name.encode('utf-8')
                data = bytes([len(filename_bytes)]) + filename_bytes + state.encode_file_data

            # Build config
            if advanced_toggle.value:
                config = create_config(
                    channels=adv_channel_select.value or 'RGB',
                    bits=adv_bits_select.value or 1,
                    strategy=strategy_select.value or 'interleaved',
                    bit_offset=bit_offset_select.value or 0,
                    seed=int(seed_input.value) if seed_input.value else None,
                    compress=compress_toggle.value,
                )
            else:
                config = create_config(
                    channels=channel_select.value or 'RGB',
                    bits=bits_select.value or 1,
                )

            # Check capacity before proceeding
            cap = calculate_capacity(state.carrier_image, config)
            # Account for header overhead (~32 bytes + compression metadata)
            estimated_size = len(data) + 64  # Conservative estimate with header
            if estimated_size > cap['usable_bytes']:
                ui.notify(
                    f'⛔ Data too large! Need {format_size(estimated_size)}, but capacity is {cap["human"]}. '
                    f'Try: more bits, more channels, or larger image.',
                    type='negative',
                    timeout=8000
                )
                return

            # Encrypt if enabled
            if encrypt_toggle.value:
                if not password_input.value:
                    ui.notify('Please enter an encryption password', type='negative')
                    return
                data = crypto.encrypt(data, password_input.value, encrypt_method.value)

            # XOR invert if enabled (advanced mode only)
            if advanced_toggle.value and invert_toggle.value:
                data = bytes(b ^ 0xFF for b in data)

            try:
                result = encode(state.carrier_image, data, config)

                # Calculate encoding stats
                data_bits = len(data) * 8
                if advanced_toggle.value:
                    ch = adv_channel_select.value or 'RGB'
                    b = adv_bits_select.value or 1
                else:
                    ch = channel_select.value or 'RGB'
                    b = bits_select.value or 1
                num_ch = len(CHANNEL_PRESETS.get(ch, []))
                bits_per_pixel = num_ch * b
                pixels_used = (data_bits // bits_per_pixel) + 1 if bits_per_pixel else 0
                total_pixels = state.carrier_image.size[0] * state.carrier_image.size[1]
                pct_used = (pixels_used / total_pixels) * 100 if total_pixels else 0

                # Show result
                b64 = image_to_base64(result)
                result_preview.set_source(f'data:image/png;base64,{b64}')
                result_container.classes(remove='hidden')

                # Update result stats
                result_stats.set_content(
                    f'<div style="color: #00ff00; font-family: monospace; font-size: 12px;">'
                    f'✓ Encoded {format_size(len(data))} into {pixels_used:,} pixels ({pct_used:.2f}% of image)<br>'
                    f'Config: {ch} @ {b} bits | Strategy: {strategy_select.value if advanced_toggle.value else "interleaved"}'
                    f'{"<br>🔐 Encrypted" if encrypt_toggle.value else ""}'
                    f'{"<br>🔀 XOR Inverted" if advanced_toggle.value and invert_toggle.value else ""}'
                    f'</div>'
                )

                # Store for download
                state.encode_result = result

                ui.notify('✓ Encoding successful!', type='positive')

            except Exception as e:
                ui.notify(f'Encoding failed: {str(e)}', type='negative')

        ui.button('🔒 ENCODE', on_click=do_encode).classes(
            'bg-green-600 hover:bg-green-500 text-black font-bold px-8 py-2 text-lg'
        )

    # Result display
    result_container = ui.column().classes('w-full hidden gap-2 mt-4')
    with result_container:
        ui.label('✓ ENCODED IMAGE').classes('text-green-400 text-lg font-bold')
        result_stats = ui.html('', sanitize=False).classes('w-full')
        result_preview = ui.image().classes('w-full max-h-96 object-contain')

        async def download_result():
            if state.encode_result is None:
                return

            # Create download
            buffer = io.BytesIO()
            state.encode_result.save(buffer, format='PNG')
            buffer.seek(0)

            ui.download(buffer.getvalue(), 'stego_output.png')

        ui.button('💾 Download Encoded Image', on_click=download_result).classes(
            'bg-cyan-600 hover:bg-cyan-500 text-black font-bold'
        )


async def create_decode_panel():
    """Create the decoding interface - Aperi'Solve inspired"""

    global state

    # Store scan results for UI updates
    scan_results_data = {"results": [], "selected": None}

    with ui.row().classes('w-full gap-4'):
        # Left column - Image upload
        with ui.column().classes('w-1/2 gap-2'):
            ui.label('🖼️ STEGO IMAGE').classes('text-cyan-400 text-lg font-bold')

            # Show current image if loaded
            if state.decode_image:
                b64 = image_to_base64(state.decode_image)
                ui.image(f'data:image/png;base64,{b64}').classes('w-full max-h-48 object-contain')
                w, h = state.decode_image.size
                ui.label(f'Loaded | {w}x{h} | {w*h:,} pixels').classes('text-green-400 text-sm')

                # Quick detection status
                if state.detected_config:
                    ui.html(
                        f'<div style="color: #00ff00; background: rgba(0,255,0,0.1); padding: 8px; border: 1px solid #00ff00; border-radius: 4px;">'
                        f'✓ STEG v3 header detected<br>'
                        f'Channels: {state.detected_config["config"]["channels"]}<br>'
                        f'Payload: {format_size(state.detected_config["original_length"])}'
                        f'</div>', sanitize=False
                    )
                else:
                    ui.html(
                        '<div style="color: #ffff00; background: rgba(255,255,0,0.1); padding: 8px; border: 1px solid #666; border-radius: 4px;">'
                        '⚠ No STEG header - use Smart Scan to detect LSB data'
                        '</div>', sanitize=False
                    )
            else:
                ui.image().classes('w-full max-h-48 object-contain')
                ui.label('No image loaded').classes('text-gray-500 text-sm')

            # Custom file picker
            decode_html, decode_js = create_file_picker('decode_image', '.png,.PNG,image/png', '/api/upload/decode', tab='decode')
            ui.html(decode_html, sanitize=False)
            ui.add_body_html(decode_js)

        # Right column - Decode options
        with ui.column().classes('w-1/2 gap-2'):
            ui.label('⚙️ DECODE OPTIONS').classes('text-cyan-400 text-lg font-bold')

            # Decryption password (optional)
            ui.label('🔓 Decryption (optional)').classes('text-sm text-gray-400')
            dec_password_input = ui.input(
                label='Password (leave empty if unencrypted)',
                password=True,
                password_toggle_button=True
            ).classes('w-full')

            ui.separator().classes('my-2')

            # Manual decode settings
            ui.label('📋 Manual Config (for targeted decode)').classes('text-sm text-gray-400')
            with ui.row().classes('w-full gap-2'):
                dec_channel_select = ui.select(
                    label='Channels',
                    options=list(CHANNEL_PRESETS.keys()),
                    value='RGB'
                ).classes('w-1/3')

                dec_bits_select = ui.select(
                    label='Bits',
                    options=list(range(1, 9)),
                    value=1
                ).classes('w-1/3')

                dec_strategy_select = ui.select(
                    label='Strategy',
                    options=['interleaved', 'sequential', 'spread', 'randomized'],
                    value='interleaved'
                ).classes('w-1/3')

    ui.separator().classes('my-4')

    # ACTION BUTTONS
    with ui.row().classes('w-full justify-center gap-4'):
        async def do_smart_scan():
            """Run Aperi'Solve-style multi-config scan"""
            if state.decode_image is None:
                ui.notify('Please upload an image first', type='negative')
                return

            ui.notify('🔍 Scanning all channel combinations...', type='info')

            try:
                password = dec_password_input.value if dec_password_input.value else None
                results = smart_scan_image(state.decode_image, password)
                scan_results_data["results"] = results

                # Build results HTML table
                html = '<div style="max-height: 400px; overflow-y: auto;">'
                html += '<table style="width: 100%; border-collapse: collapse; font-size: 12px;">'
                html += '<thead><tr style="background: #1a1a1a; color: #00ff00;">'
                html += '<th style="padding: 8px; text-align: left; border: 1px solid #333;">Config</th>'
                html += '<th style="padding: 8px; text-align: left; border: 1px solid #333;">Channels</th>'
                html += '<th style="padding: 8px; text-align: center; border: 1px solid #333;">Bits</th>'
                html += '<th style="padding: 8px; text-align: center; border: 1px solid #333;">Status</th>'
                html += '<th style="padding: 8px; text-align: center; border: 1px solid #333;">Conf</th>'
                html += '<th style="padding: 8px; text-align: left; border: 1px solid #333;">Preview</th>'
                html += '</tr></thead><tbody>'

                for i, r in enumerate(results):
                    # Status color coding
                    if r["status"] == "STEG_DETECTED" or r["status"] == "STEG_HEADER":
                        status_color = "#00ff00"
                        status_icon = "✓"
                        row_bg = "rgba(0, 255, 0, 0.15)"
                    elif r["status"] == "TEXT_FOUND":
                        status_color = "#00ffff"
                        status_icon = "📝"
                        row_bg = "rgba(0, 255, 255, 0.15)"
                    elif r["status"] == "POSSIBLE_TEXT":
                        status_color = "#ffff00"
                        status_icon = "?"
                        row_bg = "rgba(255, 255, 0, 0.1)"
                    elif r["status"] == "MIXED_DATA":
                        status_color = "#ff9900"
                        status_icon = "~"
                        row_bg = "transparent"
                    else:
                        status_color = "#666666"
                        status_icon = "·"
                        row_bg = "transparent"

                    # Confidence bar
                    conf = r.get("confidence", 0)
                    conf_bar = f'<div style="width: 50px; height: 8px; background: #333; border-radius: 2px;"><div style="width: {conf}%; height: 100%; background: {status_color}; border-radius: 2px;"></div></div>'

                    # Preview (escape HTML)
                    preview = r.get("preview", "")[:60]
                    preview_escaped = preview.replace("<", "&lt;").replace(">", "&gt;").replace("&", "&amp;")
                    if len(r.get("preview", "")) > 60:
                        preview_escaped += "..."

                    channels_str = ",".join(r["channels"]) if isinstance(r["channels"], list) else str(r["channels"])

                    html += f'<tr style="background: {row_bg}; border-bottom: 1px solid #333;">'
                    html += f'<td style="padding: 6px; color: #00ff00; border: 1px solid #333;"><b>{r["name"]}</b></td>'
                    html += f'<td style="padding: 6px; color: #888; border: 1px solid #333;">{channels_str}</td>'
                    html += f'<td style="padding: 6px; color: #888; text-align: center; border: 1px solid #333;">{r["bits"]}</td>'
                    html += f'<td style="padding: 6px; color: {status_color}; text-align: center; border: 1px solid #333;">{status_icon} {r["status"]}</td>'
                    html += f'<td style="padding: 6px; text-align: center; border: 1px solid #333;">{conf_bar}</td>'
                    html += f'<td style="padding: 6px; color: #aaa; font-family: monospace; font-size: 11px; border: 1px solid #333; max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{preview_escaped}</td>'
                    html += '</tr>'

                html += '</tbody></table></div>'

                # Summary
                text_found = sum(1 for r in results if r["status"] in ["TEXT_FOUND", "STEG_DETECTED", "STEG_HEADER"])
                possible = sum(1 for r in results if r["status"] == "POSSIBLE_TEXT")

                summary = f'<div style="margin-top: 12px; padding: 8px; background: #111; border: 1px solid #333;">'
                summary += f'<span style="color: #00ff00;">📊 Scanned {len(results)} configurations</span> | '
                summary += f'<span style="color: #00ffff;">Found: {text_found} likely</span> | '
                summary += f'<span style="color: #ffff00;">Possible: {possible}</span>'
                summary += '</div>'

                scan_results_container.set_content(html + summary)
                scan_results_container.classes(remove='hidden')

                if text_found > 0:
                    ui.notify(f'✓ Found {text_found} potential hidden data!', type='positive')
                else:
                    ui.notify('Scan complete - no obvious text found', type='warning')

            except Exception as e:
                ui.notify(f'Scan failed: {str(e)}', type='negative')

        async def do_decode():
            """Standard decode with current settings"""
            if state.decode_image is None:
                ui.notify('Please upload an image first', type='negative')
                return

            config = create_config(
                channels=dec_channel_select.value or 'RGB',
                bits=dec_bits_select.value or 1,
                strategy=dec_strategy_select.value or 'interleaved',
            )

            try:
                data = decode(state.decode_image, config)

                # Decrypt if needed
                if dec_password_input.value:
                    try:
                        data = crypto.decrypt(data, dec_password_input.value)
                    except Exception as e:
                        ui.notify(f'Decryption failed: {e}', type='warning')

                # Process extracted data
                process_extracted_data(data, output_text, file_download_btn)
                ui.notify('✓ Decode successful!', type='positive')

            except Exception as e:
                ui.notify(f'Decode failed: {str(e)}', type='negative')
                output_text.set_value(f"Error: {str(e)}\n\nTry using Smart Scan to detect the correct configuration.")

        async def do_auto_decode():
            """Auto-decode using detected STEG header"""
            if state.decode_image is None:
                ui.notify('Please upload an image first', type='negative')
                return

            try:
                # Use auto-detection (config=None)
                data = decode(state.decode_image, None)

                # Decrypt if needed
                if dec_password_input.value:
                    try:
                        data = crypto.decrypt(data, dec_password_input.value)
                    except Exception as e:
                        ui.notify(f'Decryption failed: {e}', type='warning')

                # Process extracted data
                process_extracted_data(data, output_text, file_download_btn)
                ui.notify('✓ Auto-decode successful!', type='positive')

            except Exception as e:
                ui.notify(f'Auto-decode failed: {str(e)}. Try Smart Scan.', type='negative')
                output_text.set_value(f"Auto-decode failed: {str(e)}\n\nThe image may not contain STEG v3 header.\nTry using Smart Scan to detect raw LSB data.")

        ui.button('🔍 SMART SCAN', on_click=do_smart_scan).classes(
            'bg-purple-600 hover:bg-purple-500 text-white font-bold px-6 py-2'
        ).props('unelevated')

        ui.button('🤖 AUTO DECODE', on_click=do_auto_decode).classes(
            'bg-cyan-600 hover:bg-cyan-500 text-black font-bold px-6 py-2'
        )

        ui.button('📋 MANUAL DECODE', on_click=do_decode).classes(
            'bg-gray-600 hover:bg-gray-500 text-white font-bold px-6 py-2'
        )

    # 🪆 MATRYOSHKA MODE BUTTON (only shows when matryoshka mode is active)
    matryoshka_btn_container = ui.row().classes('w-full justify-center gap-4 mt-2')

    with matryoshka_btn_container:
        async def do_matryoshka_decode():
            """🪆 Perform recursive Matryoshka decode"""
            if state.decode_image is None:
                ui.notify('Please upload an image first', type='negative')
                return

            if not state.matryoshka_mode:
                ui.notify('🪆 Matryoshka mode not active! Click the bottom-left corner to activate.', type='warning')
                return

            ui.notify(f'🪆 Starting Matryoshka decode (depth: {state.matryoshka_depth})...', type='info')

            try:
                password = dec_password_input.value if dec_password_input.value else None
                results = matryoshka_decode(state.decode_image, max_depth=state.matryoshka_depth, password=password)
                state.matryoshka_results = results

                # Build nested results display
                def build_results_html(res_list, indent=0):
                    html = ''
                    for r in res_list:
                        depth = r.get('depth', indent)
                        indent_px = depth * 24
                        doll_icon = '🪆' * (depth + 1)  # More dolls for deeper layers

                        # Color based on type
                        if r.get('type') == 'nested_image' or r.get('type') == 'nested_image_raw':
                            color = '#ff00ff'
                            icon = '🖼️'
                        elif r.get('type') == 'text':
                            color = '#00ff00'
                            icon = '📝'
                        elif r.get('type') == 'file':
                            color = '#00ffff'
                            icon = '📁'
                        elif r.get('type') == 'no_data_found':
                            color = '#666666'
                            icon = '∅'
                        elif r.get('type') == 'max_depth_reached':
                            color = '#ffff00'
                            icon = '⚠️'
                        else:
                            color = '#888888'
                            icon = '?'

                        html += f'''
                        <div style="margin-left: {indent_px}px; padding: 8px; margin-bottom: 4px;
                                    background: rgba(255,0,255,{0.1 - depth*0.02}); border-left: 3px solid {color};
                                    border-radius: 4px;">
                            <div style="color: {color}; font-weight: bold;">
                                {doll_icon} Layer {depth} {icon}
                                <span style="color: #888; font-weight: normal;">
                                    {r.get('filename') or r.get('type', 'unknown')}
                                </span>
                            </div>
                            <div style="color: #aaa; font-size: 11px; margin-top: 4px;">
                                Size: {format_size(r.get('data_size', 0))}
                            </div>
                            <div style="color: #ccc; font-family: monospace; font-size: 11px; margin-top: 4px;
                                        max-height: 60px; overflow-y: auto; white-space: pre-wrap;">
                                {r.get('preview', '')[:200]}
                            </div>
                        </div>
                        '''

                        # Recurse into nested results
                        if r.get('nested_results'):
                            html += build_results_html(r['nested_results'], indent + 1)

                    return html

                results_html = build_results_html(results)

                # Count layers found
                def count_layers(res_list):
                    count = len(res_list)
                    for r in res_list:
                        if r.get('nested_results'):
                            count += count_layers(r['nested_results'])
                    return count

                total_layers = count_layers(results)

                matryoshka_results_container.set_content(
                    f'''
                    <div class="matryoshka-tree">
                        <div style="color: #ff00ff; font-size: 14px; font-weight: bold; margin-bottom: 12px;">
                            🪆 MATRYOSHKA DECODE RESULTS
                            <span style="color: #888; font-weight: normal;">({total_layers} layers found)</span>
                        </div>
                        {results_html}
                    </div>
                    '''
                )
                matryoshka_results_container.classes(remove='hidden')

                # Also extract the deepest/last data for download
                def get_deepest_data(res_list):
                    for r in reversed(res_list):
                        if r.get('nested_results'):
                            deep = get_deepest_data(r['nested_results'])
                            if deep:
                                return deep
                        if r.get('raw_data'):
                            return r
                    return None

                deepest = get_deepest_data(results)
                if deepest and deepest.get('raw_data'):
                    state.extracted_file = deepest['raw_data']
                    state.extracted_filename = deepest.get('filename', 'extracted_data.bin')
                    file_download_btn.classes(remove='hidden')

                    # Also show in output text
                    try:
                        text = deepest['raw_data'].decode('utf-8')
                        output_text.set_value(f"🪆 Deepest layer content:\n\n{text}")
                    except:
                        output_text.set_value(f"🪆 Deepest layer: {deepest.get('filename', 'binary data')} ({format_size(len(deepest['raw_data']))})")

                ui.notify(f'🪆 Matryoshka decode complete! Found {total_layers} layers.', type='positive')

            except Exception as e:
                ui.notify(f'🪆 Matryoshka decode failed: {str(e)}', type='negative')
                matryoshka_results_container.set_content(
                    f'<div style="color: #ff3333; padding: 12px;">Error: {str(e)}</div>'
                )

        matryoshka_decode_btn = ui.button('🪆 MATRYOSHKA DECODE', on_click=do_matryoshka_decode).classes(
            'bg-pink-600 hover:bg-pink-500 text-white font-bold px-6 py-2'
        ).props('unelevated').style('display: none;')

        # Show/hide based on matryoshka mode state
        ui.add_body_html('''
        <script>
            // Check matryoshka state and show/hide button
            function updateMatryoshkaButton() {
                const btn = document.querySelector('[class*="bg-pink-600"]');
                const panel = document.getElementById('matryoshka-panel');
                if (btn && panel) {
                    if (!panel.classList.contains('hidden')) {
                        btn.style.display = 'inline-flex';
                    } else {
                        btn.style.display = 'none';
                    }
                }
            }

            // Check periodically
            setInterval(updateMatryoshkaButton, 500);
        </script>
        ''')

    # 🪆 MATRYOSHKA RESULTS CONTAINER
    matryoshka_results_container = ui.html('', sanitize=False).classes('w-full hidden mt-4')

    # SCAN RESULTS (hidden until scan runs)
    ui.label('📊 SCAN RESULTS').classes('text-purple-400 text-lg font-bold mt-4')
    scan_results_container = ui.html(
        '<div style="color: #666; padding: 20px; text-align: center;">'
        'Click "Smart Scan" to analyze all channel combinations'
        '</div>', sanitize=False
    ).classes('w-full')

    ui.separator().classes('my-4')

    # OUTPUT SECTION
    ui.label('📤 EXTRACTED DATA').classes('text-cyan-400 text-lg font-bold')
    output_text = ui.textarea(
        label='Decoded output',
        placeholder='Extracted data will appear here...'
    ).classes('w-full terminal').props('rows=8 readonly dark')

    with ui.row().classes('gap-2'):
        async def download_file():
            if state.extracted_file is None:
                return
            ui.download(state.extracted_file, state.extracted_filename)

        file_download_btn = ui.button('💾 Download Extracted File', on_click=download_file).classes(
            'bg-green-600 hover:bg-green-500 text-black font-bold hidden'
        )

        async def download_raw():
            if not output_text.value:
                return
            ui.download(output_text.value.encode('utf-8'), 'extracted_text.txt')

        ui.button('📄 Download as Text', on_click=download_raw).classes(
            'bg-gray-600 hover:bg-gray-500 text-white font-bold'
        )


def process_extracted_data(data: bytes, output_text, file_download_btn):
    """Process and display extracted data"""
    try:
        # Check if it's a file (starts with filename length byte)
        if len(data) > 2 and data[0] < 255:
            fname_len = data[0]
            if fname_len > 0 and fname_len < 200:
                try:
                    filename = data[1:1+fname_len].decode('utf-8')
                    file_data = data[1+fname_len:]
                    # Check if it looks like a valid filename
                    if '.' in filename and len(filename) < 200 and '/' not in filename:
                        state.extracted_file = file_data
                        state.extracted_filename = filename
                        output_text.set_value(
                            f"📁 Extracted file: {filename}\n"
                            f"   Size: {format_size(len(file_data))}\n\n"
                            f"(Click 'Download Extracted File' to save)"
                        )
                        file_download_btn.classes(remove='hidden')
                        return
                except:
                    pass

        # Try as plain text
        text = data.decode('utf-8')
        output_text.set_value(text)
        file_download_btn.classes(add='hidden')

    except UnicodeDecodeError:
        # Binary data - show hex preview
        hex_preview = data[:512].hex()
        formatted = ' '.join(hex_preview[i:i+2] for i in range(0, min(len(hex_preview), 512), 2))
        output_text.set_value(
            f"Binary data ({format_size(len(data))}):\n\n{formatted}"
            + ("..." if len(data) > 256 else "")
        )
        state.extracted_file = data
        state.extracted_filename = 'extracted_data.bin'
        file_download_btn.classes(remove='hidden')


async def create_matryoshka_panel():
    """Create the Matryoshka (nested steganography) interface"""

    global state

    ui.html('''
        <div style="text-align: center; margin-bottom: 20px;">
            <div style="color: #ff00ff; font-size: 24px; font-weight: bold;">🪆 MATRYOSHKA MODE 🪆</div>
            <div style="color: #ff99ff; font-size: 12px;">Russian Nesting Doll Steganography</div>
        </div>
    ''', sanitize=False)

    with ui.row().classes('w-full gap-6'):
        # ==================== ENCODE SECTION ====================
        with ui.column().classes('w-1/2 gap-3'):
            ui.label('🔐 NESTED ENCODE').classes('text-pink-400 text-lg font-bold')

            ui.html('<div style="color: #999; font-size: 11px; margin-bottom: 8px;">Add carrier images (outermost first). Each layer wraps the previous.</div>', sanitize=False)

            # Carrier list with capacity info
            carrier_container = ui.column().classes('w-full gap-1 p-3').style(
                'background: rgba(255,0,255,0.05); border: 1px solid rgba(255,0,255,0.3); border-radius: 8px; min-height: 120px;'
            )

            def refresh_carriers():
                carrier_container.clear()
                with carrier_container:
                    if not state.matryoshka_carriers:
                        ui.html('<div style="color: #666; text-align: center; padding: 20px;">No carriers added yet</div>', sanitize=False)
                    else:
                        config = create_config(channels='RGBA', bits=2)
                        for i, (img, name) in enumerate(state.matryoshka_carriers):
                            cap = _calculate_capacity_bytes(img, config)
                            layer_num = len(state.matryoshka_carriers) - i
                            with ui.row().classes('w-full items-center gap-2 p-2').style(
                                'background: rgba(255,0,255,0.1); border-radius: 4px; margin-bottom: 4px;'
                            ):
                                ui.html(f'<span style="color: #ff00ff; font-weight: bold;">L{layer_num}</span>', sanitize=False)
                                ui.label(f'{name[:25]}').classes('text-pink-300 text-sm flex-grow')
                                ui.label(f'{img.size[0]}x{img.size[1]}').classes('text-gray-500 text-xs')
                                ui.label(f'{cap//1024}KB').classes('text-pink-400 text-xs')

            refresh_carriers()

            # Carrier upload
            carrier_upload_html, carrier_upload_js = create_drop_zone(
                'matryoshka_carrier', 'image/png,image/jpeg,image/webp',
                '/api/matryoshka/add_carrier', 'matryoshka'
            )
            ui.html(carrier_upload_html, sanitize=False)
            ui.add_body_html(carrier_upload_js)

            with ui.row().classes('w-full gap-2'):
                def clear_carriers():
                    state.matryoshka_carriers = []
                    refresh_carriers()
                    ui.notify('🪆 Carriers cleared', type='info')

                ui.button('🗑️ Clear Carriers', on_click=clear_carriers).props('flat dense').classes('text-pink-400')

            ui.separator().classes('my-2')

            # Payload info
            ui.html('<div style="color: #ff99ff; font-size: 12px; font-weight: bold;">PAYLOAD</div>', sanitize=False)
            with ui.row().classes('w-full items-center gap-2 p-2').style('background: rgba(0,0,0,0.3); border-radius: 4px;'):
                if state.encode_file_data:
                    ui.icon('description').classes('text-pink-400')
                    ui.label(f'{state.encode_file_name or "file"} ({len(state.encode_file_data)} bytes)').classes('text-pink-300 text-sm')
                else:
                    ui.icon('text_fields').classes('text-gray-500')
                    ui.label('Set payload in ENCODE tab first').classes('text-gray-500 text-sm')

            # Encode button
            async def do_encode():
                if not state.matryoshka_carriers:
                    ui.notify('Add carrier images first!', type='warning')
                    return
                if not state.encode_file_data and not (hasattr(state, 'encode_text') and state.encode_text):
                    ui.notify('Set payload in ENCODE tab first', type='warning')
                    return

                ui.notify('🪆 Encoding nested layers...', type='info')
                ui.run_javascript('''
                    fetch('/api/matryoshka/encode', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({channels: 'RGBA', bits: 2})
                    })
                    .then(r => r.json())
                    .then(data => {
                        if (data.success) {
                            window.location.href = '/api/matryoshka/download';
                        } else {
                            alert('Error: ' + data.error);
                        }
                    });
                ''')

            ui.button('🪆 ENCODE MATRYOSHKA', on_click=do_encode).props('unelevated').classes(
                'w-full mt-4 bg-pink-900 text-pink-200'
            ).style('font-size: 14px; font-weight: bold;')

        # ==================== DECODE SECTION ====================
        with ui.column().classes('w-1/2 gap-3'):
            ui.label('🔓 NESTED DECODE').classes('text-pink-400 text-lg font-bold')

            ui.html('<div style="color: #999; font-size: 11px; margin-bottom: 8px;">Upload an image and recursively extract all nested layers.</div>', sanitize=False)

            # Depth control
            with ui.row().classes('w-full items-center gap-3'):
                ui.label('Max Depth:').classes('text-pink-400')
                depth_slider = ui.slider(min=1, max=11, value=state.matryoshka_depth, step=1).classes('flex-grow').props('color="pink"')
                depth_label = ui.label(f'{state.matryoshka_depth}').classes('text-pink-300 font-bold text-lg')

                def update_depth(e):
                    state.matryoshka_depth = int(depth_slider.value)
                    depth_label.set_text(str(state.matryoshka_depth))

                depth_slider.on('update:model-value', update_depth)

            # Image upload for decode
            decode_upload_html, decode_upload_js = create_drop_zone(
                'matryoshka_decode', 'image/png',
                '/api/upload/decode', 'matryoshka'
            )
            ui.html(decode_upload_html, sanitize=False)
            ui.add_body_html(decode_upload_js)

            # Current decode image preview
            if state.decode_image:
                b64 = image_to_base64(state.decode_image)
                ui.image(f'data:image/png;base64,{b64}').classes('w-full max-h-48 object-contain mt-2')

            # Decode button
            async def do_decode():
                if not state.decode_image:
                    ui.notify('Upload an image first', type='warning')
                    return

                ui.notify('🪆 Decoding nested layers...', type='info')
                ui.run_javascript(f'''
                    fetch('/api/matryoshka/decode', {{
                        method: 'POST',
                        headers: {{'Content-Type': 'application/json'}},
                        body: JSON.stringify({{depth: {state.matryoshka_depth}}})
                    }})
                    .then(r => r.json())
                    .then(data => {{
                        if (data.success) {{
                            alert('🪆 Found ' + data.layers_found + ' nested layers!');
                            window.location.reload();
                        }} else {{
                            alert('Error: ' + data.error);
                        }}
                    }});
                ''')

            ui.button('🪆 DECODE MATRYOSHKA', on_click=do_decode).props('unelevated').classes(
                'w-full mt-4 bg-pink-900 text-pink-200'
            ).style('font-size: 14px; font-weight: bold;')

            # Results display
            if state.matryoshka_results:
                ui.separator().classes('my-3')
                ui.label('📦 EXTRACTED LAYERS').classes('text-pink-400 font-bold')

                for result in state.matryoshka_results:
                    with ui.card().classes('w-full p-2 mt-2').style('background: rgba(255,0,255,0.1); border: 1px solid rgba(255,0,255,0.3);'):
                        depth = result.get('depth', 0)
                        rtype = result.get('type', 'unknown')
                        preview = result.get('preview', '')[:200]

                        ui.html(f'''
                            <div style="color: #ff00ff; font-weight: bold;">Layer {depth}: {rtype}</div>
                            <div style="color: #ccc; font-size: 11px; margin-top: 4px; word-break: break-all;">{preview}</div>
                        ''', sanitize=False)


async def create_analyze_panel():
    """Create the analysis interface"""

    global state

    with ui.row().classes('w-full gap-4'):
        # Left column - Image upload
        with ui.column().classes('w-1/2 gap-2'):
            ui.label('🔍 IMAGE TO ANALYZE').classes('text-yellow-400 text-lg font-bold')

            # Show current image if loaded
            if state.analyze_image:
                b64 = image_to_base64(state.analyze_image)
                ui.image(f'data:image/png;base64,{b64}').classes('w-full max-h-64 object-contain')
                w, h = state.analyze_image.size
                ui.label(f'Loaded | {w}x{h}').classes('text-green-400 text-sm')
            else:
                ui.image().classes('w-full max-h-64 object-contain')
                ui.label('No image loaded').classes('text-gray-500 text-sm')

            # Custom file picker - uses API endpoint
            analyze_html, analyze_js = create_file_picker('analyze_image', '.png,.PNG,image/png', '/api/upload/analyze', tab='analyze')
            ui.html(analyze_html, sanitize=False)
            ui.add_body_html(analyze_js)

        # Right column - Results
        with ui.column().classes('w-1/2 gap-2'):
            ui.label('📊 ANALYSIS RESULTS').classes('text-yellow-400 text-lg font-bold')

            analysis_output = ui.html('', sanitize=False).classes('w-full terminal p-4')

    ui.separator().classes('my-4')

    with ui.row().classes('w-full justify-center'):
        async def do_analyze():
            if state.analyze_image is None:
                ui.notify('Please upload an image first', type='negative')
                return

            try:
                analysis = analyze_image(state.analyze_image)
                detection = detect_encoding(state.analyze_image)

                # Format output
                html = '<pre style="color: #00ff00;">'
                html += '╔══════════════════════════════════════╗\n'
                html += '║       STEGANALYSIS REPORT            ║\n'
                html += '╠══════════════════════════════════════╣\n'

                html += f'║ Dimensions: {analysis["dimensions"]["width"]}x{analysis["dimensions"]["height"]}\n'
                html += f'║ Total Pixels: {analysis["total_pixels"]:,}\n'
                html += f'║ Format: {analysis["format"] or "PNG"}\n'
                html += '╠══════════════════════════════════════╣\n'

                # Detection result
                if detection:
                    html += '<span style="color: #00ff00;">║ ✓ STEG HEADER DETECTED</span>\n'
                    html += f'║   Channels: {detection["config"]["channels"]}\n'
                    html += f'║   Bits: {detection["config"]["bits_per_channel"]}\n'
                    html += f'║   Strategy: {detection["config"]["strategy"]}\n'
                    html += f'║   Payload: {format_size(detection["original_length"])}\n'
                else:
                    html += '<span style="color: #666;">║ No STEG header detected</span>\n'

                html += '╠══════════════════════════════════════╣\n'

                # Statistical analysis
                det = analysis['detection']
                if det['level'] == 'HIGH':
                    color = '#ff4444'
                elif det['level'] == 'MEDIUM':
                    color = '#ffff00'
                else:
                    color = '#00ff00'

                html += f'<span style="color: {color};">║ Detection Level: {det["level"]}</span>\n'
                html += f'║ Confidence: {det["confidence"]*100:.1f}%\n'
                html += f'║ {det["recommendation"]}\n'

                html += '╠══════════════════════════════════════╣\n'
                html += '║ CAPACITY BY CONFIG:\n'
                for cfg, cap in analysis['capacity_by_config'].items():
                    html += f'║   {cfg}: {cap}\n'

                html += '╠══════════════════════════════════════╣\n'
                html += '║ CHANNEL ANALYSIS:\n'
                for ch_name, ch_data in analysis['channels'].items():
                    chi = ch_data['chi_square_indicator']
                    chi_color = '#ff4444' if chi > 0.5 else '#ffff00' if chi > 0.2 else '#00ff00'
                    html += f'║ {ch_name}: μ={ch_data["mean"]:.1f} σ={ch_data["std"]:.1f} '
                    html += f'<span style="color: {chi_color};">χ²={chi:.3f}</span>\n'

                html += '╚══════════════════════════════════════╝'
                html += '</pre>'

                analysis_output.set_content(html)
                ui.notify('Analysis complete!', type='positive')

            except Exception as e:
                ui.notify(f'Analysis failed: {str(e)}', type='negative')

        ui.button('🔬 ANALYZE', on_click=do_analyze).classes(
            'bg-yellow-600 hover:bg-yellow-500 text-black font-bold px-8 py-2 text-lg'
        )


# ============== MAIN ==============

def main():
    """Run the web UI"""
    print(STEGO_ASCII)
    print("\n🦕 Starting STEGOSAURUS WRECKS Web UI...")
    print("   Open http://localhost:8080 in your browser\n")

    ui.run(
        title='STEGOSAURUS WRECKS',
        favicon='🦕',
        dark=True,
        port=8080,
        reload=False,
    )


if __name__ in {"__main__", "__mp_main__"}:
    main()
