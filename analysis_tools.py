"""
STEGOSAURUS WRECKS - Comprehensive Analysis Tools
Complete toolkit for steganography detection across all file types

This module provides 264+ analysis functions covering:
- Images: PNG, JPEG, GIF, BMP, WebP, TIFF, ICO, HEIC, AVIF, SVG
- Audio: WAV, MP3, FLAC, OGG
- Video: AVI, MKV
- Documents: PDF, Office
- Archives: ZIP, RAR
- Fonts: TTF, OTF, WOFF
"""

import struct
import zlib
import io
import re
import json
import hashlib
import binascii
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Union, BinaryIO
from dataclasses import dataclass, field
from enum import Enum
import math

# Optional imports - gracefully handle missing dependencies
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

try:
    from PIL import Image, ExifTags
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


# ============== CORE INFRASTRUCTURE ==============

@dataclass
class AnalysisResult:
    """Standard result format for all analysis functions"""
    success: bool
    action: str
    file_type: str
    data: Dict[str, Any] = field(default_factory=dict)
    findings: List[str] = field(default_factory=list)
    suspicious: bool = False
    confidence: float = 0.0
    raw_data: Optional[bytes] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "action": self.action,
            "file_type": self.file_type,
            "data": self.data,
            "findings": self.findings,
            "suspicious": self.suspicious,
            "confidence": self.confidence,
            "has_raw_data": self.raw_data is not None,
            "error": self.error
        }


class FileType(Enum):
    PNG = "png"
    JPEG = "jpeg"
    GIF = "gif"
    BMP = "bmp"
    WEBP = "webp"
    TIFF = "tiff"
    ICO = "ico"
    HEIC = "heic"
    AVIF = "avif"
    SVG = "svg"
    WAV = "wav"
    MP3 = "mp3"
    FLAC = "flac"
    OGG = "ogg"
    AVI = "avi"
    MKV = "mkv"
    PDF = "pdf"
    OFFICE = "office"
    ZIP = "zip"
    RAR = "rar"
    FONT = "font"
    AIFF = "aiff"
    AU = "au"
    MIDI = "midi"
    PCAP = "pcap"
    SQLITE = "sqlite"
    GZIP = "gzip"
    TAR = "tar"
    UNKNOWN = "unknown"


# Magic bytes for file type detection
MAGIC_SIGNATURES = {
    b'\x89PNG\r\n\x1a\n': FileType.PNG,
    b'\xff\xd8\xff': FileType.JPEG,
    b'GIF87a': FileType.GIF,
    b'GIF89a': FileType.GIF,
    b'BM': FileType.BMP,
    b'RIFF': FileType.WAV,  # Could also be AVI - check further
    b'\xff\xfb': FileType.MP3,
    b'\xff\xfa': FileType.MP3,
    b'\xff\xf3': FileType.MP3,
    b'\xff\xf2': FileType.MP3,
    b'ID3': FileType.MP3,
    b'fLaC': FileType.FLAC,
    b'OggS': FileType.OGG,
    b'%PDF': FileType.PDF,
    b'PK\x03\x04': FileType.ZIP,  # Could be Office - check further
    b'Rar!\x1a\x07': FileType.RAR,
    b'\x1aE\xdf\xa3': FileType.MKV,
    b'\x00\x00\x01\x00': FileType.ICO,
    b'\x00\x00\x02\x00': FileType.ICO,  # CUR format
    b'\x1f\x8b': FileType.GZIP,
    b'MThd': FileType.MIDI,
    b'.snd': FileType.AU,
    b'\xa1\xb2\xc3\xd4': FileType.PCAP,
    b'\xd4\xc3\xb2\xa1': FileType.PCAP,  # Little-endian PCAP
    b'SQLite format 3': FileType.SQLITE,
}

WEBP_SIGNATURES = [b'WEBP']
HEIC_SIGNATURES = [b'ftyp', b'heic', b'heix', b'hevc', b'mif1']
AVIF_SIGNATURES = [b'ftypavif', b'ftypavis']


def detect_file_type(data: bytes) -> FileType:
    """Detect file type from magic bytes"""
    if len(data) < 12:
        return FileType.UNKNOWN

    # Check standard signatures
    for magic, ftype in MAGIC_SIGNATURES.items():
        if data.startswith(magic):
            # Special handling for RIFF container
            if magic == b'RIFF' and len(data) >= 12:
                if data[8:12] == b'WAVE':
                    return FileType.WAV
                elif data[8:12] == b'AVI ':
                    return FileType.AVI
                elif data[8:12] == b'WEBP':
                    return FileType.WEBP
            # Special handling for ZIP-based formats
            elif magic == b'PK\x03\x04':
                # Check if it's an Office document
                if b'[Content_Types].xml' in data[:2000] or b'word/' in data[:2000] or b'xl/' in data[:2000] or b'ppt/' in data[:2000]:
                    return FileType.OFFICE
                return FileType.ZIP
            return ftype

    # Check for HEIC/AVIF (ftyp box)
    if len(data) >= 12 and data[4:8] == b'ftyp':
        brand = data[8:12]
        if brand in [b'heic', b'heix', b'hevc', b'mif1']:
            return FileType.HEIC
        elif brand in [b'avif', b'avis']:
            return FileType.AVIF

    # Check for TIFF (II = little-endian, MM = big-endian)
    if data[:4] in [b'II\x2a\x00', b'MM\x00\x2a']:
        return FileType.TIFF

    # Check for AIFF (FORM container with AIFF type)
    if data[:4] == b'FORM' and len(data) >= 12:
        if data[8:12] == b'AIFF' or data[8:12] == b'AIFC':
            return FileType.AIFF

    # Check for TAR (magic at offset 257)
    if len(data) >= 265 and data[257:262] == b'ustar':
        return FileType.TAR

    # Check for SVG
    if b'<svg' in data[:1000] or b'<?xml' in data[:100] and b'<svg' in data[:2000]:
        return FileType.SVG

    # Check for fonts
    if data[:4] in [b'\x00\x01\x00\x00', b'OTTO', b'true', b'typ1']:
        return FileType.FONT
    if data[:4] == b'wOFF' or data[:4] == b'wOF2':
        return FileType.FONT

    return FileType.UNKNOWN


def calculate_entropy(data: bytes) -> float:
    """Calculate Shannon entropy of data"""
    if not data:
        return 0.0

    byte_counts = [0] * 256
    for byte in data:
        byte_counts[byte] += 1

    length = len(data)
    entropy = 0.0
    for count in byte_counts:
        if count > 0:
            p = count / length
            entropy -= p * math.log2(p)

    return entropy


def calculate_chi_square(data: bytes) -> float:
    """Calculate chi-square statistic for randomness test"""
    if not data:
        return 0.0

    byte_counts = [0] * 256
    for byte in data:
        byte_counts[byte] += 1

    expected = len(data) / 256
    chi_square = sum((count - expected) ** 2 / expected for count in byte_counts)
    return chi_square


def find_strings(data: bytes, min_length: int = 4) -> List[Tuple[int, str]]:
    """Extract printable ASCII strings from binary data"""
    strings = []
    current = []
    start_offset = 0

    for i, byte in enumerate(data):
        if 32 <= byte < 127:
            if not current:
                start_offset = i
            current.append(chr(byte))
        else:
            if len(current) >= min_length:
                strings.append((start_offset, ''.join(current)))
            current = []

    if len(current) >= min_length:
        strings.append((start_offset, ''.join(current)))

    return strings


def hex_dump(data: bytes, offset: int = 0, length: int = 256) -> str:
    """Create hex dump of data"""
    result = []
    chunk = data[offset:offset + length]

    for i in range(0, len(chunk), 16):
        line_data = chunk[i:i + 16]
        hex_part = ' '.join(f'{b:02x}' for b in line_data)
        ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in line_data)
        result.append(f'{offset + i:08x}  {hex_part:<48}  {ascii_part}')

    return '\n'.join(result)


# ============== BIT PLANE ANALYSIS ==============

def extract_bit_plane(data: bytes, bit: int) -> bytes:
    """Extract specific bit plane from data"""
    if not HAS_NUMPY:
        # Fallback without numpy
        result = bytearray()
        for i in range(0, len(data), 8):
            byte_val = 0
            for j in range(8):
                if i + j < len(data):
                    byte_val |= ((data[i + j] >> bit) & 1) << (7 - j)
            result.append(byte_val)
        return bytes(result)

    arr = np.frombuffer(data, dtype=np.uint8)
    plane = (arr >> bit) & 1
    # Pack bits into bytes
    padded = np.pad(plane, (0, (8 - len(plane) % 8) % 8), mode='constant')
    packed = np.packbits(padded)
    return packed.tobytes()


def analyze_bit_planes(data: bytes) -> Dict[str, Any]:
    """Analyze all 8 bit planes"""
    results = {}
    for bit in range(8):
        plane_data = extract_bit_plane(data, bit)
        results[f'plane_{bit}'] = {
            'entropy': calculate_entropy(plane_data),
            'unique_bytes': len(set(plane_data)),
            'sample': plane_data[:64].hex()
        }
    return results


# ============== LSB EXTRACTION ==============

def extract_lsb(data: bytes, bits: int = 1, channels: str = "RGB") -> bytes:
    """Extract LSB data from raw pixel bytes"""
    if not data:
        return b''

    extracted_bits = []
    mask = (1 << bits) - 1

    for byte in data:
        for bit_pos in range(bits):
            extracted_bits.append((byte >> bit_pos) & 1)

    # Pack bits into bytes
    result = bytearray()
    for i in range(0, len(extracted_bits), 8):
        byte_val = 0
        for j in range(8):
            if i + j < len(extracted_bits):
                byte_val |= extracted_bits[i + j] << j
        result.append(byte_val)

    return bytes(result)


# ============== PATTERN DETECTION ==============

def detect_repeated_patterns(data: bytes, min_length: int = 4, max_length: int = 32) -> List[Dict[str, Any]]:
    """Detect repeated byte patterns"""
    patterns = []

    for length in range(min_length, min(max_length, len(data) // 2) + 1):
        seen = {}
        for i in range(len(data) - length + 1):
            pattern = data[i:i + length]
            if pattern in seen:
                seen[pattern].append(i)
            else:
                seen[pattern] = [i]

        for pattern, offsets in seen.items():
            if len(offsets) >= 3:  # At least 3 occurrences
                patterns.append({
                    'pattern': pattern.hex(),
                    'length': length,
                    'count': len(offsets),
                    'offsets': offsets[:10]  # First 10 offsets
                })

    return sorted(patterns, key=lambda x: x['count'], reverse=True)[:20]


def detect_xor_patterns(data: bytes) -> Dict[str, Any]:
    """Detect potential XOR encryption patterns"""
    results = {
        'single_byte_keys': [],
        'repeating_key_likely': False,
        'key_length_candidates': []
    }

    # Try single-byte XOR keys
    for key in range(256):
        decoded = bytes(b ^ key for b in data[:256])
        # Check if result looks like text
        printable = sum(1 for b in decoded if 32 <= b < 127 or b in [9, 10, 13])
        if printable > len(decoded) * 0.7:
            results['single_byte_keys'].append({
                'key': key,
                'key_hex': f'{key:02x}',
                'printable_ratio': printable / len(decoded),
                'sample': decoded[:50].decode('ascii', errors='replace')
            })

    # Detect repeating key by looking at byte frequency at intervals
    for key_len in range(2, 17):
        columns = [[] for _ in range(key_len)]
        for i, b in enumerate(data[:1024]):
            columns[i % key_len].append(b)

        # Check if each column has low entropy (single-byte XOR characteristic)
        avg_entropy = sum(calculate_entropy(bytes(col)) for col in columns) / key_len
        if avg_entropy < 5.0:  # Lower than random
            results['key_length_candidates'].append({
                'length': key_len,
                'avg_column_entropy': avg_entropy
            })

    if results['key_length_candidates']:
        results['repeating_key_likely'] = True

    return results


# ============== ENCODING DETECTION ==============

def detect_base64(data: bytes) -> Dict[str, Any]:
    """Detect and decode potential Base64 encoded content"""
    results = {
        'found': False,
        'segments': []
    }

    # Base64 pattern
    b64_pattern = rb'[A-Za-z0-9+/]{20,}={0,2}'

    text = data.decode('ascii', errors='ignore')
    matches = re.finditer(r'[A-Za-z0-9+/]{20,}={0,2}', text)

    for match in matches:
        b64_str = match.group()
        try:
            # Try to decode
            import base64
            decoded = base64.b64decode(b64_str)

            # Check if decoded content is meaningful
            printable = sum(1 for b in decoded if 32 <= b < 127 or b in [9, 10, 13])

            results['segments'].append({
                'offset': match.start(),
                'length': len(b64_str),
                'decoded_length': len(decoded),
                'printable_ratio': printable / len(decoded) if decoded else 0,
                'decoded_preview': decoded[:100].decode('utf-8', errors='replace') if printable > len(decoded) * 0.5 else decoded[:50].hex()
            })
            results['found'] = True
        except:
            pass

    return results


def detect_hex_strings(data: bytes) -> Dict[str, Any]:
    """Detect hex-encoded strings"""
    results = {
        'found': False,
        'segments': []
    }

    text = data.decode('ascii', errors='ignore')
    # Match continuous hex strings
    hex_pattern = r'(?:[0-9a-fA-F]{2}){8,}'

    for match in re.finditer(hex_pattern, text):
        hex_str = match.group()
        try:
            decoded = bytes.fromhex(hex_str)
            printable = sum(1 for b in decoded if 32 <= b < 127 or b in [9, 10, 13])

            results['segments'].append({
                'offset': match.start(),
                'length': len(hex_str),
                'decoded_length': len(decoded),
                'printable_ratio': printable / len(decoded) if decoded else 0,
                'decoded_preview': decoded[:100].decode('utf-8', errors='replace') if printable > len(decoded) * 0.5 else None
            })
            results['found'] = True
        except:
            pass

    return results


def detect_unicode_steg(data: bytes) -> Dict[str, Any]:
    """Detect Unicode-based steganography (zero-width chars, homoglyphs)"""
    results = {
        'found': False,
        'zero_width_chars': [],
        'homoglyphs': [],
        'invisible_chars': 0
    }

    try:
        text = data.decode('utf-8', errors='ignore')
    except:
        return results

    # Zero-width characters
    zwc_chars = {
        '\u200b': 'ZERO WIDTH SPACE',
        '\u200c': 'ZERO WIDTH NON-JOINER',
        '\u200d': 'ZERO WIDTH JOINER',
        '\u2060': 'WORD JOINER',
        '\ufeff': 'ZERO WIDTH NO-BREAK SPACE (BOM)',
        '\u180e': 'MONGOLIAN VOWEL SEPARATOR',
    }

    for char, name in zwc_chars.items():
        count = text.count(char)
        if count > 0:
            results['zero_width_chars'].append({
                'char': repr(char),
                'name': name,
                'count': count
            })
            results['invisible_chars'] += count
            results['found'] = True

    # Check for variation selectors
    for i, char in enumerate(text):
        if '\ufe00' <= char <= '\ufe0f':
            results['invisible_chars'] += 1
            results['found'] = True

    return results


def detect_whitespace_steg(data: bytes) -> Dict[str, Any]:
    """Detect whitespace steganography (tabs/spaces encoding)"""
    results = {
        'found': False,
        'trailing_spaces': 0,
        'mixed_indentation': False,
        'suspicious_patterns': [],
        'potential_message': None
    }

    try:
        text = data.decode('utf-8', errors='ignore')
    except:
        return results

    lines = text.split('\n')
    tab_indent_lines = 0
    space_indent_lines = 0

    for line in lines:
        # Count trailing whitespace
        stripped = line.rstrip()
        trailing = len(line) - len(stripped)
        if trailing > 0:
            results['trailing_spaces'] += trailing

        # Check indentation type
        if line.startswith('\t'):
            tab_indent_lines += 1
        elif line.startswith(' '):
            space_indent_lines += 1

    if tab_indent_lines > 0 and space_indent_lines > 0:
        results['mixed_indentation'] = True

    if results['trailing_spaces'] > 10:
        results['found'] = True

        # Try to decode as binary (space=0, tab=1 or similar)
        bits = []
        for line in lines:
            trailing = line[len(line.rstrip()):]
            for char in trailing:
                if char == ' ':
                    bits.append('0')
                elif char == '\t':
                    bits.append('1')

        if len(bits) >= 8:
            try:
                bit_string = ''.join(bits)
                message = bytearray()
                for i in range(0, len(bit_string) - 7, 8):
                    byte_val = int(bit_string[i:i+8], 2)
                    if byte_val == 0:
                        break
                    message.append(byte_val)

                decoded = bytes(message).decode('utf-8', errors='ignore')
                if decoded and all(32 <= ord(c) < 127 or c in '\r\n\t' for c in decoded):
                    results['potential_message'] = decoded[:200]
            except:
                pass

    return results


# ============== TOOL REGISTRY ==============

class AnalysisToolRegistry:
    """Registry of all analysis tools organized by action name"""

    def __init__(self):
        self._tools: Dict[str, callable] = {}
        self._register_all_tools()

    def _register_all_tools(self):
        """Register all analysis tools"""
        # Core detection tools
        self._tools['detect_base64'] = detect_base64
        self._tools['detect_hex_strings'] = detect_hex_strings
        self._tools['detect_unicode_steg'] = detect_unicode_steg
        self._tools['detect_whitespace_steg'] = detect_whitespace_steg
        self._tools['detect_xor_patterns'] = detect_xor_patterns
        self._tools['detect_repeated_patterns'] = detect_repeated_patterns

        # Analysis tools
        self._tools['analyze_entropy'] = lambda data: {'entropy': calculate_entropy(data)}
        self._tools['analyze_bit_planes'] = analyze_bit_planes

        # Will be populated by format-specific modules

    def register(self, action: str, func: callable):
        """Register a tool function"""
        self._tools[action] = func

    def get(self, action: str) -> Optional[callable]:
        """Get a tool function by action name"""
        return self._tools.get(action)

    def execute(self, action: str, data: bytes, **kwargs) -> AnalysisResult:
        """Execute an analysis tool"""
        func = self._tools.get(action)
        if not func:
            return AnalysisResult(
                success=False,
                action=action,
                file_type="unknown",
                error=f"Unknown action: {action}"
            )

        try:
            result = func(data, **kwargs)

            # Convert result to AnalysisResult if needed
            if isinstance(result, AnalysisResult):
                return result
            elif isinstance(result, dict):
                return AnalysisResult(
                    success=True,
                    action=action,
                    file_type=kwargs.get('file_type', 'unknown'),
                    data=result,
                    suspicious=result.get('found', False) or result.get('suspicious', False)
                )
            else:
                return AnalysisResult(
                    success=True,
                    action=action,
                    file_type=kwargs.get('file_type', 'unknown'),
                    data={'result': result}
                )
        except Exception as e:
            return AnalysisResult(
                success=False,
                action=action,
                file_type=kwargs.get('file_type', 'unknown'),
                error=str(e)
            )

    def list_tools(self) -> List[str]:
        """List all registered tools"""
        return sorted(self._tools.keys())


# Global registry instance
TOOL_REGISTRY = AnalysisToolRegistry()


def execute_action(action: str, data: bytes, **kwargs) -> AnalysisResult:
    """Execute an analysis action"""
    return TOOL_REGISTRY.execute(action, data, **kwargs)


def list_available_tools() -> List[str]:
    """List all available analysis tools"""
    return TOOL_REGISTRY.list_tools()


# ============== PNG ANALYSIS TOOLS ==============

PNG_MAGIC = b'\x89PNG\r\n\x1a\n'

PNG_CHUNK_TYPES = {
    'IHDR': 'Image header',
    'PLTE': 'Palette',
    'IDAT': 'Image data',
    'IEND': 'Image end',
    'tEXt': 'Textual data',
    'zTXt': 'Compressed textual data',
    'iTXt': 'International textual data',
    'bKGD': 'Background color',
    'cHRM': 'Primary chromaticities',
    'gAMA': 'Gamma',
    'hIST': 'Palette histogram',
    'iCCP': 'ICC profile',
    'pHYs': 'Physical pixel dimensions',
    'sBIT': 'Significant bits',
    'sPLT': 'Suggested palette',
    'sRGB': 'Standard RGB color space',
    'tIME': 'Last modification time',
    'tRNS': 'Transparency',
    'eXIf': 'EXIF data',
    'acTL': 'Animation control (APNG)',
    'fcTL': 'Frame control (APNG)',
    'fdAT': 'Frame data (APNG)',
}


def png_parse_chunks(data: bytes) -> Dict[str, Any]:
    """Parse all PNG chunks and return detailed information"""
    if not data.startswith(PNG_MAGIC):
        return {'error': 'Not a valid PNG file', 'valid': False}

    chunks = []
    pos = 8  # Skip magic bytes
    total_idat_size = 0
    chunk_type_counts = {}

    while pos < len(data):
        if pos + 8 > len(data):
            break

        chunk_length = struct.unpack('>I', data[pos:pos+4])[0]
        chunk_type = data[pos+4:pos+8].decode('ascii', errors='replace')

        if pos + 12 + chunk_length > len(data):
            chunks.append({
                'type': chunk_type,
                'offset': pos,
                'length': chunk_length,
                'error': 'Truncated chunk'
            })
            break

        chunk_data = data[pos+8:pos+8+chunk_length]
        stored_crc = struct.unpack('>I', data[pos+8+chunk_length:pos+12+chunk_length])[0]
        calculated_crc = zlib.crc32(data[pos+4:pos+8+chunk_length]) & 0xffffffff

        chunk_info = {
            'type': chunk_type,
            'description': PNG_CHUNK_TYPES.get(chunk_type, 'Unknown/Private'),
            'offset': pos,
            'length': chunk_length,
            'crc_valid': stored_crc == calculated_crc,
            'crc_stored': f'{stored_crc:08x}',
            'crc_calculated': f'{calculated_crc:08x}',
        }

        # Track chunk type counts
        chunk_type_counts[chunk_type] = chunk_type_counts.get(chunk_type, 0) + 1

        # Track IDAT size
        if chunk_type == 'IDAT':
            total_idat_size += chunk_length

        # Parse IHDR
        if chunk_type == 'IHDR' and chunk_length == 13:
            width, height, bit_depth, color_type, compression, filter_method, interlace = struct.unpack('>IIBBBBB', chunk_data)
            chunk_info['parsed'] = {
                'width': width,
                'height': height,
                'bit_depth': bit_depth,
                'color_type': color_type,
                'compression': compression,
                'filter': filter_method,
                'interlace': interlace
            }

        # Parse text chunks
        elif chunk_type == 'tEXt':
            null_pos = chunk_data.find(b'\x00')
            if null_pos != -1:
                keyword = chunk_data[:null_pos].decode('latin-1', errors='replace')
                text = chunk_data[null_pos+1:].decode('latin-1', errors='replace')
                chunk_info['parsed'] = {'keyword': keyword, 'text': text[:500]}

        elif chunk_type == 'zTXt':
            null_pos = chunk_data.find(b'\x00')
            if null_pos != -1:
                keyword = chunk_data[:null_pos].decode('latin-1', errors='replace')
                try:
                    text = zlib.decompress(chunk_data[null_pos+2:]).decode('latin-1', errors='replace')
                    chunk_info['parsed'] = {'keyword': keyword, 'text': text[:500], 'compressed': True}
                except:
                    chunk_info['parsed'] = {'keyword': keyword, 'error': 'Decompression failed'}

        elif chunk_type == 'iTXt':
            null_pos = chunk_data.find(b'\x00')
            if null_pos != -1:
                keyword = chunk_data[:null_pos].decode('latin-1', errors='replace')
                chunk_info['parsed'] = {'keyword': keyword}

        # Parse tIME
        elif chunk_type == 'tIME' and chunk_length == 7:
            year, month, day, hour, minute, second = struct.unpack('>HBBBBB', chunk_data)
            chunk_info['parsed'] = {
                'timestamp': f'{year:04d}-{month:02d}-{day:02d} {hour:02d}:{minute:02d}:{second:02d}'
            }

        # Parse pHYs
        elif chunk_type == 'pHYs' and chunk_length == 9:
            ppux, ppuy, unit = struct.unpack('>IIB', chunk_data)
            chunk_info['parsed'] = {
                'pixels_per_unit_x': ppux,
                'pixels_per_unit_y': ppuy,
                'unit': 'meter' if unit == 1 else 'unknown'
            }

        chunks.append(chunk_info)
        pos += 12 + chunk_length

        if chunk_type == 'IEND':
            break

    # Check for data after IEND
    after_iend = len(data) - pos

    return {
        'valid': True,
        'chunks': chunks,
        'chunk_count': len(chunks),
        'chunk_type_counts': chunk_type_counts,
        'total_idat_size': total_idat_size,
        'data_after_iend': after_iend,
        'suspicious': after_iend > 0
    }


def png_extract_text_chunks(data: bytes) -> Dict[str, Any]:
    """Extract all text metadata from PNG"""
    result = png_parse_chunks(data)
    if not result.get('valid'):
        return result

    text_chunks = []
    for chunk in result['chunks']:
        if chunk['type'] in ('tEXt', 'zTXt', 'iTXt') and 'parsed' in chunk:
            text_chunks.append({
                'type': chunk['type'],
                'keyword': chunk['parsed'].get('keyword', ''),
                'text': chunk['parsed'].get('text', ''),
                'offset': chunk['offset']
            })

    return {
        'found': len(text_chunks) > 0,
        'text_chunks': text_chunks,
        'count': len(text_chunks)
    }


def png_detect_appended_data(data: bytes) -> Dict[str, Any]:
    """Detect data appended after PNG IEND chunk"""
    if not data.startswith(PNG_MAGIC):
        return {'found': False, 'error': 'Not a valid PNG file'}

    # Parse through PNG chunks to find actual IEND position
    pos = 8  # Skip magic
    iend_end_pos = None

    while pos + 8 <= len(data):
        chunk_length = struct.unpack('>I', data[pos:pos+4])[0]
        chunk_type = data[pos+4:pos+8]

        # Chunk end = pos + 4 (length) + 4 (type) + chunk_length + 4 (CRC)
        chunk_end_pos = pos + 12 + chunk_length

        if chunk_type == b'IEND':
            iend_end_pos = chunk_end_pos
            break

        pos = chunk_end_pos

    if iend_end_pos is None:
        return {'found': False, 'error': 'No IEND chunk found'}

    if iend_end_pos >= len(data):
        return {'found': False, 'appended_size': 0}

    appended_data = data[iend_end_pos:]

    if len(appended_data) == 0:
        return {'found': False, 'appended_size': 0}

    # Analyze appended data
    result = {
        'found': True,
        'appended_size': len(appended_data),
        'offset': iend_end_pos,
        'entropy': calculate_entropy(appended_data),
        'preview_hex': appended_data[:64].hex(),
        'suspicious': True
    }

    # Check if appended data is another file
    file_type = detect_file_type(appended_data)
    if file_type != FileType.UNKNOWN:
        result['embedded_file_type'] = file_type.value

    # Check for printable text
    try:
        text = appended_data[:200].decode('utf-8')
        if all(c.isprintable() or c in '\r\n\t' for c in text):
            result['text_preview'] = text
    except:
        pass

    return result


def png_analyze_idat(data: bytes) -> Dict[str, Any]:
    """Analyze PNG IDAT chunks for anomalies"""
    result = png_parse_chunks(data)
    if not result.get('valid'):
        return result

    idat_chunks = []
    prev_end = 0

    for chunk in result['chunks']:
        if chunk['type'] == 'IDAT':
            idat_chunks.append({
                'offset': chunk['offset'],
                'length': chunk['length'],
                'crc_valid': chunk['crc_valid']
            })

            # Check for gap between IDAT chunks
            if prev_end > 0 and chunk['offset'] != prev_end:
                gap = chunk['offset'] - prev_end
                if gap > 12:  # More than just the next chunk header
                    idat_chunks[-1]['gap_before'] = gap

            prev_end = chunk['offset'] + 12 + chunk['length']

    if not idat_chunks:
        return {'found': False, 'error': 'No IDAT chunks found'}

    total_size = sum(c['length'] for c in idat_chunks)
    sizes = [c['length'] for c in idat_chunks]

    return {
        'found': True,
        'chunk_count': len(idat_chunks),
        'total_size': total_size,
        'chunks': idat_chunks,
        'size_variance': max(sizes) - min(sizes) if len(sizes) > 1 else 0,
        'avg_chunk_size': total_size // len(idat_chunks),
        'all_crc_valid': all(c['crc_valid'] for c in idat_chunks),
        'suspicious': any('gap_before' in c for c in idat_chunks)
    }


def png_extract_lsb(data: bytes, bits: int = 1, channels: str = "RGB") -> Dict[str, Any]:
    """Extract LSB data from PNG image pixels"""
    if not HAS_PIL:
        return {'error': 'PIL not available', 'found': False}

    try:
        img = Image.open(io.BytesIO(data))

        # Convert to RGBA for consistent processing
        if img.mode == 'P':
            img = img.convert('RGBA')
        elif img.mode == 'L':
            img = img.convert('RGB')
        elif img.mode not in ('RGB', 'RGBA'):
            img = img.convert('RGBA')

        pixels = list(img.getdata())

        # Extract bits from specified channels
        channel_map = {'R': 0, 'G': 1, 'B': 2, 'A': 3}
        channel_indices = [channel_map[c] for c in channels.upper() if c in channel_map]

        extracted_bits = []
        mask = (1 << bits) - 1

        for pixel in pixels:
            for ch_idx in channel_indices:
                if ch_idx < len(pixel):
                    for bit_pos in range(bits):
                        extracted_bits.append((pixel[ch_idx] >> bit_pos) & 1)

        # Pack into bytes
        result_bytes = bytearray()
        for i in range(0, len(extracted_bits) - 7, 8):
            byte_val = 0
            for j in range(8):
                byte_val |= extracted_bits[i + j] << j
            result_bytes.append(byte_val)

        raw_data = bytes(result_bytes)

        # Look for patterns
        result = {
            'found': True,
            'extracted_size': len(raw_data),
            'channels': channels,
            'bits_per_channel': bits,
            'entropy': calculate_entropy(raw_data[:1024]),
            'raw_data': raw_data
        }

        # Check for STEG magic
        if raw_data[:4] == b'STEG':
            result['steg_header_found'] = True
            result['suspicious'] = True

        # Check for file signatures
        file_type = detect_file_type(raw_data)
        if file_type != FileType.UNKNOWN:
            result['embedded_file_type'] = file_type.value
            result['suspicious'] = True

        # Check for readable text
        try:
            text = raw_data[:100].decode('utf-8')
            printable = sum(1 for c in text if c.isprintable() or c in '\r\n\t')
            if printable > len(text) * 0.7:
                result['text_preview'] = text
                result['suspicious'] = True
        except:
            pass

        return result

    except Exception as e:
        return {'error': str(e), 'found': False}


def png_chi_square_analysis(data: bytes) -> Dict[str, Any]:
    """Chi-square analysis to detect LSB manipulation"""
    if not HAS_PIL or not HAS_NUMPY:
        return {'error': 'PIL or numpy not available'}

    try:
        img = Image.open(io.BytesIO(data))

        if img.mode == 'P':
            img = img.convert('RGB')
        elif img.mode == 'L':
            img = img.convert('RGB')
        elif img.mode not in ('RGB', 'RGBA'):
            img = img.convert('RGB')

        pixels = np.array(img)
        results = {}

        # Analyze each channel
        channel_names = ['Red', 'Green', 'Blue', 'Alpha']
        for ch_idx in range(min(pixels.shape[2], 4)):
            channel = pixels[:, :, ch_idx].flatten()

            # Pair analysis: count pairs (2k, 2k+1)
            pairs = np.zeros(128)
            for val in channel:
                pair_idx = val // 2
                if pair_idx < 128:
                    pairs[pair_idx] += 1

            # Expected distribution
            total = len(channel)
            expected = total / 128

            # Chi-square for pairs
            chi_sq = sum((pairs[i] - expected) ** 2 / expected for i in range(128) if expected > 0)

            # Also analyze bit plane
            lsb_plane = channel & 1
            ones = np.sum(lsb_plane)
            zeros = total - ones
            expected_ones = total / 2
            lsb_chi_sq = ((ones - expected_ones) ** 2 / expected_ones +
                          (zeros - expected_ones) ** 2 / expected_ones)

            results[channel_names[ch_idx]] = {
                'chi_square_pairs': float(chi_sq),
                'chi_square_lsb': float(lsb_chi_sq),
                'lsb_ones_ratio': float(ones / total),
                'suspicious': lsb_chi_sq > 3.84  # 95% confidence threshold
            }

        overall_suspicious = any(r['suspicious'] for r in results.values())

        return {
            'found': True,
            'channels': results,
            'suspicious': overall_suspicious,
            'interpretation': 'Low chi-square LSB values may indicate LSB steganography' if overall_suspicious else 'No strong LSB manipulation detected'
        }

    except Exception as e:
        return {'error': str(e), 'found': False}


def png_bit_plane_analysis(data: bytes) -> Dict[str, Any]:
    """Analyze individual bit planes of PNG image"""
    if not HAS_PIL or not HAS_NUMPY:
        return {'error': 'PIL or numpy not available'}

    try:
        img = Image.open(io.BytesIO(data))

        if img.mode == 'P':
            img = img.convert('RGB')

        pixels = np.array(img)
        results = {}

        channel_names = ['Red', 'Green', 'Blue', 'Alpha'][:pixels.shape[2] if len(pixels.shape) > 2 else 1]

        if len(pixels.shape) == 2:  # Grayscale
            pixels = pixels.reshape(pixels.shape[0], pixels.shape[1], 1)
            channel_names = ['Gray']

        for ch_idx, ch_name in enumerate(channel_names):
            channel = pixels[:, :, ch_idx]
            planes = {}

            for bit in range(8):
                plane = (channel >> bit) & 1

                # Calculate entropy of bit plane
                plane_bytes = np.packbits(plane.flatten())
                entropy = calculate_entropy(plane_bytes.tobytes())

                # Calculate percentage of 1s
                ones_pct = np.mean(plane) * 100

                planes[f'bit_{bit}'] = {
                    'entropy': float(entropy),
                    'ones_percentage': float(ones_pct),
                    'suspicious': bit < 2 and (entropy > 7.5 or abs(ones_pct - 50) < 1)
                }

            results[ch_name] = planes

        # Determine overall suspicion
        suspicious = any(
            plane['suspicious']
            for channel_planes in results.values()
            for plane in channel_planes.values()
        )

        return {
            'found': True,
            'channels': results,
            'suspicious': suspicious,
            'interpretation': 'High entropy in lower bit planes may indicate hidden data'
        }

    except Exception as e:
        return {'error': str(e), 'found': False}


def png_palette_analysis(data: bytes) -> Dict[str, Any]:
    """Analyze PNG palette for steganography indicators and attempt LSB decode"""
    if not HAS_PIL:
        return {'error': 'PIL not available'}

    try:
        img = Image.open(io.BytesIO(data))

        if img.mode != 'P':
            return {'found': False, 'reason': 'Image is not palette-based'}

        palette = img.getpalette()
        if not palette:
            return {'found': False, 'reason': 'No palette found'}

        # Palette is RGB triplets
        colors = []
        for i in range(0, len(palette), 3):
            colors.append((palette[i], palette[i+1], palette[i+2]))

        # Check for sorted palette (common steg indicator)
        is_sorted = colors == sorted(colors)

        # Check for near-duplicate colors (LSB differences only)
        near_duplicates = []
        for i, c1 in enumerate(colors):
            for j, c2 in enumerate(colors[i+1:], i+1):
                diff = sum(abs(a - b) for a, b in zip(c1, c2))
                if 0 < diff <= 3:  # Very similar colors
                    near_duplicates.append((i, j, diff))

        # Check color distribution
        histogram = img.histogram()
        used_colors = sum(1 for h in histogram[:256] if h > 0)

        # === PALETTE INDEX LSB DECODE ATTEMPT ===
        # Extract LSB of each pixel's palette index
        pixel_indices = list(img.getdata())
        bits = [idx & 1 for idx in pixel_indices]

        decoded_message = None
        decoded_length = None
        if len(bits) >= 32:
            # Try 32-bit length prefix (big-endian)
            length = 0
            for i in range(32):
                length = (length << 1) | bits[i]

            if 0 < length < min(5000, (len(bits) - 32) // 8):
                decoded_length = length
                msg_bits = bits[32:32 + length * 8]
                msg_bytes = bytearray()
                for i in range(0, len(msg_bits), 8):
                    v = 0
                    for j in range(8):
                        if i + j < len(msg_bits):
                            v = (v << 1) | msg_bits[i + j]
                    msg_bytes.append(v)
                try:
                    decoded_message = msg_bytes.decode('utf-8', errors='replace')
                except:
                    decoded_message = msg_bytes.hex()

        # === PALETTE COLOR LSB DECODE ATTEMPT ===
        # Some steg tools encode in the LSB of palette colors themselves
        palette_lsb_bits = []
        for r, g, b in colors:
            palette_lsb_bits.extend([r & 1, g & 1, b & 1])

        palette_decoded = None
        if len(palette_lsb_bits) >= 32:
            plen = 0
            for i in range(32):
                plen = (plen << 1) | palette_lsb_bits[i]
            if 0 < plen < (len(palette_lsb_bits) - 32) // 8:
                pbits = palette_lsb_bits[32:32 + plen * 8]
                pbytes = bytearray()
                for i in range(0, len(pbits), 8):
                    v = 0
                    for j in range(8):
                        if i + j < len(pbits):
                            v = (v << 1) | pbits[i + j]
                    pbytes.append(v)
                try:
                    palette_decoded = pbytes.decode('utf-8', errors='replace')
                except:
                    palette_decoded = pbytes.hex()

        result = {
            'found': True,
            'palette_size': len(colors),
            'used_colors': used_colors,
            'is_sorted': is_sorted,
            'near_duplicate_pairs': len(near_duplicates),
            'near_duplicates': near_duplicates[:10],
            'suspicious': len(near_duplicates) > 5 or is_sorted or decoded_message is not None,
            'interpretation': 'Sorted palette or many near-duplicates may indicate palette-based steganography',
        }

        if decoded_message:
            result['index_lsb_decode'] = {
                'length': decoded_length,
                'message': decoded_message[:200],
                'method': 'palette_index_lsb'
            }
        if palette_decoded:
            result['palette_color_lsb_decode'] = {
                'message': palette_decoded[:200],
                'method': 'palette_color_lsb'
            }

        return result

    except Exception as e:
        return {'error': str(e), 'found': False}


def detect_pvd_steg(data: bytes) -> Dict[str, Any]:
    """Detect and decode Pixel Value Differencing (PVD) steganography.

    PVD encodes bits in the LSB of the second pixel in each horizontal pair.
    bit=1 means the R channel of pixel[x+1] is odd, bit=0 means even.
    """
    if not HAS_PIL:
        return {'error': 'PIL not available', 'found': False}

    try:
        img = Image.open(io.BytesIO(data)).convert('RGB')
        pixels = img.load()
        width, height = img.size

        # Extract bits from R channel LSB of every second pixel in each pair
        bits = []
        for y in range(height):
            for x in range(0, width - 1, 2):
                r2, _, _ = pixels[x + 1, y]
                bits.append(r2 & 1)

        if len(bits) < 32:
            return {'found': False, 'reason': 'Not enough pixel pairs'}

        # Try 32-bit big-endian length prefix
        length = 0
        for i in range(32):
            length = (length << 1) | bits[i]

        if length <= 0 or length > min(5000, (len(bits) - 32) // 8):
            return {'found': False, 'reason': f'Invalid length prefix: {length}'}

        msg_bits = bits[32:32 + length * 8]
        msg_bytes = bytearray()
        for i in range(0, len(msg_bits), 8):
            v = 0
            for j in range(8):
                if i + j < len(msg_bits):
                    v = (v << 1) | msg_bits[i + j]
            msg_bytes.append(v)

        try:
            decoded = msg_bytes.decode('utf-8', errors='replace')
        except:
            decoded = msg_bytes.hex()

        return {
            'found': True,
            'method': 'pvd_pair_lsb',
            'length': length,
            'message': decoded[:200],
            'suspicious': True,
            'findings': [f'PVD decode ({length} bytes): {decoded[:80]}'],
            'interpretation': 'Pixel Value Differencing — data encoded in R channel LSB of paired pixels'
        }

    except Exception as e:
        return {'error': str(e), 'found': False}


def detect_histogram_shift_steg(data: bytes) -> Dict[str, Any]:
    """Detect and decode histogram shifting steganography.

    Histogram shifting encodes bits by shifting the peak pixel value:
    peak stays = 0, peak+1 = 1. The encoder also shifts all pixels > peak
    by +1 to make room, so the encoded image has two peaks (original peak
    split into peak and peak+1). We try multiple candidate peaks.
    """
    if not HAS_PIL:
        return {'error': 'PIL not available', 'found': False}

    try:
        img = Image.open(io.BytesIO(data))
        if img.mode != 'L':
            img = img.convert('L')
        pixels = img.load()
        width, height = img.size

        # Build histogram
        hist = [0] * 256
        for y in range(height):
            for x in range(width):
                hist[pixels[x, y]] += 1

        # After encoding, the original peak is split across peak and peak+1.
        # We brute-force all possible peak values (0-254) since the peak
        # may not be the highest in the encoded histogram.
        candidates = list(range(255))

        for peak in candidates:
            bits = []
            for y in range(height):
                for x in range(width):
                    v = pixels[x, y]
                    if v == peak:
                        bits.append(0)
                    elif v == peak + 1:
                        bits.append(1)

            if len(bits) < 40:
                continue

            # Try 32-bit length prefix
            length = 0
            for i in range(32):
                length = (length << 1) | bits[i]

            if length <= 0 or length > min(5000, (len(bits) - 32) // 8):
                continue

            msg_bits = bits[32:32 + length * 8]
            msg_bytes = bytearray()
            for i in range(0, len(msg_bits), 8):
                v = 0
                for j in range(8):
                    if i + j < len(msg_bits):
                        v = (v << 1) | msg_bits[i + j]
                msg_bytes.append(v)

            try:
                decoded = msg_bytes.decode('utf-8', errors='replace')
            except:
                continue

            # Check if it looks like valid text (high threshold to avoid false positives)
            printable = sum(1 for c in decoded if c.isprintable() or c in '\r\n\t')
            if printable > len(decoded) * 0.85:
                return {
                    'found': True,
                    'method': 'histogram_shift',
                    'peak': peak,
                    'length': length,
                    'message': decoded[:200],
                    'suspicious': True,
                    'findings': [f'Histogram shift decode (peak={peak}, {length} bytes): {decoded[:80]}'],
                    'interpretation': 'Histogram shifting — peak pixel values encode bits via shift'
                }

        return {'found': False, 'reason': 'No valid histogram shift pattern found'}

    except Exception as e:
        return {'error': str(e), 'found': False}


def detect_multibit_lsb(data: bytes) -> Dict[str, Any]:
    """Detect and decode multi-bit LSB steganography (2-bit, 4-bit per channel)."""
    if not HAS_PIL:
        return {'error': 'PIL not available', 'found': False}

    try:
        img = Image.open(io.BytesIO(data)).convert('RGBA')
        pixels = list(img.getdata())
        results = {}

        for bits_per_ch in [2, 4]:
            mask = (1 << bits_per_ch) - 1
            nibbles = []
            for r, g, b, a in pixels:
                for ch in [r, g, b]:
                    nibbles.append(ch & mask)

            units_per_byte = 8 // bits_per_ch
            length_units = 4 * units_per_byte

            if len(nibbles) < length_units:
                continue

            length = 0
            for i in range(length_units):
                length = (length << bits_per_ch) | nibbles[i]

            if 0 < length < min(5000, (len(nibbles) - length_units) // units_per_byte):
                msg = bytearray()
                idx = length_units
                for _ in range(length):
                    byte_val = 0
                    for _ in range(units_per_byte):
                        if idx < len(nibbles):
                            byte_val = (byte_val << bits_per_ch) | nibbles[idx]
                            idx += 1
                    msg.append(byte_val & 0xFF)

                try:
                    decoded = msg.decode('utf-8', errors='replace')
                except:
                    decoded = msg.hex()

                printable = sum(1 for c in decoded if c.isprintable() or c in '\r\n\t')
                if printable > len(decoded) * 0.5:
                    results[f'{bits_per_ch}bit'] = {
                        'found': True,
                        'bits_per_channel': bits_per_ch,
                        'length': length,
                        'message': decoded[:200],
                    }

        if results:
            best = list(results.values())[0]
            return {
                'found': True,
                'method': f'multibit_lsb_{best["bits_per_channel"]}bpc',
                'length': best['length'],
                'message': best['message'],
                'suspicious': True,
                'findings': [f'Multi-bit LSB ({best["bits_per_channel"]}bpc, {best["length"]} bytes): {best["message"][:80]}'],
            }

        return {'found': False, 'reason': 'No valid multi-bit LSB pattern found'}

    except Exception as e:
        return {'error': str(e), 'found': False}


def gif_analysis(data: bytes) -> Dict[str, Any]:
    """Analyze GIF files for steganography — comment blocks, palette LSB, disposal methods"""
    if not HAS_PIL:
        return {'error': 'PIL not available'}

    results = {
        'found': False,
        'findings': [],
        'comment_blocks': [],
        'palette_lsb_decode': None,
        'disposal_methods': [],
    }

    try:
        # 1. Extract GIF comment extension blocks from raw data
        pos = 0
        while pos < len(data) - 2:
            if data[pos] == 0x21 and data[pos + 1] == 0xFE:  # Comment extension
                pos += 2
                comment = bytearray()
                while pos < len(data) and data[pos] != 0:
                    block_len = data[pos]
                    pos += 1
                    comment.extend(data[pos:pos + block_len])
                    pos += block_len
                pos += 1  # Skip terminator
                try:
                    decoded = comment.decode('utf-8', errors='replace')
                    results['comment_blocks'].append(decoded)
                    results['found'] = True
                    results['findings'].append(f'Comment block: {decoded[:100]}')
                except:
                    results['comment_blocks'].append(comment.hex())
                continue
            pos += 1

        # 2. Extract disposal method bits from GCE blocks
        pos = 0
        while pos < len(data) - 5:
            if data[pos] == 0x21 and data[pos + 1] == 0xF9 and data[pos + 2] == 0x04:
                packed = data[pos + 3]
                disposal = (packed >> 2) & 0x07
                results['disposal_methods'].append(disposal)
                pos += 6
            else:
                pos += 1

        if len(results['disposal_methods']) > 1:
            results['findings'].append(f"Disposal methods: {results['disposal_methods'][:20]}")

        # 3. Palette index LSB decode
        img = Image.open(io.BytesIO(data))
        if img.mode == 'P':
            pixel_indices = list(img.getdata())
            bits = [idx & 1 for idx in pixel_indices]

            if len(bits) >= 32:
                length = 0
                for i in range(32):
                    length = (length << 1) | bits[i]

                if 0 < length < min(5000, (len(bits) - 32) // 8):
                    msg_bits = bits[32:32 + length * 8]
                    msg_bytes = bytearray()
                    for i in range(0, len(msg_bits), 8):
                        v = 0
                        for j in range(8):
                            if i + j < len(msg_bits):
                                v = (v << 1) | msg_bits[i + j]
                        msg_bytes.append(v)
                    try:
                        decoded_msg = msg_bytes.decode('utf-8', errors='replace')
                        results['palette_lsb_decode'] = {
                            'length': length,
                            'message': decoded_msg[:200],
                            'method': 'palette_index_lsb'
                        }
                        results['found'] = True
                        results['findings'].append(f'Palette LSB decode ({length} bytes): {decoded_msg[:50]}')
                    except:
                        pass

        results['suspicious'] = results['found']
        return results

    except Exception as e:
        return {'error': str(e), 'found': False}


def bmp_analysis(data: bytes) -> Dict[str, Any]:
    """Analyze BMP files for steganography — reserved header fields, trailing data, LSB"""
    results = {
        'found': False,
        'findings': [],
        'reserved_bytes': None,
        'trailing_data': None,
        'lsb_decode': None,
    }

    if len(data) < 54:
        return {'error': 'File too small for BMP', 'found': False}

    if data[:2] != b'BM':
        return {'error': 'Not a BMP file', 'found': False}

    try:
        # Check reserved bytes at offset 6-9 (should be zero in clean BMPs)
        reserved = data[6:10]
        if reserved != b'\x00\x00\x00\x00':
            results['reserved_bytes'] = reserved.hex()
            results['found'] = True
            results['findings'].append(f'Non-zero reserved bytes: {reserved.hex()}')

        # Check for trailing data after pixel data
        file_size = struct.unpack('<I', data[2:6])[0]
        actual_size = len(data)
        if actual_size > file_size:
            trailing = data[file_size:]
            results['trailing_data'] = {
                'size': actual_size - file_size,
                'preview': trailing[:200].decode('utf-8', errors='replace')
            }
            results['found'] = True
            results['findings'].append(f'Trailing data: {actual_size - file_size} bytes after BMP end')

        # LSB decode via PIL
        if HAS_PIL:
            img = Image.open(io.BytesIO(data)).convert('RGBA')
            pixels = list(img.getdata())
            bits = []
            for r, g, b, a in pixels:
                for ch in [r, g, b]:
                    bits.append(ch & 1)

            if len(bits) >= 32:
                length = 0
                for i in range(32):
                    length = (length << 1) | bits[i]

                if 0 < length < min(5000, (len(bits) - 32) // 8):
                    msg_bits = bits[32:32 + length * 8]
                    msg_bytes = bytearray()
                    for i in range(0, len(msg_bits), 8):
                        v = 0
                        for j in range(8):
                            if i + j < len(msg_bits):
                                v = (v << 1) | msg_bits[i + j]
                        msg_bytes.append(v)
                    try:
                        decoded = msg_bytes.decode('utf-8', errors='replace')
                        results['lsb_decode'] = {
                            'length': length,
                            'message': decoded[:200],
                            'method': 'rgb_lsb'
                        }
                        results['found'] = True
                        results['findings'].append(f'LSB decode ({length} bytes): {decoded[:50]}')
                    except:
                        pass

        results['suspicious'] = results['found']
        return results

    except Exception as e:
        return {'error': str(e), 'found': False}


def png_filter_analysis(data: bytes) -> Dict[str, Any]:
    """Analyze PNG filter bytes for anomalies"""
    result = png_parse_chunks(data)
    if not result.get('valid'):
        return result

    # Need to decompress IDAT to get filter bytes
    idat_data = b''
    ihdr_data = None

    for chunk in result['chunks']:
        if chunk['type'] == 'IDAT':
            offset = chunk['offset']
            length = chunk['length']
            idat_data += data[offset+8:offset+8+length]
        elif chunk['type'] == 'IHDR' and 'parsed' in chunk:
            ihdr_data = chunk['parsed']

    if not ihdr_data:
        return {'error': 'No IHDR chunk found'}

    try:
        decompressed = zlib.decompress(idat_data)
    except:
        return {'error': 'Failed to decompress IDAT'}

    # Calculate bytes per row
    width = ihdr_data['width']
    height = ihdr_data['height']
    bit_depth = ihdr_data['bit_depth']
    color_type = ihdr_data['color_type']

    # Samples per pixel based on color type
    samples = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}.get(color_type, 3)
    bytes_per_pixel = max(1, (samples * bit_depth) // 8)
    row_bytes = 1 + width * bytes_per_pixel  # +1 for filter byte

    # Extract filter bytes
    filter_bytes = []
    for row in range(height):
        offset = row * row_bytes
        if offset < len(decompressed):
            filter_bytes.append(decompressed[offset])

    # Analyze filter distribution
    filter_counts = {}
    for f in filter_bytes:
        filter_counts[f] = filter_counts.get(f, 0) + 1

    filter_names = {0: 'None', 1: 'Sub', 2: 'Up', 3: 'Average', 4: 'Paeth'}

    return {
        'found': True,
        'row_count': len(filter_bytes),
        'filter_distribution': {filter_names.get(k, f'Unknown({k})'): v for k, v in filter_counts.items()},
        'unique_filters': len(filter_counts),
        'suspicious': 0 in filter_counts and filter_counts[0] > len(filter_bytes) * 0.9,
        'interpretation': 'Excessive use of filter 0 (None) may indicate modified image'
    }


def png_detect_embedded_png(data: bytes) -> Dict[str, Any]:
    """Detect PNG files embedded within PNG (nested steganography)"""
    results = {
        'found': False,
        'embedded_pngs': []
    }

    # Look for PNG magic in various locations
    search_start = 8  # Skip the outer PNG magic

    while True:
        pos = data.find(PNG_MAGIC, search_start)
        if pos == -1:
            break

        # Try to parse as PNG
        try:
            end_pos = data.find(b'IEND', pos)
            if end_pos != -1:
                # IEND + length (0) + CRC = +8 bytes
                end_pos += 12
                embedded_size = end_pos - pos

                results['embedded_pngs'].append({
                    'offset': pos,
                    'size': embedded_size,
                    'location': 'after_iend' if pos > data.rfind(b'IEND', 0, pos) else 'within_image'
                })
                results['found'] = True
        except:
            pass

        search_start = pos + 1

    results['count'] = len(results['embedded_pngs'])
    results['suspicious'] = results['found']

    return results


def png_color_histogram_analysis(data: bytes) -> Dict[str, Any]:
    """Analyze color histogram for LSB steganography indicators"""
    if not HAS_PIL or not HAS_NUMPY:
        return {'error': 'PIL or numpy not available'}

    try:
        img = Image.open(io.BytesIO(data))

        if img.mode == 'P':
            img = img.convert('RGB')

        pixels = np.array(img)
        results = {}

        channel_names = ['Red', 'Green', 'Blue'][:pixels.shape[2] if len(pixels.shape) > 2 else 1]

        for ch_idx, ch_name in enumerate(channel_names):
            channel = pixels[:, :, ch_idx].flatten()

            # Calculate histogram
            hist, _ = np.histogram(channel, bins=256, range=(0, 256))

            # Pairs of Values (PoV) analysis
            # In natural images, adjacent histogram bins have similar counts
            # LSB embedding creates anomalies in pairs (2k, 2k+1)
            pair_diffs = []
            for i in range(0, 256, 2):
                if hist[i] + hist[i+1] > 0:
                    diff = abs(hist[i] - hist[i+1]) / (hist[i] + hist[i+1])
                    pair_diffs.append(diff)

            avg_pair_diff = np.mean(pair_diffs) if pair_diffs else 0

            results[ch_name] = {
                'unique_values': int(np.sum(hist > 0)),
                'avg_pair_difference': float(avg_pair_diff),
                'suspicious': avg_pair_diff < 0.05  # Very similar pairs suggest LSB
            }

        return {
            'found': True,
            'channels': results,
            'suspicious': any(r['suspicious'] for r in results.values()),
            'interpretation': 'Similar histogram pair values may indicate LSB steganography'
        }

    except Exception as e:
        return {'error': str(e), 'found': False}


def png_visual_attack(data: bytes) -> Dict[str, Any]:
    """Generate visual attack images for bit plane analysis"""
    if not HAS_PIL or not HAS_NUMPY:
        return {'error': 'PIL or numpy not available'}

    try:
        img = Image.open(io.BytesIO(data))

        if img.mode == 'P':
            img = img.convert('RGB')

        pixels = np.array(img)

        # Extract LSB planes and scale to full intensity
        lsb_images = {}

        channel_names = ['Red', 'Green', 'Blue']
        for ch_idx, ch_name in enumerate(channel_names):
            if ch_idx < pixels.shape[2]:
                # LSB plane scaled to 0 or 255
                lsb = (pixels[:, :, ch_idx] & 1) * 255
                lsb_images[ch_name] = lsb.tolist()  # Can be reconstructed client-side

        # Combined RGB LSB
        combined = np.zeros_like(pixels)
        for ch_idx in range(min(3, pixels.shape[2])):
            combined[:, :, ch_idx] = (pixels[:, :, ch_idx] & 1) * 255

        return {
            'found': True,
            'image_size': [int(pixels.shape[1]), int(pixels.shape[0])],
            'channel_lsb_available': list(lsb_images.keys()),
            'interpretation': 'Visual inspection of LSB planes can reveal hidden patterns'
        }

    except Exception as e:
        return {'error': str(e), 'found': False}


def png_steg_signature_scan(data: bytes) -> Dict[str, Any]:
    """Scan for known steganography tool signatures"""
    signatures = {
        b'STEG': 'Stegosaurus Wrecks',
        b'openstego': 'OpenStego',
        b'steghide': 'Steghide',
        b'F5': 'F5 Algorithm',
        b'jphide': 'JPHide',
        b'outguess': 'OutGuess',
        b'invisible secrets': 'Invisible Secrets',
        b'camouflage': 'Camouflage',
        b'snow': 'SNOW',
        b'\x00\x00\x00\x01steg': 'Generic Steg Header',
    }

    found = []

    for sig, tool_name in signatures.items():
        pos = data.find(sig)
        if pos != -1:
            found.append({
                'signature': sig.hex() if not sig.isascii() else sig.decode('ascii', errors='replace'),
                'tool': tool_name,
                'offset': pos
            })

    # Also check LSB extracted data
    lsb_result = png_extract_lsb(data, bits=1, channels="RGB")
    if lsb_result.get('raw_data'):
        lsb_data = lsb_result['raw_data'][:1000]
        for sig, tool_name in signatures.items():
            if sig in lsb_data:
                found.append({
                    'signature': sig.hex() if not sig.isascii() else sig.decode('ascii', errors='replace'),
                    'tool': tool_name,
                    'location': 'LSB_extracted'
                })

    return {
        'found': len(found) > 0,
        'signatures': found,
        'suspicious': len(found) > 0
    }


def png_full_analysis(data: bytes) -> Dict[str, Any]:
    """Run all PNG analysis tools and compile results"""
    results = {
        'file_type': 'PNG',
        'analyses': {}
    }

    # Run all PNG analysis tools
    analyses = [
        ('chunk_parse', png_parse_chunks),
        ('text_chunks', png_extract_text_chunks),
        ('appended_data', png_detect_appended_data),
        ('idat_analysis', png_analyze_idat),
        ('chi_square', png_chi_square_analysis),
        ('bit_planes', png_bit_plane_analysis),
        ('histogram', png_color_histogram_analysis),
        ('filter_analysis', png_filter_analysis),
        ('embedded_png', png_detect_embedded_png),
        ('steg_signatures', png_steg_signature_scan),
    ]

    suspicious_count = 0

    for name, func in analyses:
        try:
            result = func(data)
            results['analyses'][name] = result
            if result.get('suspicious'):
                suspicious_count += 1
        except Exception as e:
            results['analyses'][name] = {'error': str(e)}

    results['suspicious_indicators'] = suspicious_count
    results['overall_suspicious'] = suspicious_count >= 2
    results['summary'] = f"Found {suspicious_count} suspicious indicators"

    return results


# Register PNG tools
def _register_png_tools():
    """Register all PNG analysis tools with the global registry"""
    TOOL_REGISTRY.register('png_parse_chunks', png_parse_chunks)
    TOOL_REGISTRY.register('png_extract_text_chunks', png_extract_text_chunks)
    TOOL_REGISTRY.register('png_detect_appended_data', png_detect_appended_data)
    TOOL_REGISTRY.register('png_analyze_idat', png_analyze_idat)
    TOOL_REGISTRY.register('png_extract_lsb', png_extract_lsb)
    TOOL_REGISTRY.register('png_chi_square_analysis', png_chi_square_analysis)
    TOOL_REGISTRY.register('png_bit_plane_analysis', png_bit_plane_analysis)
    TOOL_REGISTRY.register('png_palette_analysis', png_palette_analysis)
    TOOL_REGISTRY.register('png_filter_analysis', png_filter_analysis)
    TOOL_REGISTRY.register('png_detect_embedded_png', png_detect_embedded_png)
    TOOL_REGISTRY.register('png_color_histogram_analysis', png_color_histogram_analysis)
    TOOL_REGISTRY.register('png_visual_attack', png_visual_attack)
    TOOL_REGISTRY.register('png_steg_signature_scan', png_steg_signature_scan)
    TOOL_REGISTRY.register('png_full_analysis', png_full_analysis)
    # GIF, BMP, and advanced image analysis
    TOOL_REGISTRY.register('gif_analysis', gif_analysis)
    TOOL_REGISTRY.register('bmp_analysis', bmp_analysis)
    TOOL_REGISTRY.register('detect_pvd_steg', detect_pvd_steg)
    TOOL_REGISTRY.register('detect_histogram_shift_steg', detect_histogram_shift_steg)
    TOOL_REGISTRY.register('detect_multibit_lsb', detect_multibit_lsb)


# Auto-register on module load
_register_png_tools()


# ============== ADVANCED TEXT STEGANOGRAPHY DETECTION ==============

def detect_homoglyph_steg(data: bytes) -> Dict[str, Any]:
    """Detect Cyrillic/Latin homoglyph substitution steganography."""
    results = {'found': False, 'substitutions': 0, 'details': []}
    try:
        text = data.decode('utf-8', errors='ignore')
    except:
        return results

    # Cyrillic chars that look like Latin
    CYRILLIC_TO_LATIN = {
        '\u0430': 'a', '\u0441': 'c', '\u0435': 'e', '\u043e': 'o',
        '\u0440': 'p', '\u0455': 's', '\u0445': 'x', '\u0443': 'y',
        '\u0410': 'A', '\u0412': 'B', '\u0421': 'C', '\u0415': 'E',
        '\u041d': 'H', '\u041a': 'K', '\u041c': 'M', '\u041e': 'O',
        '\u0420': 'P', '\u0422': 'T', '\u0425': 'X',
    }

    for i, ch in enumerate(text):
        if ch in CYRILLIC_TO_LATIN:
            results['substitutions'] += 1
            if results['substitutions'] <= 5:
                results['details'].append({
                    'offset': i,
                    'cyrillic': repr(ch),
                    'looks_like': CYRILLIC_TO_LATIN[ch]
                })

    if results['substitutions'] > 3:
        results['found'] = True

    return results


def detect_variation_selector_steg(data: bytes) -> Dict[str, Any]:
    """Detect variation selector steganography."""
    results = {'found': False, 'count': 0, 'selectors': []}
    try:
        text = data.decode('utf-8', errors='ignore')
    except:
        return results

    for i, ch in enumerate(text):
        if '\uFE00' <= ch <= '\uFE0F':
            results['count'] += 1
            if results['count'] <= 5:
                results['selectors'].append({'offset': i, 'selector': f'VS{ord(ch) - 0xFDFF}'})

    if results['count'] > 3:
        results['found'] = True

    return results


def detect_combining_mark_steg(data: bytes) -> Dict[str, Any]:
    """Detect steganography via invisible combining characters."""
    results = {'found': False, 'count': 0, 'marks': []}
    try:
        text = data.decode('utf-8', errors='ignore')
    except:
        return results

    INVISIBLE_COMBINERS = {
        '\u034F': 'COMBINING GRAPHEME JOINER',
        '\u200D': 'ZERO WIDTH JOINER',
        '\u2060': 'WORD JOINER',
        '\u2061': 'FUNCTION APPLICATION',
        '\u2062': 'INVISIBLE TIMES',
        '\u2063': 'INVISIBLE SEPARATOR',
        '\u2064': 'INVISIBLE PLUS',
    }

    for i, ch in enumerate(text):
        if ch in INVISIBLE_COMBINERS:
            results['count'] += 1
            if results['count'] <= 5:
                results['marks'].append({
                    'offset': i,
                    'name': INVISIBLE_COMBINERS[ch]
                })

    if results['count'] > 3:
        results['found'] = True

    return results


def detect_confusable_whitespace(data: bytes) -> Dict[str, Any]:
    """Detect steganography via Unicode whitespace variants."""
    results = {'found': False, 'non_standard_spaces': 0, 'types': {}}
    try:
        text = data.decode('utf-8', errors='ignore')
    except:
        return results

    SPACE_VARIANTS = {
        '\u00A0': 'NO-BREAK SPACE',
        '\u2000': 'EN QUAD',
        '\u2001': 'EM QUAD',
        '\u2002': 'EN SPACE',
        '\u2003': 'EM SPACE',
        '\u2004': 'THREE-PER-EM SPACE',
        '\u2005': 'FOUR-PER-EM SPACE',
        '\u2006': 'SIX-PER-EM SPACE',
        '\u2007': 'FIGURE SPACE',
        '\u2008': 'PUNCTUATION SPACE',
        '\u2009': 'THIN SPACE',
        '\u200A': 'HAIR SPACE',
        '\u202F': 'NARROW NO-BREAK SPACE',
        '\u205F': 'MEDIUM MATHEMATICAL SPACE',
        '\u3000': 'IDEOGRAPHIC SPACE',
    }

    for ch in text:
        if ch in SPACE_VARIANTS:
            name = SPACE_VARIANTS[ch]
            results['non_standard_spaces'] += 1
            results['types'][name] = results['types'].get(name, 0) + 1

    if results['non_standard_spaces'] > 3:
        results['found'] = True

    return results


def detect_emoji_steg(data: bytes) -> Dict[str, Any]:
    """Detect emoji substitution steganography patterns."""
    results = {'found': False, 'emoji_count': 0, 'pattern_detected': False}
    try:
        text = data.decode('utf-8', errors='ignore')
    except:
        return results

    import unicodedata
    emojis = [ch for ch in text if unicodedata.category(ch).startswith(('So', 'Sk'))]
    results['emoji_count'] = len(emojis)

    # Check for alternating emoji pairs (characteristic of emoji substitution steg)
    if len(emojis) > 20:
        # Count unique emoji types
        unique = len(set(emojis))
        if unique <= 20 and len(emojis) > 50:
            results['pattern_detected'] = True
            results['found'] = True

    return results


def detect_capitalization_steg(data: bytes) -> Dict[str, Any]:
    """Detect capitalization encoding steganography."""
    results = {'found': False, 'suspicious_caps': 0, 'total_words': 0}
    try:
        text = data.decode('utf-8', errors='ignore')
    except:
        return results

    words = text.split()
    results['total_words'] = len(words)

    # Count words with unexpected capitalization (mid-sentence uppercase)
    for i, word in enumerate(words):
        if word and word[0].isupper() and i > 0:
            prev = words[i - 1] if i > 0 else ''
            # Not after sentence end
            if prev and prev[-1] not in '.!?:':
                results['suspicious_caps'] += 1

    # High ratio of unexpected caps suggests encoding
    if results['total_words'] > 20:
        ratio = results['suspicious_caps'] / results['total_words']
        if ratio > 0.15:  # More than 15% unexpected caps
            results['found'] = True

    return results


# ============== AUDIO STEGANOGRAPHY ==============

def audio_lsb_decode(data: bytes) -> Dict[str, Any]:
    """Decode LSB steganography from WAV audio files."""
    import wave
    try:
        w = wave.open(io.BytesIO(data))
        raw = w.readframes(w.getnframes())
        sampwidth = w.getsampwidth()
        w.close()
        if sampwidth != 2:
            return {'found': False, 'reason': f'Sample width {sampwidth} not supported'}
        samples = struct.unpack(f'<{len(raw)//2}h', raw)
        bits = [s & 1 for s in samples]
        if len(bits) < 32:
            return {'found': False}
        length = 0
        for i in range(32):
            length = (length << 1) | bits[i]
        if length <= 0 or length > min(10000, (len(bits) - 32) // 8):
            return {'found': False, 'reason': f'Invalid length: {length}'}
        msg = bytearray()
        for i in range(0, length * 8, 8):
            v = 0
            for j in range(8):
                if 32 + i + j < len(bits):
                    v = (v << 1) | bits[32 + i + j]
            msg.append(v)
        decoded = msg.decode('utf-8', errors='replace')
        return {'found': True, 'method': 'audio_lsb', 'length': length,
                'message': decoded[:200], 'suspicious': True,
                'findings': [f'Audio LSB ({length} bytes): {decoded[:80]}']}
    except Exception as e:
        return {'error': str(e), 'found': False}


# ============== PCAP / NETWORK PROTOCOL DECODERS ==============

def pcap_decode(data: bytes) -> Dict[str, Any]:
    """Parse PCAP and extract steganographic data from protocol fields."""
    results = {'found': False, 'findings': [], 'packets': 0, 'methods': {}}
    if len(data) < 24:
        return results
    magic = data[:4]
    if magic == b'\xa1\xb2\xc3\xd4':
        endian = '>'
    elif magic == b'\xd4\xc3\xb2\xa1':
        endian = '<'
    else:
        return {'found': False, 'reason': 'Not PCAP'}

    pos = 24
    ttl_bytes = bytearray()
    ipid_bytes = bytearray()
    win_bytes = bytearray()
    urg_bytes = bytearray()
    payloads = bytearray()
    timestamps = []
    import base64, re as _re

    while pos + 16 <= len(data):
        ts_sec = struct.unpack(f'{endian}I', data[pos:pos+4])[0]
        ts_usec = struct.unpack(f'{endian}I', data[pos+4:pos+8])[0]
        incl_len = struct.unpack(f'{endian}I', data[pos+8:pos+12])[0]
        pos += 16
        if pos + incl_len > len(data):
            break
        pkt = data[pos:pos + incl_len]
        results['packets'] += 1
        timestamps.append(ts_sec * 1000000 + ts_usec)
        if len(pkt) > 34 and pkt[12:14] == b'\x08\x00':
            ip_start = 14
            ttl_bytes.append(pkt[ip_start + 8])
            ipid_bytes.extend(pkt[ip_start + 4:ip_start + 6])
            protocol = pkt[ip_start + 9]
            ip_hdr_len = (pkt[ip_start] & 0x0F) * 4
            if protocol == 17 and len(pkt) > ip_start + ip_hdr_len + 8:
                udp_start = ip_start + ip_hdr_len
                udp_len = struct.unpack('>H', pkt[udp_start + 4:udp_start + 6])[0]
                payloads.extend(pkt[udp_start + 8:udp_start + udp_len])
            elif protocol == 6 and len(pkt) > ip_start + ip_hdr_len + 20:
                tcp_start = ip_start + ip_hdr_len
                win_bytes.extend(pkt[tcp_start + 14:tcp_start + 16])
                urg_bytes.extend(pkt[tcp_start + 18:tcp_start + 20])
            elif protocol == 1 and len(pkt) > ip_start + ip_hdr_len + 8:
                payloads.extend(pkt[ip_start + ip_hdr_len + 8:])
        pos += incl_len

    def try_decode(raw, name):
        try:
            text = raw.decode('utf-8', errors='strict')
            p = sum(1 for c in text if c.isprintable() or c in '\r\n\t')
            if len(text) > 4 and p > len(text) * 0.7:
                results['methods'][name] = {'message': text[:200]}
                results['found'] = True
                results['findings'].append(f'{name}: {text[:60]}')
                return
        except: pass
        try:
            text = raw.decode('ascii', errors='ignore')
            for m in _re.finditer(r'[A-Za-z0-9+/]{16,}={0,2}', text):
                d = base64.b64decode(m.group()).decode('utf-8', errors='strict')
                if len(d) > 4:
                    results['methods'][name + '_b64'] = {'message': d[:200]}
                    results['found'] = True
                    results['findings'].append(f'{name} (b64): {d[:60]}')
                    return
        except: pass
        try:
            clean = ''.join(c for c in raw.decode('ascii', errors='ignore').upper()
                          if c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567')
            if len(clean) > 10:
                d = base64.b32decode(clean + '=' * ((8 - len(clean) % 8) % 8)).decode('utf-8', errors='strict')
                if len(d) > 4:
                    results['methods'][name + '_b32'] = {'message': d[:200]}
                    results['found'] = True
                    results['findings'].append(f'{name} (b32): {d[:60]}')
        except: pass

    if payloads: try_decode(bytes(payloads), 'payload')
    if ttl_bytes: try_decode(bytes(ttl_bytes), 'ip_ttl')
    if ipid_bytes: try_decode(bytes(ipid_bytes), 'ip_id')
    if win_bytes: try_decode(bytes(win_bytes), 'tcp_window')
    if urg_bytes: try_decode(bytes(urg_bytes), 'tcp_urgent')

    # Covert timing
    if len(timestamps) > 16:
        delays = [timestamps[i+1] - timestamps[i] for i in range(len(timestamps)-1)]
        median = sorted(delays)[len(delays)//2]
        tbits = ['1' if d > median else '0' for d in delays]
        if len(tbits) >= 16:
            tlen = int(''.join(tbits[:16]), 2)
            if 0 < tlen < min(500, (len(tbits) - 16) // 8):
                tb = bytearray()
                for i in range(16, 16 + tlen * 8, 8):
                    if i + 8 <= len(tbits):
                        tb.append(int(''.join(tbits[i:i+8]), 2))
                try:
                    t = tb.decode('utf-8', errors='strict')
                    if sum(1 for c in t if c.isprintable()) > len(t) * 0.7:
                        results['methods']['covert_timing'] = {'message': t[:200]}
                        results['found'] = True
                        results['findings'].append(f'Timing ({tlen}b): {t[:60]}')
                except: pass

    if b'HTTP/' in payloads:
        results['findings'].append('HTTP traffic detected')
        results['found'] = True

    results['suspicious'] = results['found']
    return results


# ============== ARCHIVE DECODERS ==============

def zip_decode(data: bytes) -> Dict[str, Any]:
    """Extract steg data from ZIP — comments, nested ZIPs, trailing data."""
    import zipfile
    results = {'found': False, 'findings': []}
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
        if zf.comment:
            results['comment'] = zf.comment.decode('utf-8', errors='replace')[:200]
            results['found'] = True
            results['findings'].append(f'ZIP comment: {results["comment"][:60]}')
        for name in zf.namelist():
            if any(s in name.lower() for s in ['secret', 'hidden', 'steg', 'flag', 'inner.zip']):
                content = zf.read(name)
                if content[:2] == b'PK':
                    inner = zipfile.ZipFile(io.BytesIO(content))
                    for iname in inner.namelist():
                        ic = inner.read(iname).decode('utf-8', errors='replace')
                        results['findings'].append(f'Nested {iname}: {ic[:100]}')
                        results['found'] = True
                    inner.close()
                else:
                    results['findings'].append(f'{name}: {content.decode("utf-8", errors="replace")[:100]}')
                    results['found'] = True
        zf.close()
        eocd = data.rfind(b'PK\x05\x06')
        if eocd >= 0:
            eocd_size = 22 + struct.unpack('<H', data[eocd+20:eocd+22])[0]
            if eocd + eocd_size < len(data):
                trailing = data[eocd + eocd_size:]
                results['findings'].append(f'Trailing ({len(trailing)}b): {trailing.decode("utf-8", errors="replace")[:60]}')
                results['found'] = True
    except Exception as e:
        results['error'] = str(e)
    results['suspicious'] = results['found']
    return results


def tar_decode(data: bytes) -> Dict[str, Any]:
    """Extract steg data from TAR — PAX headers, file contents."""
    import tarfile
    results = {'found': False, 'findings': []}
    try:
        tf = tarfile.open(fileobj=io.BytesIO(data))
        # Note: we only READ members, never extract to filesystem — no path traversal risk
        for member in tf.getmembers():
            if hasattr(member, 'pax_headers') and member.pax_headers:
                for k, v in member.pax_headers.items():
                    results['findings'].append(f'PAX {k}: {str(v)[:100]}')
                    results['found'] = True
            if member.isfile():
                f = tf.extractfile(member)
                if f:
                    results['findings'].append(f'{member.name}: {f.read(200).decode("utf-8", errors="replace")[:100]}')
        tf.close()
    except Exception as e:
        results['error'] = str(e)
    results['suspicious'] = results['found']
    return results


def gzip_decode(data: bytes) -> Dict[str, Any]:
    """Extract steg data from GZip — FEXTRA, FCOMMENT fields."""
    results = {'found': False, 'findings': []}
    if len(data) < 10 or data[:2] != b'\x1f\x8b':
        return results
    flags = data[3]
    pos = 10
    if flags & 0x04 and pos + 2 <= len(data):
        xlen = struct.unpack('<H', data[pos:pos+2])[0]
        pos += 2
        extra = data[pos:pos+xlen]
        results['findings'].append(f'FEXTRA ({xlen}b): {extra.decode("utf-8", errors="replace")[:60]}')
        results['found'] = True
        pos += xlen
    if flags & 0x08:
        end = data.index(0, pos); pos = end + 1
    if flags & 0x10:
        end = data.index(0, pos)
        comment = data[pos:end].decode('utf-8', errors='replace')
        results['findings'].append(f'FCOMMENT: {comment[:60]}')
        results['found'] = True
    results['suspicious'] = results['found']
    return results


def sqlite_decode(data: bytes) -> Dict[str, Any]:
    """Extract steg data from SQLite — hidden tables."""
    import sqlite3, tempfile, os
    results = {'found': False, 'findings': []}
    try:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        tmp.write(data); tmp.close()
        conn = sqlite3.connect(tmp.name)
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in c.fetchall()]
        results['tables'] = tables
        for table in tables:
            if any(s in table.lower() for s in ['steg', 'hidden', 'secret', 'payload', '_steg']):
                c.execute(f'SELECT * FROM "{table}" LIMIT 10')
                for row in c.fetchall():
                    results['findings'].append(f'{table}: {" | ".join(str(v)[:80] for v in row)[:150]}')
                    results['found'] = True
        conn.close(); os.unlink(tmp.name)
    except Exception as e:
        results['error'] = str(e)
    results['suspicious'] = results['found']
    return results


# ============== DOCUMENT DECODERS ==============

def pdf_decode(data: bytes) -> Dict[str, Any]:
    """Extract steg data from PDF — JS, forms, XMP, trailing data."""
    import re as _re, base64
    results = {'found': False, 'findings': []}
    if not data.startswith(b'%PDF'):
        return results
    text = data.decode('latin-1', errors='replace')
    if '/JavaScript' in text or '/JS ' in text:
        results['findings'].append('JavaScript detected')
        results['found'] = True
        for m in _re.finditer(r'/JS\s*\(([^)]+)\)', text):
            results['findings'].append(f'JS: {m.group(1)[:80]}')
    if '/AcroForm' in text:
        for m in _re.finditer(r'/V\s*\(([^)]+)\)', text):
            results['findings'].append(f'Form: {m.group(1)[:80]}')
            results['found'] = True
    eof = data.rfind(b'%%EOF')
    if eof >= 0:
        trailing = data[eof + 5:].strip()
        if trailing:
            results['findings'].append(f'Post-EOF ({len(trailing)}b): {trailing.decode("utf-8", errors="replace")[:80]}')
            results['found'] = True
    xmp = data.find(b'<x:xmpmeta')
    if xmp >= 0:
        xmp_end = data.find(b'</x:xmpmeta>', xmp)
        if xmp_end >= 0:
            xmp_data = data[xmp:xmp_end+12].decode('utf-8', errors='replace')
            for m in _re.finditer(r'<dc:description>([^<]+)</dc:description>', xmp_data):
                results['findings'].append(f'XMP desc: {m.group(1)[:80]}')
                results['found'] = True
    results['suspicious'] = results['found']
    return results


def jpeg_decode(data: bytes) -> Dict[str, Any]:
    """Extract steg data from JPEG — COM markers, APP segments."""
    results = {'found': False, 'findings': []}
    if len(data) < 2 or data[:2] != b'\xFF\xD8':
        return results
    pos = 2
    while pos < len(data) - 4:
        if data[pos] != 0xFF:
            pos += 1; continue
        marker = data[pos + 1]
        if marker == 0xFE:  # COM
            length = struct.unpack('>H', data[pos+2:pos+4])[0]
            comment = data[pos+4:pos+2+length].decode('utf-8', errors='replace')
            results['findings'].append(f'COM: {comment[:100]}')
            results['found'] = True
            pos += 2 + length
        elif 0xE0 <= marker <= 0xEF:
            length = struct.unpack('>H', data[pos+2:pos+4])[0]
            if marker not in (0xE0, 0xE1):
                seg = data[pos+4:pos+2+length]
                text = seg.decode('utf-8', errors='replace')
                if any(s in text.lower() for s in ['st3gg', 'steg', 'secret']):
                    results['findings'].append(f'APP{marker-0xE0}: {text[:80]}')
                    results['found'] = True
            pos += 2 + length
        elif marker in (0xDA, 0xD9):
            break
        else:
            try:
                length = struct.unpack('>H', data[pos+2:pos+4])[0]
                pos += 2 + length
            except:
                break
    results['suspicious'] = results['found']
    return results


def svg_decode(data: bytes) -> Dict[str, Any]:
    """Extract steg data from SVG — comments, data attributes, metadata."""
    import re as _re
    results = {'found': False, 'findings': []}
    try:
        text = data.decode('utf-8', errors='replace')
        for m in _re.finditer(r'<!--(.*?)-->', text, _re.DOTALL):
            c = m.group(1).strip()
            if len(c) > 5:
                results['findings'].append(f'Comment: {c[:80]}')
                results['found'] = True
        for m in _re.finditer(r'data-\w+="([^"]*)"', text):
            results['findings'].append(f'Data attr: {m.group(1)[:80]}')
            results['found'] = True
        meta = text.find('<metadata')
        if meta >= 0:
            meta_end = text.find('</metadata>', meta)
            if meta_end >= 0:
                for m in _re.finditer(r'<dc:description>([^<]+)</dc:description>', text[meta:meta_end]):
                    results['findings'].append(f'Description: {m.group(1)[:80]}')
                    results['found'] = True
    except Exception as e:
        results['error'] = str(e)
    results['suspicious'] = results['found']
    return results


# ============== GENERIC IMAGE LSB ==============

def generic_image_lsb_decode(data: bytes) -> Dict[str, Any]:
    """Decode LSB from any PIL-supported image (TIFF, PPM, PGM, ICO, WebP, etc).

    Handles grayscale (L), palette (P), RGB, and RGBA modes.
    Tries both 32-bit and 16-bit length prefixes for small images (ICO).
    """
    if not HAS_PIL:
        return {'error': 'PIL not available', 'found': False}
    try:
        img = Image.open(io.BytesIO(data))
        fmt = img.format or 'unknown'

        # Extract bits based on image mode
        if img.mode == 'P':
            pixels = list(img.getdata())
            bits = [p & 1 for p in pixels]
        elif img.mode in ('L', 'LA'):
            # Grayscale: 1 channel
            if img.mode == 'LA':
                img = img.convert('L')
            pixels = list(img.getdata())
            bits = [p & 1 for p in pixels]
        else:
            img = img.convert('RGBA')
            pixels = list(img.getdata())
            bits = []
            for r, g, b, a in pixels:
                for ch in [r, g, b]:
                    bits.append(ch & 1)

        if len(bits) < 16:
            return {'found': False}

        # Try both 32-bit and 16-bit length prefixes
        for prefix_bits in [32, 16]:
            if len(bits) < prefix_bits:
                continue
            length = 0
            for i in range(prefix_bits):
                length = (length << 1) | bits[i]
            if length <= 0 or length > min(10000, (len(bits) - prefix_bits) // 8):
                continue
            msg = bytearray()
            for i in range(0, length * 8, 8):
                v = 0
                for j in range(8):
                    if prefix_bits + i + j < len(bits):
                        v = (v << 1) | bits[prefix_bits + i + j]
                msg.append(v)
            decoded = msg.decode('utf-8', errors='replace')
            printable = sum(1 for c in decoded if c.isprintable() or c in '\r\n\t')
            if printable > len(decoded) * 0.5:
                return {'found': True, 'format': fmt, 'method': 'image_lsb',
                        'length': length, 'prefix_bits': prefix_bits,
                        'message': decoded[:200], 'suspicious': True,
                        'findings': [f'{fmt} LSB ({length}b, {prefix_bits}b prefix): {decoded[:80]}']}

        return {'found': False, 'format': fmt}
    except Exception as e:
        return {'error': str(e), 'found': False}


# ============== TEXT TECHNIQUE DECODERS ==============

def decode_braille(data: bytes) -> Dict[str, Any]:
    """Decode Braille pattern steganography (U+2800 block)."""
    try:
        text = data.decode('utf-8')
        braille = [c for c in text if 0x2800 <= ord(c) <= 0x28FF]
        if len(braille) < 4:
            return {'found': False}
        decoded = bytes(ord(c) - 0x2800 for c in braille).decode('utf-8', errors='replace')
        return {'found': True, 'method': 'braille', 'length': len(braille),
                'message': decoded[:200],
                'findings': [f'Braille ({len(braille)} chars): {decoded[:80]}']}
    except Exception as e:
        return {'error': str(e), 'found': False}


def decode_directional_override(data: bytes) -> Dict[str, Any]:
    """Decode directional override steganography (RLO=1, LRO=0)."""
    try:
        text = data.decode('utf-8')
        bits = []
        for ch in text:
            if ch == '\u202E': bits.append('1')
            elif ch == '\u202D': bits.append('0')
        if len(bits) < 16:
            return {'found': False}
        length = int(''.join(bits[:16]), 2)
        if length <= 0 or length > (len(bits) - 16) // 8:
            return {'found': False}
        msg = bytearray()
        for i in range(16, 16 + length * 8, 8):
            if i + 8 <= len(bits):
                msg.append(int(''.join(bits[i:i+8]), 2))
        decoded = msg.decode('utf-8', errors='replace')
        return {'found': True, 'method': 'directional', 'length': length,
                'message': decoded[:200],
                'findings': [f'Bidi decode ({length}b): {decoded[:80]}']}
    except Exception as e:
        return {'error': str(e), 'found': False}


def decode_hangul_filler(data: bytes) -> Dict[str, Any]:
    """Decode Hangul filler steganography (U+3164=1, space=0).

    Handles partial messages where cover text has fewer spaces than payload needs.
    """
    try:
        text = data.decode('utf-8')
        hf_count = text.count('\u3164')
        if hf_count == 0:
            return {'found': False}
        bits = []
        for ch in text:
            if ch == '\u3164': bits.append('1')
            elif ch == ' ': bits.append('0')
        if len(bits) < 16:
            return {'found': False}
        length = int(''.join(bits[:16]), 2)
        if length <= 0 or length > 5000:
            return {'found': False}
        # Decode as many bytes as we have bits for (may be partial)
        available_bytes = (len(bits) - 16) // 8
        decode_bytes = min(length, available_bytes)
        msg = bytearray()
        for i in range(16, 16 + decode_bytes * 8, 8):
            if i + 8 <= len(bits):
                msg.append(int(''.join(bits[i:i+8]), 2))
        decoded = msg.decode('utf-8', errors='replace')
        partial = decode_bytes < length
        return {'found': True, 'method': 'hangul_filler',
                'length': length, 'decoded_bytes': decode_bytes,
                'partial': partial, 'message': decoded[:200],
                'findings': [f'Hangul ({decode_bytes}/{length}b{"*" if partial else ""}): {decoded[:80]}']}
    except Exception as e:
        return {'error': str(e), 'found': False}


def decode_math_alphanumeric(data: bytes) -> Dict[str, Any]:
    """Decode math bold substitution (bold=1, normal=0)."""
    try:
        text = data.decode('utf-8')
        bits = []
        for ch in text:
            o = ord(ch)
            if 0x1D400 <= o <= 0x1D419 or 0x1D41A <= o <= 0x1D433:
                bits.append('1')
            elif ch.isascii() and ch.isalpha():
                bits.append('0')
        if len(bits) < 16:
            return {'found': False}
        length = int(''.join(bits[:16]), 2)
        if length <= 0 or length > (len(bits) - 16) // 8:
            return {'found': False}
        msg = bytearray()
        for i in range(16, 16 + length * 8, 8):
            if i + 8 <= len(bits):
                msg.append(int(''.join(bits[i:i+8]), 2))
        decoded = msg.decode('utf-8', errors='replace')
        return {'found': True, 'method': 'math_alpha', 'length': length,
                'message': decoded[:200],
                'findings': [f'Math alpha ({length}b): {decoded[:80]}']}
    except Exception as e:
        return {'error': str(e), 'found': False}


def decode_emoji_skin_tone(data: bytes) -> Dict[str, Any]:
    """Decode emoji skin tone steganography (4 tones = 2 bits each)."""
    try:
        text = data.decode('utf-8')
        TONES = {'\U0001F3FB': 0, '\U0001F3FC': 1, '\U0001F3FE': 2, '\U0001F3FF': 3}
        pairs = [TONES[c] for c in text if c in TONES]
        if len(pairs) < 4:
            return {'found': False}
        msg = bytearray()
        for i in range(0, len(pairs) - 3, 4):
            msg.append((pairs[i] << 6) | (pairs[i+1] << 4) | (pairs[i+2] << 2) | pairs[i+3])
        decoded = msg.decode('utf-8', errors='replace')
        printable = sum(1 for c in decoded if c.isprintable())
        if printable > len(decoded) * 0.5:
            return {'found': True, 'method': 'emoji_skin_tone', 'length': len(msg),
                    'message': decoded[:200],
                    'findings': [f'Skin tone ({len(msg)}b): {decoded[:80]}']}
        return {'found': False}
    except Exception as e:
        return {'error': str(e), 'found': False}


# ============== ADVANCED STEGANALYSIS ==============

def rs_analysis(data: bytes) -> Dict[str, Any]:
    """RS (Regular-Singular) Analysis — gold standard for LSB detection.

    Divides pixels into pairs and measures how LSB flipping affects smoothness.
    Clean images: flipping increases/decreases regularity equally.
    Stego images: balance is skewed because LSBs already carry data.
    More accurate than chi-square for low embedding rates.
    """
    if not HAS_PIL or not HAS_NUMPY:
        return {'error': 'PIL/numpy required', 'found': False}
    try:
        img = Image.open(io.BytesIO(data)).convert('RGB')
        pixels = np.array(img, dtype=np.int16)
        results = {}
        for ch_idx, ch_name in enumerate(['Red', 'Green', 'Blue']):
            ch = pixels[:, :, ch_idx].flatten()
            n = len(ch) // 2
            p1, p2 = ch[:n*2:2], ch[1:n*2:2]
            d_orig = float(np.mean(np.abs(p1 - p2)))
            d_flip = float(np.mean(np.abs((p1 ^ 1) - p2)))
            rs_ratio = d_flip / d_orig if d_orig > 0 else 1.0
            est_rate = max(0, min(1, (rs_ratio - 1.0) * 2))
            results[ch_name] = {
                'smoothness_original': round(d_orig, 4),
                'smoothness_flipped': round(d_flip, 4),
                'rs_ratio': round(rs_ratio, 4),
                'estimated_embedding_rate': round(est_rate, 4),
                'suspicious': rs_ratio > 1.02 or est_rate > 0.05,
            }
        rate = max(r['estimated_embedding_rate'] for r in results.values())
        return {
            'found': True, 'channels': results,
            'overall_embedding_rate': round(rate, 4),
            'suspicious': any(r['suspicious'] for r in results.values()),
            'interpretation': f"RS analysis: {rate:.1%} estimated embedding. " + (
                "HIGH probability of LSB steg." if rate > 0.1
                else "MODERATE indicators." if rate > 0.03
                else "LOW — likely clean."),
            'method': 'rs_analysis'
        }
    except Exception as e:
        return {'error': str(e), 'found': False}


def sample_pairs_analysis(data: bytes) -> Dict[str, Any]:
    """Sample Pairs Analysis (SPA) — detects LSB by pixel pair statistics.

    Examines how adjacent pixel pairs relate when LSBs are considered.
    Clean images have predictable pair-type ratios. LSB embedding disrupts them.
    Complementary to RS analysis — catches different patterns.
    """
    if not HAS_PIL or not HAS_NUMPY:
        return {'error': 'PIL/numpy required', 'found': False}
    try:
        img = Image.open(io.BytesIO(data)).convert('RGB')
        pixels = np.array(img, dtype=np.int16)
        results = {}
        for ch_idx, ch_name in enumerate(['Red', 'Green', 'Blue']):
            ch = pixels[:, :, ch_idx].flatten()
            n = len(ch) - 1
            p1, p2 = ch[:n], ch[1:n+1]
            h1, h2 = p1 >> 1, p2 >> 1
            x = int(np.sum(h1 == h2))
            y = int(np.sum(np.abs(h1 - h2) == 1))
            total = float(n)
            x_r, y_r = x/total, y/total
            spa = abs(x_r - y_r) / (x_r + y_r) if (x_r + y_r) > 0 else 0
            est = max(0, min(1, 1.0 - spa * 3))
            results[ch_name] = {
                'x_pairs': x, 'y_pairs': y, 'z_pairs': n - x - y,
                'spa_ratio': round(spa, 4),
                'estimated_embedding_rate': round(est, 4),
                'suspicious': spa < 0.1,
            }
        rate = max(r['estimated_embedding_rate'] for r in results.values())
        return {
            'found': True, 'channels': results,
            'overall_embedding_rate': round(rate, 4),
            'suspicious': any(r['suspicious'] for r in results.values()),
            'interpretation': f"SPA: {rate:.1%} estimated embedding. " + (
                "HIGH probability." if rate > 0.5
                else "MODERATE." if rate > 0.2
                else "LOW."),
            'method': 'sample_pairs_analysis'
        }
    except Exception as e:
        return {'error': str(e), 'found': False}


# ============== REGISTER ALL TOOLS ==============

def _register_all_tools():
    """Register ALL analysis and decode tools."""
    TOOL_REGISTRY.register('detect_homoglyph_steg', detect_homoglyph_steg)
    TOOL_REGISTRY.register('detect_variation_selector_steg', detect_variation_selector_steg)
    TOOL_REGISTRY.register('detect_combining_mark_steg', detect_combining_mark_steg)
    TOOL_REGISTRY.register('detect_confusable_whitespace', detect_confusable_whitespace)
    TOOL_REGISTRY.register('detect_emoji_steg', detect_emoji_steg)
    TOOL_REGISTRY.register('detect_capitalization_steg', detect_capitalization_steg)
    # Advanced steganalysis
    TOOL_REGISTRY.register('rs_analysis', rs_analysis)
    TOOL_REGISTRY.register('sample_pairs_analysis', sample_pairs_analysis)
    TOOL_REGISTRY.register('audio_lsb_decode', audio_lsb_decode)
    TOOL_REGISTRY.register('pcap_decode', pcap_decode)
    TOOL_REGISTRY.register('zip_decode', zip_decode)
    TOOL_REGISTRY.register('tar_decode', tar_decode)
    TOOL_REGISTRY.register('gzip_decode', gzip_decode)
    TOOL_REGISTRY.register('sqlite_decode', sqlite_decode)
    TOOL_REGISTRY.register('pdf_decode', pdf_decode)
    TOOL_REGISTRY.register('jpeg_decode', jpeg_decode)
    TOOL_REGISTRY.register('svg_decode', svg_decode)
    TOOL_REGISTRY.register('generic_image_lsb_decode', generic_image_lsb_decode)
    TOOL_REGISTRY.register('decode_braille', decode_braille)
    TOOL_REGISTRY.register('decode_directional_override', decode_directional_override)
    TOOL_REGISTRY.register('decode_hangul_filler', decode_hangul_filler)
    TOOL_REGISTRY.register('decode_math_alphanumeric', decode_math_alphanumeric)
    TOOL_REGISTRY.register('decode_emoji_skin_tone', decode_emoji_skin_tone)

_register_all_tools()
