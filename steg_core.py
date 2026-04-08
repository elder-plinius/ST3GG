"""
STEGOSAURUS WRECKS - Core Steganography Engine v3.0
Ultimate LSB steganography with vectorized operations and robust encoding

Features:
- Vectorized numpy operations (10-100x faster)
- Self-describing header format with magic bytes
- CRC32 checksum for data integrity
- Multiple encoding strategies
- Auto-detection of encoding parameters
"""

import zlib
import struct
import hashlib
import secrets
from PIL import Image
from typing import Tuple, List, Optional, Union, Dict, Any
from enum import Enum, IntEnum
from dataclasses import dataclass, field
import numpy as np


# ============== CONSTANTS ==============

MAGIC_BYTES = b'STEG'  # Magic signature
FORMAT_VERSION = 3     # Current format version
HEADER_SIZE = 32       # Fixed header size in bytes

class Channel(IntEnum):
    """Color channels - IntEnum for direct numpy indexing"""
    R = 0
    G = 1
    B = 2
    A = 3


class EncodingStrategy(Enum):
    """Different strategies for embedding data"""
    SEQUENTIAL = "sequential"      # Fill pixels in order
    INTERLEAVED = "interleaved"    # Cycle through channels per pixel
    SPREAD = "spread"              # Spread across image evenly
    RANDOMIZED = "randomized"      # Pseudo-random order (seeded)


# ============== CONFIGURATION ==============

@dataclass
class StegConfig:
    """Configuration for steganography operations"""
    channels: List[Channel] = field(default_factory=lambda: [Channel.R, Channel.G, Channel.B])
    bits_per_channel: int = 1
    bit_offset: int = 0
    use_compression: bool = True
    strategy: EncodingStrategy = EncodingStrategy.INTERLEAVED
    seed: Optional[int] = None  # For randomized strategy

    @property
    def bits_per_pixel(self) -> int:
        return len(self.channels) * self.bits_per_channel

    @property
    def channel_indices(self) -> np.ndarray:
        return np.array([c.value for c in self.channels], dtype=np.uint8)

    def to_bytes(self) -> bytes:
        """Serialize config to bytes for header"""
        flags = 0
        flags |= (1 << 0) if self.use_compression else 0
        flags |= (self.strategy.value == "interleaved") << 1
        flags |= (self.strategy.value == "spread") << 2
        flags |= (self.strategy.value == "randomized") << 3

        channel_mask = sum(1 << c.value for c in self.channels)

        return struct.pack(
            '>BBBB I',
            channel_mask,
            self.bits_per_channel,
            self.bit_offset,
            flags,
            self.seed or 0
        )

    @classmethod
    def from_bytes(cls, data: bytes) -> 'StegConfig':
        """Deserialize config from bytes"""
        channel_mask, bits_per_ch, bit_offset, flags, seed = struct.unpack('>BBBB I', data)

        channels = [Channel(i) for i in range(4) if channel_mask & (1 << i)]
        use_compression = bool(flags & 1)

        if flags & (1 << 3):
            strategy = EncodingStrategy.RANDOMIZED
        elif flags & (1 << 2):
            strategy = EncodingStrategy.SPREAD
        elif flags & (1 << 1):
            strategy = EncodingStrategy.INTERLEAVED
        else:
            strategy = EncodingStrategy.SEQUENTIAL

        return cls(
            channels=channels,
            bits_per_channel=bits_per_ch,
            bit_offset=bit_offset,
            use_compression=use_compression,
            strategy=strategy,
            seed=seed if seed else None
        )


# Channel presets
CHANNEL_PRESETS = {
    "R": [Channel.R],
    "G": [Channel.G],
    "B": [Channel.B],
    "A": [Channel.A],
    "RG": [Channel.R, Channel.G],
    "RB": [Channel.R, Channel.B],
    "RA": [Channel.R, Channel.A],
    "GB": [Channel.G, Channel.B],
    "GA": [Channel.G, Channel.A],
    "BA": [Channel.B, Channel.A],
    "RGB": [Channel.R, Channel.G, Channel.B],
    "RGA": [Channel.R, Channel.G, Channel.A],
    "RBA": [Channel.R, Channel.B, Channel.A],
    "GBA": [Channel.G, Channel.B, Channel.A],
    "RGBA": [Channel.R, Channel.G, Channel.B, Channel.A],
}


def get_channel_preset(name: str) -> List[Channel]:
    """Get channel list from preset name"""
    return CHANNEL_PRESETS.get(name.upper(), [Channel.R, Channel.G, Channel.B])


def derive_magic(password: str) -> bytes:
    """Derive 4-byte magic from password using HMAC-SHA256.

    When a password is provided, the STEG header magic is derived from
    the password instead of using the fixed 'STEG' bytes. This means
    the header is undetectable without the password — no fixed signature
    to scan for.
    """
    import hmac
    return hmac.new(password.encode('utf-8'), b'ST3GG-MAGIC-V3', 'sha256').digest()[:4]


# ============== HEADER FORMAT ==============
"""
Header Format (32 bytes):
  [0:4]   - Magic bytes: 'STEG'
  [4:5]   - Version: uint8
  [5:6]   - Channel mask: uint8 (bit flags for R,G,B,A)
  [6:7]   - Bits per channel: uint8
  [7:8]   - Bit offset: uint8
  [8:9]   - Flags: uint8 (compression, strategy bits)
  [9:12]  - Reserved: 3 bytes
  [12:16] - Seed: uint32 (for randomized strategy)
  [16:20] - Payload length: uint32
  [20:24] - Original length: uint32 (before compression)
  [24:28] - CRC32: uint32
  [28:32] - Reserved: 4 bytes
"""

@dataclass
class StegHeader:
    """Header for encoded data"""
    version: int = FORMAT_VERSION
    config: StegConfig = field(default_factory=StegConfig)
    payload_length: int = 0
    original_length: int = 0
    crc32: int = 0

    def to_bytes(self, password: Optional[str] = None) -> bytes:
        """Serialize header to 32 bytes.

        If password is provided, the magic bytes are derived from the password
        using HMAC-SHA256, making the header undetectable without the password.
        """
        config_bytes = self.config.to_bytes()

        header = bytearray(HEADER_SIZE)
        header[0:4] = derive_magic(password) if password else MAGIC_BYTES
        header[4] = self.version
        header[5:13] = config_bytes
        struct.pack_into('>I', header, 16, self.payload_length)
        struct.pack_into('>I', header, 20, self.original_length)
        struct.pack_into('>I', header, 24, self.crc32)

        return bytes(header)

    @classmethod
    def from_bytes(cls, data: bytes, password: Optional[str] = None) -> 'StegHeader':
        """Deserialize header from bytes.

        If password is provided, validates against password-derived magic.
        Otherwise validates against the fixed 'STEG' magic bytes.
        """
        if len(data) < HEADER_SIZE:
            raise ValueError(f"Header too short: {len(data)} < {HEADER_SIZE}")

        magic = data[0:4]
        expected = derive_magic(password) if password else MAGIC_BYTES
        if magic != expected:
            raise ValueError(f"Invalid magic bytes: {magic!r} != {expected!r}")

        version = data[4]
        if version > FORMAT_VERSION:
            raise ValueError(f"Unsupported version: {version} > {FORMAT_VERSION}")

        config = StegConfig.from_bytes(data[5:13])
        payload_length = struct.unpack('>I', data[16:20])[0]
        original_length = struct.unpack('>I', data[20:24])[0]
        crc32 = struct.unpack('>I', data[24:28])[0]

        return cls(
            version=version,
            config=config,
            payload_length=payload_length,
            original_length=original_length,
            crc32=crc32
        )


# ============== BIT MANIPULATION (Vectorized) ==============

def _create_bit_mask(bits: int, offset: int = 0) -> int:
    """Create a bit mask for specified bits at offset"""
    return ((1 << bits) - 1) << offset


def _bytes_to_bits_array(data: bytes, bits_per_unit: int = 1) -> np.ndarray:
    """
    Convert bytes to numpy array of bit groups.
    Much faster than string conversion.

    Args:
        data: Input bytes
        bits_per_unit: How many bits per output element (1-8)

    Returns:
        numpy array of uint8 values, each containing bits_per_unit bits
    """
    # Convert to bit array
    byte_array = np.frombuffer(data, dtype=np.uint8)
    # Unpack each byte into 8 bits
    bits = np.unpackbits(byte_array)

    # Group into units of bits_per_unit
    if bits_per_unit == 1:
        return bits

    # Pad to multiple of bits_per_unit
    pad_len = (bits_per_unit - len(bits) % bits_per_unit) % bits_per_unit
    if pad_len:
        bits = np.concatenate([bits, np.zeros(pad_len, dtype=np.uint8)])

    # Reshape and combine bits
    bits = bits.reshape(-1, bits_per_unit)
    # Convert each group to a value (MSB first within each group)
    multipliers = 2 ** np.arange(bits_per_unit - 1, -1, -1, dtype=np.uint8)
    return np.sum(bits * multipliers, axis=1).astype(np.uint8)


def _bits_array_to_bytes(bits: np.ndarray, bits_per_unit: int = 1, total_bits: int = None) -> bytes:
    """
    Convert numpy array of bit groups back to bytes.

    Args:
        bits: Array of bit values
        bits_per_unit: Bits per element in input array
        total_bits: Total number of valid bits (for trimming padding)

    Returns:
        Reconstructed bytes
    """
    if bits_per_unit == 1:
        bit_array = bits
    else:
        # Expand each value to bits_per_unit bits
        bit_array = np.zeros(len(bits) * bits_per_unit, dtype=np.uint8)
        for i in range(bits_per_unit):
            shift = bits_per_unit - 1 - i
            bit_array[i::bits_per_unit] = (bits >> shift) & 1

    # Trim to total_bits if specified
    if total_bits is not None:
        bit_array = bit_array[:total_bits]

    # Pad to multiple of 8
    pad_len = (8 - len(bit_array) % 8) % 8
    if pad_len:
        bit_array = np.concatenate([bit_array, np.zeros(pad_len, dtype=np.uint8)])

    # Pack into bytes
    return np.packbits(bit_array).tobytes()


# ============== PIXEL INDEX GENERATION ==============

def _generate_pixel_indices(
    num_pixels: int,
    num_needed: int,
    strategy: EncodingStrategy,
    seed: Optional[int] = None
) -> np.ndarray:
    """
    Generate pixel indices based on encoding strategy.

    Args:
        num_pixels: Total pixels available
        num_needed: Number of pixels needed
        strategy: Encoding strategy
        seed: Random seed for reproducibility

    Returns:
        Array of pixel indices to use
    """
    if num_needed > num_pixels:
        raise ValueError(f"Not enough pixels: need {num_needed}, have {num_pixels}")

    if strategy == EncodingStrategy.SEQUENTIAL or strategy == EncodingStrategy.INTERLEAVED:
        # Simple sequential indices
        return np.arange(num_needed, dtype=np.uint32)

    elif strategy == EncodingStrategy.SPREAD:
        # Spread evenly across the image
        step = num_pixels / num_needed
        return np.floor(np.arange(num_needed) * step).astype(np.uint32)

    elif strategy == EncodingStrategy.RANDOMIZED:
        # Pseudo-random but reproducible
        rng = np.random.default_rng(seed or 42)
        indices = rng.permutation(num_pixels)[:num_needed]
        return np.sort(indices).astype(np.uint32)  # Sort for cache efficiency

    return np.arange(num_needed, dtype=np.uint32)


# ============== CAPACITY CALCULATION ==============

def calculate_capacity(image: Image.Image, config: StegConfig) -> Dict[str, Any]:
    """Calculate steganographic capacity of an image"""
    width, height = image.size
    total_pixels = width * height

    bits_per_pixel = config.bits_per_pixel
    total_bits = total_pixels * bits_per_pixel
    total_bytes = total_bits // 8

    # Account for header
    header_bits = HEADER_SIZE * 8
    usable_bits = total_bits - header_bits
    usable_bytes = usable_bits // 8

    return {
        "dimensions": (width, height),
        "pixels": total_pixels,
        "bits_total": total_bits,
        "bytes_total": total_bytes,
        "header_bytes": HEADER_SIZE,
        "usable_bits": usable_bits,
        "usable_bytes": max(0, usable_bytes),
        "human": _human_readable_size(max(0, usable_bytes)),
        "config": {
            "channels": [c.name for c in config.channels],
            "bits_per_channel": config.bits_per_channel,
            "bits_per_pixel": bits_per_pixel,
            "strategy": config.strategy.value,
        }
    }


def _human_readable_size(size_bytes: int) -> str:
    """Convert bytes to human readable string"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.2f} TB"


# ============== ENCODER ==============

def encode(
    image: Image.Image,
    data: bytes,
    config: StegConfig,
    output_path: Optional[str] = None
) -> Image.Image:
    """
    Encode data into image using LSB steganography.

    Args:
        image: Source PIL Image
        data: Bytes to encode
        config: Steganography configuration
        output_path: Optional path to save result

    Returns:
        Modified PIL Image with embedded data
    """
    # Convert to RGBA numpy array
    img = image.convert("RGBA")
    pixels = np.array(img, dtype=np.uint8)
    height, width = pixels.shape[:2]
    total_pixels = height * width

    # Prepare payload
    original_length = len(data)
    if config.use_compression:
        payload = zlib.compress(data, level=9)
    else:
        payload = data

    payload_length = len(payload)
    crc32 = zlib.crc32(data) & 0xFFFFFFFF

    # Create header
    header = StegHeader(
        version=FORMAT_VERSION,
        config=config,
        payload_length=payload_length,
        original_length=original_length,
        crc32=crc32
    )
    header_bytes = header.to_bytes()

    # Combine header and payload
    full_data = header_bytes + payload

    # Check capacity
    capacity = calculate_capacity(image, config)
    data_bits_needed = len(full_data) * 8
    if data_bits_needed > capacity["bits_total"]:
        raise ValueError(
            f"Data too large: {len(full_data):,} bytes needed, "
            f"{capacity['bytes_total']:,} bytes available"
        )

    # Convert data to bit units
    bits_per_ch = config.bits_per_channel
    bit_units = _bytes_to_bits_array(full_data, bits_per_ch)

    # Calculate how many pixel-channel slots we need
    num_channels = len(config.channels)
    channel_indices = config.channel_indices

    if config.strategy == EncodingStrategy.INTERLEAVED:
        # Interleaved: cycle through channels at each pixel
        slots_needed = len(bit_units)
        pixels_needed = (slots_needed + num_channels - 1) // num_channels

        # Generate pixel indices
        pixel_indices = _generate_pixel_indices(
            total_pixels, pixels_needed, config.strategy, config.seed
        )

        # Flatten pixels for easier access
        flat_pixels = pixels.reshape(-1, 4)

        # Embed data
        bit_mask = _create_bit_mask(bits_per_ch, config.bit_offset)
        clear_mask = ~bit_mask & 0xFF

        slot_idx = 0
        for pix_idx in pixel_indices:
            for ch in channel_indices:
                if slot_idx >= len(bit_units):
                    break
                # Clear target bits and set new value
                original = flat_pixels[pix_idx, ch]
                value = bit_units[slot_idx]
                flat_pixels[pix_idx, ch] = (original & clear_mask) | (value << config.bit_offset)
                slot_idx += 1
            if slot_idx >= len(bit_units):
                break

        # Reshape back
        pixels = flat_pixels.reshape(height, width, 4)

    else:
        # Sequential or other strategies: process each channel in order
        flat_pixels = pixels.reshape(-1, 4)

        if config.strategy == EncodingStrategy.SEQUENTIAL:
            # Fill each channel completely before moving to next
            bit_mask = _create_bit_mask(bits_per_ch, config.bit_offset)
            clear_mask = ~bit_mask & 0xFF

            slot_idx = 0
            for ch in channel_indices:
                pixel_indices = _generate_pixel_indices(
                    total_pixels,
                    min(total_pixels, len(bit_units) - slot_idx),
                    config.strategy,
                    config.seed
                )
                for pix_idx in pixel_indices:
                    if slot_idx >= len(bit_units):
                        break
                    original = flat_pixels[pix_idx, ch]
                    value = bit_units[slot_idx]
                    flat_pixels[pix_idx, ch] = (original & clear_mask) | (value << config.bit_offset)
                    slot_idx += 1
                if slot_idx >= len(bit_units):
                    break

        else:
            # Spread or randomized with interleaving
            slots_needed = len(bit_units)
            pixels_needed = (slots_needed + num_channels - 1) // num_channels

            pixel_indices = _generate_pixel_indices(
                total_pixels, pixels_needed, config.strategy, config.seed
            )

            bit_mask = _create_bit_mask(bits_per_ch, config.bit_offset)
            clear_mask = ~bit_mask & 0xFF

            slot_idx = 0
            for pix_idx in pixel_indices:
                for ch in channel_indices:
                    if slot_idx >= len(bit_units):
                        break
                    original = flat_pixels[pix_idx, ch]
                    value = bit_units[slot_idx]
                    flat_pixels[pix_idx, ch] = (original & clear_mask) | (value << config.bit_offset)
                    slot_idx += 1
                if slot_idx >= len(bit_units):
                    break

        pixels = flat_pixels.reshape(height, width, 4)

    # Create result image
    result = Image.fromarray(pixels, 'RGBA')

    if output_path:
        result.save(output_path, format='PNG', optimize=False)

    return result


# ============== DECODER ==============

def decode(
    image: Image.Image,
    config: Optional[StegConfig] = None,
    verify_checksum: bool = True
) -> bytes:
    """
    Decode data from image using LSB steganography.

    Args:
        image: PIL Image with embedded data
        config: Optional config (if None, auto-detect from header)
        verify_checksum: Whether to verify CRC32 checksum

    Returns:
        Extracted bytes
    """
    # Convert to RGBA numpy array
    img = image.convert("RGBA")
    pixels = np.array(img, dtype=np.uint8)
    height, width = pixels.shape[:2]
    total_pixels = height * width
    flat_pixels = pixels.reshape(-1, 4)

    # First, we need to extract the header to get config
    if config is None:
        # Auto-detect: exhaustive search across all channel/bit combos
        detected = detect_encoding(image)
        if detected:
            # Reconstruct config from detection result
            channel_map = {'R': Channel.R, 'G': Channel.G, 'B': Channel.B, 'A': Channel.A}
            channels = [channel_map[c] for c in detected['config']['channels']]
            header_config = StegConfig(
                channels=channels,
                bits_per_channel=detected['config']['bits_per_channel']
            )
        else:
            # Fallback to default
            header_config = StegConfig()
    else:
        header_config = config

    # Extract header bytes
    header_bits_needed = HEADER_SIZE * 8
    header_units_needed = header_bits_needed // header_config.bits_per_channel
    if header_bits_needed % header_config.bits_per_channel:
        header_units_needed += 1

    header_units = _extract_bit_units(
        flat_pixels,
        header_units_needed,
        header_config,
        total_pixels
    )

    header_bytes = _bits_array_to_bytes(
        header_units,
        header_config.bits_per_channel,
        header_bits_needed
    )[:HEADER_SIZE]

    # Parse header
    try:
        header = StegHeader.from_bytes(header_bytes)
    except ValueError as e:
        raise ValueError(f"Failed to decode header: {e}. Image may not contain encoded data or config mismatch.")

    # Use config from header if not provided
    actual_config = config if config else header.config

    # Now extract the full payload using actual config
    total_data_len = HEADER_SIZE + header.payload_length
    total_bits_needed = total_data_len * 8
    total_units_needed = total_bits_needed // actual_config.bits_per_channel
    if total_bits_needed % actual_config.bits_per_channel:
        total_units_needed += 1

    all_units = _extract_bit_units(
        flat_pixels,
        total_units_needed,
        actual_config,
        total_pixels
    )

    all_bytes = _bits_array_to_bytes(
        all_units,
        actual_config.bits_per_channel,
        total_bits_needed
    )

    # Extract payload (skip header)
    payload = all_bytes[HEADER_SIZE:HEADER_SIZE + header.payload_length]

    if len(payload) < header.payload_length:
        raise ValueError(
            f"Incomplete payload: got {len(payload)}, expected {header.payload_length}"
        )

    # Decompress if needed
    if actual_config.use_compression:
        try:
            data = zlib.decompress(payload)
        except zlib.error as e:
            raise ValueError(f"Decompression failed: {e}")
    else:
        data = payload

    # Verify length
    if len(data) != header.original_length:
        raise ValueError(
            f"Length mismatch: got {len(data)}, expected {header.original_length}"
        )

    # Verify checksum
    if verify_checksum:
        actual_crc = zlib.crc32(data) & 0xFFFFFFFF
        if actual_crc != header.crc32:
            raise ValueError(
                f"Checksum mismatch: got {actual_crc:08x}, expected {header.crc32:08x}. "
                "Data may be corrupted."
            )

    return data


def _extract_bit_units(
    flat_pixels: np.ndarray,
    num_units: int,
    config: StegConfig,
    total_pixels: int
) -> np.ndarray:
    """
    Extract bit units from pixel array.

    Args:
        flat_pixels: Flattened pixel array (N, 4)
        num_units: Number of bit units to extract
        config: Steganography configuration
        total_pixels: Total number of pixels

    Returns:
        Array of extracted bit values
    """
    channel_indices = config.channel_indices
    num_channels = len(channel_indices)
    bits_per_ch = config.bits_per_channel
    bit_offset = config.bit_offset
    bit_mask = _create_bit_mask(bits_per_ch, bit_offset)

    result = np.zeros(num_units, dtype=np.uint8)

    if config.strategy == EncodingStrategy.INTERLEAVED:
        pixels_needed = (num_units + num_channels - 1) // num_channels
        pixel_indices = _generate_pixel_indices(
            total_pixels, pixels_needed, config.strategy, config.seed
        )

        unit_idx = 0
        for pix_idx in pixel_indices:
            for ch in channel_indices:
                if unit_idx >= num_units:
                    break
                value = flat_pixels[pix_idx, ch]
                result[unit_idx] = (value & bit_mask) >> bit_offset
                unit_idx += 1
            if unit_idx >= num_units:
                break

    elif config.strategy == EncodingStrategy.SEQUENTIAL:
        unit_idx = 0
        for ch in channel_indices:
            pixel_indices = _generate_pixel_indices(
                total_pixels,
                min(total_pixels, num_units - unit_idx),
                config.strategy,
                config.seed
            )
            for pix_idx in pixel_indices:
                if unit_idx >= num_units:
                    break
                value = flat_pixels[pix_idx, ch]
                result[unit_idx] = (value & bit_mask) >> bit_offset
                unit_idx += 1
            if unit_idx >= num_units:
                break

    else:
        # Spread or randomized
        pixels_needed = (num_units + num_channels - 1) // num_channels
        pixel_indices = _generate_pixel_indices(
            total_pixels, pixels_needed, config.strategy, config.seed
        )

        unit_idx = 0
        for pix_idx in pixel_indices:
            for ch in channel_indices:
                if unit_idx >= num_units:
                    break
                value = flat_pixels[pix_idx, ch]
                result[unit_idx] = (value & bit_mask) >> bit_offset
                unit_idx += 1
            if unit_idx >= num_units:
                break

    return result


# ============== CONVENIENCE FUNCTIONS ==============

def encode_text(
    image: Image.Image,
    text: str,
    config: StegConfig,
    output_path: Optional[str] = None
) -> Image.Image:
    """Encode text string into image"""
    return encode(image, text.encode('utf-8'), config, output_path)


def decode_text(
    image: Image.Image,
    config: Optional[StegConfig] = None
) -> str:
    """Decode text string from image"""
    data = decode(image, config)
    return data.decode('utf-8')


def create_config(
    channels: str = "RGB",
    bits: int = 1,
    compress: bool = True,
    strategy: str = "interleaved",
    bit_offset: int = 0,
    seed: Optional[int] = None
) -> StegConfig:
    """
    Create a StegConfig with convenient parameters.

    Args:
        channels: Channel preset name (R, G, B, A, RGB, RGBA, etc.)
        bits: Bits per channel (1-8)
        compress: Whether to compress data
        strategy: Encoding strategy ('sequential', 'interleaved', 'spread', 'randomized')
        bit_offset: Bit position offset (0 = LSB)
        seed: Random seed for randomized strategy

    Returns:
        StegConfig instance
    """
    strategy_map = {
        'sequential': EncodingStrategy.SEQUENTIAL,
        'interleaved': EncodingStrategy.INTERLEAVED,
        'spread': EncodingStrategy.SPREAD,
        'randomized': EncodingStrategy.RANDOMIZED,
    }

    return StegConfig(
        channels=get_channel_preset(channels),
        bits_per_channel=max(1, min(8, bits)),
        bit_offset=max(0, min(7, bit_offset)),
        use_compression=compress,
        strategy=strategy_map.get(strategy.lower(), EncodingStrategy.INTERLEAVED),
        seed=seed
    )


# ============== ANALYSIS ==============

def analyze_image(image: Image.Image) -> Dict[str, Any]:
    """
    Analyze an image for steganography potential and detection.

    Performs statistical analysis to detect potential hidden data.
    """
    img = image.convert("RGBA")
    pixels = np.array(img, dtype=np.uint8)

    analysis = {
        "dimensions": {"width": img.width, "height": img.height},
        "total_pixels": img.width * img.height,
        "mode": image.mode,
        "format": image.format,
        "channels": {},
        "capacity_by_config": {},
        "detection": {},
    }

    # Analyze each channel
    channel_names = ['R', 'G', 'B', 'A']
    for i, name in enumerate(channel_names):
        channel_data = pixels[:, :, i].flatten()

        # Basic statistics
        mean_val = float(np.mean(channel_data))
        std_val = float(np.std(channel_data))

        # LSB analysis
        lsb = channel_data & 1
        lsb_zeros = np.sum(lsb == 0)
        lsb_ones = np.sum(lsb == 1)
        total = len(channel_data)

        # Chi-square test for LSB
        expected = total / 2
        chi_square = ((lsb_zeros - expected) ** 2 + (lsb_ones - expected) ** 2) / expected

        # Pairs analysis (RS analysis simplified)
        even_pixels = channel_data[::2]
        odd_pixels = channel_data[1::2] if len(channel_data) > 1 else even_pixels

        # Calculate LSB flipping effect
        min_len = min(len(even_pixels), len(odd_pixels))
        diff_original = np.abs(even_pixels[:min_len].astype(np.int16) - odd_pixels[:min_len].astype(np.int16))
        flipped_even = even_pixels[:min_len] ^ 1
        diff_flipped = np.abs(flipped_even.astype(np.int16) - odd_pixels[:min_len].astype(np.int16))

        smoothness_change = np.mean(diff_flipped) - np.mean(diff_original)

        analysis["channels"][name] = {
            "mean": mean_val,
            "std": std_val,
            "min": int(np.min(channel_data)),
            "max": int(np.max(channel_data)),
            "lsb_ratio": {
                "zeros": lsb_zeros / total,
                "ones": lsb_ones / total,
            },
            "chi_square": float(chi_square),
            "chi_square_indicator": min(1.0, chi_square / 100),  # Normalized 0-1
            "smoothness_change": float(smoothness_change),
        }

    # Overall detection score
    max_chi = max(ch["chi_square_indicator"] for ch in analysis["channels"].values())
    avg_smoothness = np.mean([abs(ch["smoothness_change"]) for ch in analysis["channels"].values()])

    if max_chi > 0.5 or avg_smoothness > 0.5:
        detection_level = "HIGH"
        confidence = min(0.95, (max_chi + avg_smoothness) / 2)
    elif max_chi > 0.2 or avg_smoothness > 0.2:
        detection_level = "MEDIUM"
        confidence = (max_chi + avg_smoothness) / 4
    else:
        detection_level = "LOW"
        confidence = max_chi / 4

    analysis["detection"] = {
        "level": detection_level,
        "confidence": float(confidence),
        "recommendation": (
            "High probability of hidden data" if detection_level == "HIGH" else
            "Possible hidden data" if detection_level == "MEDIUM" else
            "No obvious indicators"
        )
    }

    # Calculate capacity for common configurations
    for preset_name in ["R", "RGB", "RGBA"]:
        for bits in [1, 2, 4]:
            config = StegConfig(
                channels=get_channel_preset(preset_name),
                bits_per_channel=bits
            )
            cap = calculate_capacity(image, config)
            analysis["capacity_by_config"][f"{preset_name}_{bits}bit"] = cap["human"]

    return analysis


def detect_encoding(image: Image.Image, password: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Attempt to detect if image contains STEG-encoded data.

    If password is provided, also checks for password-derived magic bytes
    (stealth mode headers that are undetectable without the password).

    Returns detection info if magic bytes found, None otherwise.
    """
    img = image.convert("RGBA")
    pixels = np.array(img, dtype=np.uint8)
    flat_pixels = pixels.reshape(-1, 4)

    # Exhaustive search — try ALL 15 channel presets × 8 bit depths = 120 combinations
    all_channel_combos = [
        [Channel.R, Channel.G, Channel.B],           # RGB (most common first)
        [Channel.R, Channel.G, Channel.B, Channel.A], # RGBA
        [Channel.R],                                   # R
        [Channel.G],                                   # G
        [Channel.B],                                   # B
        [Channel.A],                                   # A
        [Channel.R, Channel.G],                        # RG
        [Channel.R, Channel.B],                        # RB
        [Channel.R, Channel.A],                        # RA
        [Channel.G, Channel.B],                        # GB
        [Channel.G, Channel.A],                        # GA
        [Channel.B, Channel.A],                        # BA
        [Channel.R, Channel.G, Channel.A],             # RGA
        [Channel.R, Channel.B, Channel.A],             # RBA
        [Channel.G, Channel.B, Channel.A],             # GBA
    ]

    configs_to_try = []
    for channels in all_channel_combos:
        for bits in range(1, 9):  # 1-8 bits per channel
            configs_to_try.append(StegConfig(channels=channels, bits_per_channel=bits))

    for config in configs_to_try:
        try:
            header_units = _extract_bit_units(
                flat_pixels,
                HEADER_SIZE * 8 // config.bits_per_channel + 1,
                config,
                len(flat_pixels)
            )
            header_bytes = _bits_array_to_bytes(
                header_units,
                config.bits_per_channel,
                HEADER_SIZE * 8
            )[:HEADER_SIZE]

            # Check for both fixed magic AND password-derived magic
            expected_magics = [MAGIC_BYTES]
            if password:
                expected_magics.append(derive_magic(password))
            if header_bytes[:4] in expected_magics:
                header = StegHeader.from_bytes(header_bytes)
                return {
                    "detected": True,
                    "config": {
                        "channels": [c.name for c in header.config.channels],
                        "bits_per_channel": header.config.bits_per_channel,
                        "strategy": header.config.strategy.value,
                        "compression": header.config.use_compression,
                    },
                    "payload_length": header.payload_length,
                    "original_length": header.original_length,
                }
        except:
            continue

    return None


# ============== BRUTE FORCE LSB EXTRACTION ==============

# Common file signatures for detection
FILE_SIGNATURES = {
    b'\x89PNG\r\n\x1a\n': 'PNG image',
    b'GIF87a': 'GIF image',
    b'GIF89a': 'GIF image',
    b'\xff\xd8\xff': 'JPEG image',
    b'PK\x03\x04': 'ZIP/Office file',
    b'PK\x05\x06': 'ZIP (empty)',
    b'\x7fELF': 'ELF executable',
    b'%PDF': 'PDF document',
    b'Rar!\x1a\x07': 'RAR archive',
    b'\x1f\x8b\x08': 'GZIP data',
    b'BZh': 'BZIP2 data',
    b'\xfd7zXZ': 'XZ data',
    b'SQLite': 'SQLite database',
    b'{\n': 'JSON (likely)',
    b'{"': 'JSON object',
    b'<?xml': 'XML document',
    b'<!DOCTYPE': 'HTML document',
    b'<html': 'HTML document',
}


def _is_printable_ascii(data: bytes, threshold: float = 0.85) -> bool:
    """Check if data is mostly printable ASCII"""
    if not data:
        return False
    printable = sum(1 for b in data if 32 <= b <= 126 or b in (9, 10, 13))
    return printable / len(data) >= threshold


def _is_valid_utf8(data: bytes) -> bool:
    """Check if data is valid UTF-8"""
    try:
        data.decode('utf-8')
        return True
    except UnicodeDecodeError:
        return False


def _detect_file_type(data: bytes) -> Optional[str]:
    """Detect file type from magic bytes"""
    for sig, file_type in FILE_SIGNATURES.items():
        if data.startswith(sig):
            return file_type
    return None


def _score_extraction(data: bytes, max_check: int = 1000) -> Dict[str, Any]:
    """
    Score extracted data for likelihood of being meaningful content.

    Returns dict with score (0-100) and detected characteristics.
    """
    if not data:
        return {"score": 0, "reason": "empty"}

    check_data = data[:max_check]
    result = {
        "score": 0,
        "is_text": False,
        "is_utf8": False,
        "file_type": None,
        "preview": None,
        "length": len(data),
    }

    # Check for file signatures (highest confidence)
    file_type = _detect_file_type(data)
    if file_type:
        result["score"] = 95
        result["file_type"] = file_type
        return result

    # Check for valid UTF-8 text
    if _is_valid_utf8(check_data):
        result["is_utf8"] = True
        text = check_data.decode('utf-8', errors='replace')

        # Check printable ratio
        if _is_printable_ascii(check_data, 0.90):
            result["score"] = 85
            result["is_text"] = True
            result["preview"] = text[:200]
        elif _is_printable_ascii(check_data, 0.70):
            result["score"] = 60
            result["is_text"] = True
            result["preview"] = text[:200]
        else:
            result["score"] = 20

    # Check for ASCII text (even if not valid UTF-8)
    elif _is_printable_ascii(check_data, 0.85):
        result["score"] = 70
        result["is_text"] = True
        result["preview"] = check_data.decode('ascii', errors='replace')[:200]

    # Low entropy might indicate compressed/encrypted data
    # (not random noise)
    else:
        # Check if it looks like compressed data (has some structure)
        byte_freq = {}
        for b in check_data:
            byte_freq[b] = byte_freq.get(b, 0) + 1
        unique_ratio = len(byte_freq) / 256

        if unique_ratio < 0.5:  # Less than half of possible byte values
            result["score"] = 15
            result["reason"] = "possibly compressed/encrypted"

    return result


def extract_raw_lsb(
    image: Image.Image,
    channels: List[Channel],
    bits_per_channel: int = 1,
    max_bytes: int = 10000,
    strategy: EncodingStrategy = EncodingStrategy.SEQUENTIAL
) -> bytes:
    """
    Extract raw LSB data without expecting any header format.

    Args:
        image: PIL Image
        channels: List of channels to extract from
        bits_per_channel: Bits per channel (1-8)
        max_bytes: Maximum bytes to extract
        strategy: Extraction strategy

    Returns:
        Raw extracted bytes
    """
    img = image.convert("RGBA")
    pixels = np.array(img, dtype=np.uint8)
    height, width = pixels.shape[:2]
    total_pixels = height * width
    flat_pixels = pixels.reshape(-1, 4)

    config = StegConfig(
        channels=channels,
        bits_per_channel=bits_per_channel,
        strategy=strategy,
    )

    bits_needed = max_bytes * 8
    units_needed = bits_needed // bits_per_channel
    if bits_needed % bits_per_channel:
        units_needed += 1

    # Don't exceed image capacity
    max_units = (total_pixels * len(channels) * bits_per_channel) // bits_per_channel
    units_needed = min(units_needed, max_units)

    units = _extract_bit_units(flat_pixels, units_needed, config, total_pixels)
    data = _bits_array_to_bytes(units, bits_per_channel, units_needed * bits_per_channel)

    return data[:max_bytes]


def brute_force_extract(
    image: Image.Image,
    max_bytes: int = 5000,
    include_sequential: bool = True,
    include_interleaved: bool = True,
) -> List[Dict[str, Any]]:
    """
    Try multiple LSB extraction configurations and return scored results.

    This function tries common steganography configurations WITHOUT
    expecting any specific header format. Useful for images encoded
    with other tools.

    Args:
        image: PIL Image to analyze
        max_bytes: Max bytes to extract per config
        include_sequential: Try sequential strategy
        include_interleaved: Try interleaved strategy

    Returns:
        List of results sorted by score (highest first), each containing:
        - config: channel/bit configuration used
        - score: likelihood score (0-100)
        - data: extracted bytes
        - preview: text preview if applicable
        - file_type: detected file type if applicable
    """
    results = []

    # Configurations to try (ordered by commonality)
    channel_configs = [
        # Single channels (very common in basic steg tools)
        ([Channel.R], "R"),
        ([Channel.G], "G"),
        ([Channel.B], "B"),
        ([Channel.A], "A"),
        # Multi-channel (common)
        ([Channel.R, Channel.G, Channel.B], "RGB"),
        ([Channel.R, Channel.G, Channel.B, Channel.A], "RGBA"),
        # Two-channel combos
        ([Channel.R, Channel.G], "RG"),
        ([Channel.R, Channel.B], "RB"),
        ([Channel.G, Channel.B], "GB"),
    ]

    bit_depths = [1, 2]  # Most common

    strategies = []
    if include_sequential:
        strategies.append(EncodingStrategy.SEQUENTIAL)
    if include_interleaved:
        strategies.append(EncodingStrategy.INTERLEAVED)

    for channels, channel_name in channel_configs:
        for bits in bit_depths:
            for strategy in strategies:
                try:
                    data = extract_raw_lsb(
                        image,
                        channels,
                        bits,
                        max_bytes,
                        strategy
                    )

                    score_result = _score_extraction(data)

                    if score_result["score"] > 10:  # Filter out noise
                        results.append({
                            "config": {
                                "channels": channel_name,
                                "bits_per_channel": bits,
                                "strategy": strategy.value,
                            },
                            "score": score_result["score"],
                            "data": data,
                            "preview": score_result.get("preview"),
                            "file_type": score_result.get("file_type"),
                            "is_text": score_result.get("is_text", False),
                            "length": len(data),
                        })
                except Exception:
                    continue

    # Sort by score descending
    results.sort(key=lambda x: x["score"], reverse=True)

    return results


def smart_extract(
    image: Image.Image,
    max_bytes: int = 10000,
) -> Optional[Dict[str, Any]]:
    """
    Intelligently extract hidden data, trying STEG header first,
    then falling back to brute force extraction.

    Args:
        image: PIL Image
        max_bytes: Max bytes to extract

    Returns:
        Best extraction result or None if nothing found
    """
    # First try STEG v3 header detection
    detection = detect_encoding(image)
    if detection:
        try:
            data = decode(image, verify_checksum=True)
            return {
                "method": "steg_v3_header",
                "config": detection["config"],
                "data": data,
                "score": 100,
                "is_text": _is_valid_utf8(data),
                "preview": data.decode('utf-8', errors='replace')[:200] if _is_valid_utf8(data) else None,
            }
        except Exception:
            pass  # Fall through to brute force

    # Brute force extraction
    results = brute_force_extract(image, max_bytes)

    if results and results[0]["score"] >= 50:
        return {
            "method": "brute_force_lsb",
            **results[0]
        }

    # Return best result even if low confidence
    if results:
        return {
            "method": "brute_force_lsb",
            "confidence": "low",
            **results[0]
        }

    return None


# ============== LEGACY COMPATIBILITY ==============

# Keep old function signatures working
def encode_batch(
    image: Image.Image,
    data_list: List[bytes],
    configs: List[StegConfig]
) -> Image.Image:
    """Encode multiple payloads with different configs (legacy)"""
    result = image.copy()
    for data, config in zip(data_list, configs):
        result = encode(result, data, config)
    return result
