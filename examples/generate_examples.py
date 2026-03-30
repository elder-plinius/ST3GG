#!/usr/bin/env python3
"""
Generate pre-encoded steganography example files for ST3GG.
Each file contains a hidden message that the Agent tab's exhaustive mode can find.
"""

import struct
import zlib
import wave
import array
import os
from PIL import Image, PngImagePlugin

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
SECRET_MSG = "STEGOSAURUS WRECKS - Hidden message found! 🦕"
PLINIAN_DIVIDER = "⊰•-•✧•-•-⦑/L\\O/V\\E/\\P/L\\I/N\\Y/⦒-•-•✧•-•⊱"

# =============================================================================
# Utility functions matching ST3GG's STEG v3 format
# =============================================================================

def crc32_steg(data: bytes) -> int:
    """CRC32 matching ST3GG's implementation."""
    crc = 0xFFFFFFFF
    table = []
    for i in range(256):
        c = i
        for _ in range(8):
            c = (0xEDB88320 ^ (c >> 1)) if (c & 1) else (c >> 1)
        table.append(c)
    for b in data:
        crc = table[(crc ^ b) & 0xFF] ^ (crc >> 8)
    return (crc ^ 0xFFFFFFFF) & 0xFFFFFFFF


def deflate_compress(data: bytes) -> bytes:
    """Deflate compression matching browser's CompressionStream('deflate')."""
    # Browser 'deflate' uses raw deflate wrapped with zlib header (wbits=15)
    # Actually, CompressionStream('deflate') uses RFC 1950 (zlib format)
    return zlib.compress(data)


def create_steg_header(payload_len: int, original_len: int, crc: int,
                       channel_mask: int, bits_per_channel: int,
                       compressed: bool = True) -> bytes:
    """Create a 32-byte STEG v3 header."""
    header = bytearray(32)
    # Magic: STEG
    header[0:4] = b'STEG'
    # Version
    header[4] = 3
    # Channel mask
    header[5] = channel_mask
    # Bits per channel
    header[6] = bits_per_channel
    # Bit offset
    header[7] = 0
    # Flags: compressed (bit 0) | interleaved (bit 1)
    header[8] = (1 if compressed else 0) | 2
    # Bytes 9-15: reserved (zeros)
    # Payload length (big endian)
    struct.pack_into('>I', header, 16, payload_len)
    # Original length (big endian)
    struct.pack_into('>I', header, 20, original_len)
    # CRC32 (big endian)
    struct.pack_into('>I', header, 24, crc)
    return bytes(header)


def bytes_to_bits(data: bytes, bits_per_unit: int = 1) -> list:
    """Convert bytes to bit units, matching ST3GG's bytesToBits."""
    bits = []
    for byte in data:
        for j in range(7, -1, -1):
            bits.append((byte >> j) & 1)

    if bits_per_unit == 1:
        return bits

    result = []
    for i in range(0, len(bits), bits_per_unit):
        value = 0
        for j in range(bits_per_unit):
            if i + j < len(bits):
                value = (value << 1) | bits[i + j]
        result.append(value)
    return result


# =============================================================================
# 1. PNG with LSB RGB 1-bit (STEG v3 header)
# =============================================================================

def generate_lsb_png():
    """Create a 200x200 PNG with a hidden message in LSB RGB 1-bit."""
    print("  Generating LSB RGB 1-bit PNG...")
    width, height = 200, 200
    img = Image.new('RGBA', (width, height))

    # Create a nice gradient background
    pixels = img.load()
    for y in range(height):
        for x in range(width):
            r = int(100 + 80 * (x / width))
            g = int(60 + 120 * (y / height))
            b = int(140 + 60 * ((x + y) / (width + height)))
            pixels[x, y] = (r, g, b, 255)

    # Encode message using STEG v3 format
    msg_bytes = SECRET_MSG.encode('utf-8')
    crc = crc32_steg(msg_bytes)
    payload = deflate_compress(msg_bytes)

    # RGB channels = mask 0b0111 = 7, 1 bit per channel
    header = create_steg_header(len(payload), len(msg_bytes), crc,
                                channel_mask=7, bits_per_channel=1)

    full_data = header + payload
    bit_units = bytes_to_bits(full_data, 1)

    # Embed in LSB of RGB channels (interleaved)
    channels = [0, 1, 2]  # R, G, B
    unit_idx = 0
    for pix_idx in range(width * height):
        if unit_idx >= len(bit_units):
            break
        x = pix_idx % width
        y = pix_idx // width
        r, g, b, a = pixels[x, y]
        vals = [r, g, b, a]
        for ch in channels:
            if unit_idx >= len(bit_units):
                break
            vals[ch] = (vals[ch] & 0xFE) | bit_units[unit_idx]
            unit_idx += 1
        pixels[x, y] = tuple(vals)

    path = os.path.join(OUTPUT_DIR, 'example_lsb_rgb.png')
    img.save(path)
    print(f"    -> {path} ({unit_idx} bits embedded)")
    return path


# =============================================================================
# 2. PNG with tEXt chunk
# =============================================================================

def generate_text_chunk_png():
    """Create a PNG with a hidden message in a tEXt metadata chunk."""
    print("  Generating PNG with tEXt chunk...")
    width, height = 150, 150
    img = Image.new('RGB', (width, height))
    pixels = img.load()

    # Simple blue-ish pattern
    for y in range(height):
        for x in range(width):
            r = int(40 + 30 * (x / width))
            g = int(50 + 40 * (y / height))
            b = int(150 + 80 * ((x + y) / (width + height)))
            pixels[x, y] = (r, g, b)

    # Add tEXt chunks with hidden data
    info = PngImagePlugin.PngInfo()
    info.add_text("Comment", "Just a normal image, nothing to see here...")
    info.add_text("Secret", SECRET_MSG)
    info.add_text("Author", "STEGOSAURUS WRECKS")
    info.add_text("Flag", "CTF{hidden_in_plain_sight}")

    path = os.path.join(OUTPUT_DIR, 'example_png_chunks.png')
    img.save(path, pnginfo=info)
    print(f"    -> {path}")
    return path


# =============================================================================
# 3. PNG with trailing data after IEND
# =============================================================================

def generate_trailing_data_png():
    """Create a PNG with hidden data appended after the IEND chunk."""
    print("  Generating PNG with trailing data...")
    width, height = 120, 120
    img = Image.new('RGB', (width, height))
    pixels = img.load()

    # Green-ish pattern
    for y in range(height):
        for x in range(width):
            r = int(30 + 50 * (x / width))
            g = int(120 + 100 * (y / height))
            b = int(40 + 40 * ((x * y) / (width * height)))
            pixels[x, y] = (r, g, b)

    path = os.path.join(OUTPUT_DIR, 'example_trailing_data.png')
    img.save(path)

    # Append hidden data after IEND
    trailing = b'\n--- HIDDEN DATA BELOW ---\n'
    trailing += SECRET_MSG.encode('utf-8')
    trailing += b'\nCTF{data_after_iend_chunk}\n'
    trailing += b'This data is invisible to normal image viewers!\n'

    with open(path, 'ab') as f:
        f.write(trailing)

    print(f"    -> {path} ({len(trailing)} bytes appended)")
    return path


# =============================================================================
# 4. Text with zero-width Unicode steganography
# =============================================================================

def generate_zero_width_text():
    """Create a text file with a message hidden in zero-width Unicode chars."""
    print("  Generating zero-width Unicode text...")

    ZWSP = '\u200B'  # Zero-width space = 0
    ZWNJ = '\u200C'  # Zero-width non-joiner = 1
    ZWJ = '\u200D'   # Zero-width joiner = delimiter

    secret = "Agent found the zero-width secret!"
    secret_bytes = secret.encode('utf-8')

    # Convert to binary string
    binary_str = ''.join(format(b, '08b') for b in secret_bytes)

    # Build zero-width string
    zw_string = ZWJ  # Start delimiter
    for bit in binary_str:
        zw_string += ZWSP if bit == '0' else ZWNJ
    zw_string += ZWJ  # End delimiter

    cover = """The Stegosaurus was a large, herbivorous dinosaur that lived during the Late Jurassic period,
approximately 155 to 150 million years ago. It is best known for its distinctive row of large,
bony plates along its back and the sharp spikes on its tail, known as the thagomizer.

Despite its massive size, the Stegosaurus had a remarkably small brain, roughly the size of a
walnut. This has led to much speculation about how such a large animal could function with such
limited cognitive capacity.

The name "Stegosaurus" means "roof lizard" or "covered lizard," referring to the plates on its
back, which were once thought to lie flat like roof tiles. Modern research suggests these plates
were used for thermoregulation and display rather than defense."""

    # Insert after first character
    stego_text = cover[0] + zw_string + cover[1:]

    path = os.path.join(OUTPUT_DIR, 'example_zero_width.txt')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(stego_text)

    print(f"    -> {path} ({len(binary_str)} bits hidden)")
    return path


# =============================================================================
# 5. Text with whitespace encoding
# =============================================================================

def generate_whitespace_text():
    """Create a text file with a message hidden in trailing whitespace."""
    print("  Generating whitespace-encoded text...")

    secret = "Whitespace hides secrets!"
    secret_bytes = secret.encode('utf-8')

    # Length prefix (16 bits) + data bits
    length_bits = format(len(secret_bytes), '016b')
    data_bits = ''.join(format(b, '08b') for b in secret_bytes)
    all_bits = length_bits + data_bits

    cover_lines = [
        "How to Identify Steganography",
        "==============================",
        "",
        "Steganography is the practice of hiding secret information within",
        "ordinary, non-secret data or physical objects. Unlike cryptography,",
        "which makes data unreadable, steganography conceals the very",
        "existence of the secret message.",
        "",
        "Common techniques include:",
        "- Least Significant Bit (LSB) embedding in images",
        "- Hiding data in audio frequency spectrums",
        "- Using invisible Unicode characters in text",
        "- Appending data after file end markers",
        "- Encoding in metadata fields",
        "",
        "Detection methods include statistical analysis, visual inspection",
        "of bit planes, frequency domain analysis, and file structure",
        "examination. Tools like ST3GG can automate this process.",
        "",
        "The word steganography comes from the Greek words 'steganos'",
        "(meaning covered or hidden) and 'graphein' (meaning to write).",
        "",
        "In the digital age, steganography has found applications in",
        "digital watermarking, covert communication, and CTF challenges.",
        "",
        "Always remember: just because you can't see it doesn't mean",
        "it's not there. Hidden in plain sight is the ultimate disguise.",
        "",
        "End of document.",
    ]

    bit_index = 0
    result_lines = []
    for line in cover_lines:
        trailing = ''
        for _ in range(8):
            if bit_index < len(all_bits):
                trailing += ' ' if all_bits[bit_index] == '0' else '\t'
                bit_index += 1
        result_lines.append(line + trailing)

    path = os.path.join(OUTPUT_DIR, 'example_whitespace.txt')
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(result_lines))

    print(f"    -> {path} ({bit_index} bits hidden in trailing whitespace)")
    return path


# =============================================================================
# 6. Text with invisible ink (Unicode tag characters)
# =============================================================================

def generate_invisible_ink_text():
    """Create a text file with a message hidden using Unicode tag characters."""
    print("  Generating invisible ink (Unicode tags) text...")

    TAG_BASE = 0xE0000
    secret = "Invisible ink message decoded!"

    # Build tag string
    tag_string = chr(TAG_BASE)  # Start tag
    for char in secret:
        code = ord(char)
        if code < 128:
            tag_string += chr(TAG_BASE + code)
    tag_string += chr(TAG_BASE)  # End tag

    cover = """Dinosaur Facts: The Stegosaurus

The Stegosaurus is one of the most recognizable dinosaurs thanks to its
distinctive double row of kite-shaped plates rising vertically along its
arched back and the two pairs of long spikes extending from its tail.

Size: Up to 9 meters (30 feet) long and 4 meters (14 feet) tall
Weight: Approximately 5,000 kg (11,000 lbs)
Diet: Herbivore (ferns, cycads, and conifers)
Period: Late Jurassic (155-150 million years ago)
Location: Western North America, Portugal"""

    # Insert tag string after first character
    stego_text = cover[0] + tag_string + cover[1:]

    path = os.path.join(OUTPUT_DIR, 'example_invisible_ink.txt')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(stego_text)

    print(f"    -> {path}")
    return path


# =============================================================================
# 7. WAV with Audio LSB steganography
# =============================================================================

def generate_audio_lsb_wav():
    """Create a WAV file with a message hidden in audio sample LSBs."""
    print("  Generating WAV with audio LSB...")

    sample_rate = 44100
    duration = 2  # seconds
    num_samples = sample_rate * duration

    # Generate a simple sine wave tone (440 Hz)
    import math
    frequency = 440.0
    samples = []
    for i in range(num_samples):
        t = i / sample_rate
        # Mix two frequencies for a richer sound
        value = 0.5 * math.sin(2 * math.pi * frequency * t)
        value += 0.3 * math.sin(2 * math.pi * (frequency * 1.5) * t)
        # Convert to 16-bit integer
        sample = int(value * 16000)
        sample = max(-32768, min(32767, sample))
        samples.append(sample)

    # Embed message in LSB of samples
    msg = SECRET_MSG.encode('utf-8')

    # Simple format: 4-byte length prefix + message bytes
    length_bytes = struct.pack('>I', len(msg))
    payload = length_bytes + msg

    # Convert payload to bits
    bits = []
    for byte in payload:
        for j in range(7, -1, -1):
            bits.append((byte >> j) & 1)

    # Embed bits in LSB of samples (handling signed 16-bit properly)
    for i, bit in enumerate(bits):
        if i < len(samples):
            s = samples[i]
            # Convert to unsigned, set LSB, convert back to signed
            u = s & 0xFFFF  # unsigned view
            u = (u & 0xFFFE) | bit
            # Convert back to signed
            samples[i] = u if u < 32768 else u - 65536

    path = os.path.join(OUTPUT_DIR, 'example_audio_lsb.wav')
    with wave.open(path, 'w') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)  # 16-bit
        wav.setframerate(sample_rate)
        # Pack samples as signed 16-bit little-endian
        data = struct.pack(f'<{len(samples)}h', *samples)
        wav.writeframes(data)

    print(f"    -> {path} ({len(bits)} bits embedded in {num_samples} samples)")
    return path


# =============================================================================
# 8. PNG with EXIF-like metadata (hidden in Description)
# =============================================================================

def generate_exif_png():
    """Create a PNG with suspicious metadata fields."""
    print("  Generating PNG with metadata...")
    width, height = 100, 100
    img = Image.new('RGB', (width, height))
    pixels = img.load()

    # Red-orange pattern
    for y in range(height):
        for x in range(width):
            r = int(180 + 60 * (x / width))
            g = int(80 + 60 * (y / height))
            b = int(20 + 30 * ((x + y) / (width + height)))
            pixels[x, y] = (r, g, b)

    info = PngImagePlugin.PngInfo()
    info.add_text("Description", "Base64 encoded secret: " +
                  __import__('base64').b64encode(SECRET_MSG.encode()).decode())
    info.add_text("Software", "STEGOSAURUS WRECKS v3.0")
    info.add_text("Warning", "Look closer at the other example files too!")
    # Add a hex-encoded hidden message
    info.add_text("HexData", SECRET_MSG.encode('utf-8').hex())

    path = os.path.join(OUTPUT_DIR, 'example_metadata.png')
    img.save(path, pnginfo=info)
    print(f"    -> {path}")
    return path


# =============================================================================
# 9. BMP with LSB steganography
# =============================================================================

def generate_lsb_bmp():
    """Create a BMP file with the Plinian divider hidden in LSB of pixels."""
    print("  Generating BMP with LSB steganography...")
    width, height = 160, 160
    img = Image.new('RGB', (width, height))
    pixels = img.load()

    # Purple gradient background
    for y in range(height):
        for x in range(width):
            r = int(120 + 80 * (x / width))
            g = int(40 + 60 * (y / height))
            b = int(160 + 80 * ((x + y) / (width + height)))
            pixels[x, y] = (r, g, b)

    # Encode Plinian divider in LSB
    msg_bytes = PLINIAN_DIVIDER.encode('utf-8')
    length_bytes = struct.pack('>I', len(msg_bytes))
    payload = length_bytes + msg_bytes
    bits = []
    for byte in payload:
        for j in range(7, -1, -1):
            bits.append((byte >> j) & 1)

    bit_idx = 0
    for pix_idx in range(width * height):
        if bit_idx >= len(bits):
            break
        x = pix_idx % width
        y = pix_idx // width
        r, g, b = pixels[x, y]
        vals = [r, g, b]
        for ch in range(3):
            if bit_idx >= len(bits):
                break
            vals[ch] = (vals[ch] & 0xFE) | bits[bit_idx]
            bit_idx += 1
        pixels[x, y] = tuple(vals)

    path = os.path.join(OUTPUT_DIR, 'example_lsb.bmp')
    img.save(path, 'BMP')
    print(f"    -> {path} ({bit_idx} bits embedded)")
    return path


# =============================================================================
# 10. GIF with comment extension
# =============================================================================

def generate_gif_comment():
    """Create a GIF with the Plinian divider hidden in a comment extension block."""
    print("  Generating GIF with comment extension...")
    width, height = 100, 100
    img = Image.new('P', (width, height))
    pixels = img.load()

    # Simple gradient pattern
    for y in range(height):
        for x in range(width):
            pixels[x, y] = int((x + y) * 127 / (width + height))

    path = os.path.join(OUTPUT_DIR, 'example_comment.gif')
    img.save(path, 'GIF')

    # GIF comment extension: inject after GIF header
    with open(path, 'rb') as f:
        data = f.read()

    # Build comment extension block
    comment = PLINIAN_DIVIDER.encode('utf-8')
    comment_ext = b'\x21\xFE'  # Comment extension introducer
    # Split into sub-blocks of max 255 bytes
    i = 0
    while i < len(comment):
        chunk = comment[i:i + 255]
        comment_ext += bytes([len(chunk)]) + chunk
        i += 255
    comment_ext += b'\x00'  # Block terminator

    # Insert comment extension after GIF header (before image data)
    # GIF header is 6 bytes + logical screen descriptor (7 bytes) + global color table
    # Find the image descriptor (0x2C) or extension block
    insert_pos = 13  # After header + LSD
    if data[10] & 0x80:  # Global color table flag
        gct_size = 3 * (2 ** ((data[10] & 0x07) + 1))
        insert_pos += gct_size

    new_data = data[:insert_pos] + comment_ext + data[insert_pos:]
    with open(path, 'wb') as f:
        f.write(new_data)

    print(f"    -> {path} (comment extension: {len(comment)} bytes)")
    return path


# =============================================================================
# 11. GIF with LSB in palette indices
# =============================================================================

def generate_gif_lsb():
    """Create a GIF with the Plinian divider in LSB of palette indices.

    Note: We write the GIF manually (binary) because Pillow's GIF encoder
    requantizes the palette, which destroys LSB data. We use uncompressed
    LZW (max code size) to preserve exact index values.
    """
    print("  Generating GIF with palette index LSB...")
    width, height = 120, 120

    # Create a palette with maximally distinct colors (pairs differ in R LSB)
    palette = bytearray(256 * 3)
    for i in range(256):
        palette[i * 3] = (i * 37 + 80) & 0xFE  # R: spread out, always even base
        palette[i * 3 + 1] = (i * 13 + 60) & 0xFF  # G
        palette[i * 3 + 2] = (i * 7 + 120) & 0xFF  # B
        # Ensure pairs (2i, 2i+1) differ only in R LSB
        if i % 2 == 1:
            palette[i * 3] = palette[(i - 1) * 3] | 1
            palette[i * 3 + 1] = palette[(i - 1) * 3 + 1]
            palette[i * 3 + 2] = palette[(i - 1) * 3 + 2]

    # Build pixel index data
    pixel_indices = bytearray()
    for y in range(height):
        for x in range(width):
            # Use even palette indices so we can flip LSB
            pixel_indices.append(int((x + y) * 127 / (width + height)) * 2 % 256)

    # Encode Plinian divider in LSB of palette indices
    msg_bytes = PLINIAN_DIVIDER.encode('utf-8')
    length_bytes = struct.pack('>I', len(msg_bytes))
    payload = length_bytes + msg_bytes
    bits = []
    for byte in payload:
        for j in range(7, -1, -1):
            bits.append((byte >> j) & 1)

    bit_idx = 0
    for i in range(len(pixel_indices)):
        if bit_idx >= len(bits):
            break
        pixel_indices[i] = (pixel_indices[i] & 0xFE) | bits[bit_idx]
        bit_idx += 1

    # Write GIF manually to preserve exact palette indices
    path = os.path.join(OUTPUT_DIR, 'example_lsb.gif')
    with open(path, 'wb') as f:
        # GIF89a header
        f.write(b'GIF89a')
        # Logical Screen Descriptor
        f.write(struct.pack('<HH', width, height))
        f.write(bytes([0xF7, 0x00, 0x00]))  # GCT flag, 256 colors, no sort, bg=0, aspect=0
        # Global Color Table (256 entries)
        f.write(bytes(palette))
        # Image Descriptor
        f.write(b'\x2C')  # Image separator
        f.write(struct.pack('<HHHH', 0, 0, width, height))
        f.write(bytes([0x00]))  # No local color table, not interlaced

        # LZW-compress the pixel data
        # Min code size = 8 (for 256 colors)
        min_code_size = 8
        f.write(bytes([min_code_size]))

        # Use simple LZW: emit clear code, then each pixel as a literal, then EOI
        clear_code = 1 << min_code_size  # 256
        eoi_code = clear_code + 1        # 257

        # Bit packer
        bit_buffer = 0
        bit_count = 0
        output = bytearray()
        code_size = min_code_size + 1  # Start at 9 bits

        def emit_code(code):
            nonlocal bit_buffer, bit_count
            bit_buffer |= (code << bit_count)
            bit_count += code_size
            while bit_count >= 8:
                output.append(bit_buffer & 0xFF)
                bit_buffer >>= 8
                bit_count -= 8

        # Emit clear code first
        emit_code(clear_code)

        # Emit each pixel as a literal code (0-255)
        # To keep code_size at 9, emit clear codes periodically to reset the table
        count = 0
        for idx in pixel_indices:
            emit_code(idx)
            count += 1
            if count >= 250:  # Reset before table grows too much
                emit_code(clear_code)
                code_size = min_code_size + 1
                count = 0

        # Emit EOI
        emit_code(eoi_code)

        # Flush remaining bits
        if bit_count > 0:
            output.append(bit_buffer & 0xFF)

        # Write as sub-blocks (max 255 bytes each)
        i = 0
        while i < len(output):
            chunk = output[i:i + 255]
            f.write(bytes([len(chunk)]))
            f.write(chunk)
            i += 255
        f.write(b'\x00')  # Block terminator

        # Trailer
        f.write(b'\x3B')

    print(f"    -> {path} ({bit_idx} bits embedded)")
    return path


# =============================================================================
# 12. TIFF with metadata steganography
# =============================================================================

def generate_tiff_metadata():
    """Create a TIFF with the Plinian divider hidden in EXIF/metadata fields."""
    print("  Generating TIFF with metadata steganography...")
    width, height = 100, 100
    img = Image.new('RGB', (width, height))
    pixels = img.load()

    # Warm gradient
    for y in range(height):
        for x in range(width):
            r = int(200 + 40 * (x / width))
            g = int(140 + 60 * (y / height))
            b = int(60 + 40 * ((x + y) / (width + height)))
            pixels[x, y] = (r, g, b)

    import base64
    path = os.path.join(OUTPUT_DIR, 'example_metadata.tiff')
    # Save TIFF with metadata tags
    img.save(path, 'TIFF', compression='raw',
             software='ST3GG STEGOSAURUS WRECKS',
             description=base64.b64encode(PLINIAN_DIVIDER.encode('utf-8')).decode())
    print(f"    -> {path}")
    return path


# =============================================================================
# 13. TIFF with LSB steganography
# =============================================================================

def generate_tiff_lsb():
    """Create a TIFF with the Plinian divider hidden in LSB of pixels."""
    print("  Generating TIFF with LSB steganography...")
    width, height = 140, 140
    img = Image.new('RGB', (width, height))
    pixels = img.load()

    # Teal gradient
    for y in range(height):
        for x in range(width):
            r = int(30 + 60 * (x / width))
            g = int(140 + 80 * (y / height))
            b = int(130 + 80 * ((x + y) / (width + height)))
            pixels[x, y] = (r, g, b)

    # Encode Plinian divider in LSB
    msg_bytes = PLINIAN_DIVIDER.encode('utf-8')
    length_bytes = struct.pack('>I', len(msg_bytes))
    payload = length_bytes + msg_bytes
    bits = []
    for byte in payload:
        for j in range(7, -1, -1):
            bits.append((byte >> j) & 1)

    bit_idx = 0
    for pix_idx in range(width * height):
        if bit_idx >= len(bits):
            break
        x = pix_idx % width
        y = pix_idx // width
        r, g, b = pixels[x, y]
        vals = [r, g, b]
        for ch in range(3):
            if bit_idx >= len(bits):
                break
            vals[ch] = (vals[ch] & 0xFE) | bits[bit_idx]
            bit_idx += 1
        pixels[x, y] = tuple(vals)

    path = os.path.join(OUTPUT_DIR, 'example_lsb.tiff')
    img.save(path, 'TIFF', compression='raw')
    print(f"    -> {path} ({bit_idx} bits embedded)")
    return path


# =============================================================================
# 14. PPM with LSB steganography
# =============================================================================

def generate_ppm_lsb():
    """Create a PPM (Portable Pixmap) with the Plinian divider in LSB."""
    print("  Generating PPM with LSB steganography...")
    width, height = 120, 120

    # Build pixel data
    pixel_data = bytearray()
    for y in range(height):
        for x in range(width):
            r = int(100 + 90 * (x / width))
            g = int(80 + 100 * (y / height))
            b = int(60 + 120 * ((x + y) / (width + height)))
            pixel_data.extend([r, g, b])

    # Encode Plinian divider in LSB
    msg_bytes = PLINIAN_DIVIDER.encode('utf-8')
    length_bytes = struct.pack('>I', len(msg_bytes))
    payload = length_bytes + msg_bytes
    bits = []
    for byte in payload:
        for j in range(7, -1, -1):
            bits.append((byte >> j) & 1)

    for i, bit in enumerate(bits):
        if i < len(pixel_data):
            pixel_data[i] = (pixel_data[i] & 0xFE) | bit

    path = os.path.join(OUTPUT_DIR, 'example_lsb.ppm')
    with open(path, 'wb') as f:
        f.write(f'P6\n{width} {height}\n255\n'.encode('ascii'))
        f.write(bytes(pixel_data))
    print(f"    -> {path} ({len(bits)} bits embedded)")
    return path


# =============================================================================
# 15. PGM with LSB steganography
# =============================================================================

def generate_pgm_lsb():
    """Create a PGM (Portable Graymap) with the Plinian divider in LSB."""
    print("  Generating PGM with LSB steganography...")
    width, height = 150, 150

    # Build grayscale pixel data
    pixel_data = bytearray()
    for y in range(height):
        for x in range(width):
            val = int(60 + 160 * ((x * y) / (width * height)))
            pixel_data.append(val)

    # Encode Plinian divider in LSB
    msg_bytes = PLINIAN_DIVIDER.encode('utf-8')
    length_bytes = struct.pack('>I', len(msg_bytes))
    payload = length_bytes + msg_bytes
    bits = []
    for byte in payload:
        for j in range(7, -1, -1):
            bits.append((byte >> j) & 1)

    for i, bit in enumerate(bits):
        if i < len(pixel_data):
            pixel_data[i] = (pixel_data[i] & 0xFE) | bit

    path = os.path.join(OUTPUT_DIR, 'example_lsb.pgm')
    with open(path, 'wb') as f:
        f.write(f'P5\n{width} {height}\n255\n'.encode('ascii'))
        f.write(bytes(pixel_data))
    print(f"    -> {path} ({len(bits)} bits embedded)")
    return path


# =============================================================================
# 16. SVG with hidden data in XML
# =============================================================================

def generate_svg_hidden():
    """Create an SVG with the Plinian divider hidden in XML comments and attributes."""
    print("  Generating SVG with hidden XML data...")
    import base64

    encoded = base64.b64encode(PLINIAN_DIVIDER.encode('utf-8')).decode()
    hex_encoded = PLINIAN_DIVIDER.encode('utf-8').hex()

    svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<!-- {PLINIAN_DIVIDER} -->
<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200"
     data-steg="{encoded}"
     data-desc="Nothing suspicious here">
  <!-- Hidden in plain sight: steganography demonstration file -->
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#4a0e8f;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#c471ed;stop-opacity:1" />
    </linearGradient>
    <linearGradient id="fg" x1="0%" y1="100%" x2="100%" y2="0%">
      <stop offset="0%" style="stop-color:#12c2e9;stop-opacity:0.8" />
      <stop offset="100%" style="stop-color:#f64f59;stop-opacity:0.8" />
    </linearGradient>
  </defs>
  <rect width="200" height="200" fill="url(#bg)"/>
  <circle cx="100" cy="80" r="50" fill="url(#fg)" opacity="0.7"/>
  <polygon points="60,140 100,90 140,140" fill="#f5af19" opacity="0.6"/>
  <text x="100" y="175" font-family="monospace" font-size="11"
        fill="white" text-anchor="middle" opacity="0.8">ST3GG Example</text>
  <!-- hex:{hex_encoded} -->
  <metadata>
    <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
             xmlns:dc="http://purl.org/dc/elements/1.1/">
      <rdf:Description>
        <dc:description>{PLINIAN_DIVIDER}</dc:description>
        <dc:creator>STEGOSAURUS WRECKS</dc:creator>
      </rdf:Description>
    </rdf:RDF>
  </metadata>
</svg>'''

    path = os.path.join(OUTPUT_DIR, 'example_hidden.svg')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(svg)
    print(f"    -> {path}")
    return path


# =============================================================================
# 17. ICO with LSB steganography
# =============================================================================

def generate_ico_lsb():
    """Create an ICO (icon) file with the Plinian divider in LSB of pixels."""
    print("  Generating ICO with LSB steganography...")
    size = 32
    img = Image.new('RGBA', (size, size))
    pixels = img.load()

    # Icon-like gradient
    for y in range(size):
        for x in range(size):
            r = int(60 + 160 * (x / size))
            g = int(100 + 100 * (y / size))
            b = int(180 + 60 * ((x + y) / (2 * size)))
            # Circular alpha mask
            cx, cy = size / 2, size / 2
            dist = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
            a = 255 if dist < size / 2 - 1 else 0
            pixels[x, y] = (r, g, b, a)

    # Encode Plinian divider in LSB of RGB
    msg_bytes = PLINIAN_DIVIDER.encode('utf-8')
    length_bytes = struct.pack('>H', len(msg_bytes))  # 16-bit length for small icon
    payload = length_bytes + msg_bytes
    bits = []
    for byte in payload:
        for j in range(7, -1, -1):
            bits.append((byte >> j) & 1)

    bit_idx = 0
    for pix_idx in range(size * size):
        if bit_idx >= len(bits):
            break
        x = pix_idx % size
        y = pix_idx // size
        r, g, b, a = pixels[x, y]
        vals = [r, g, b]
        for ch in range(3):
            if bit_idx >= len(bits):
                break
            vals[ch] = (vals[ch] & 0xFE) | bits[bit_idx]
            bit_idx += 1
        pixels[x, y] = (vals[0], vals[1], vals[2], a)

    path = os.path.join(OUTPUT_DIR, 'example_lsb.ico')
    img.save(path, format='ICO', sizes=[(32, 32)])
    print(f"    -> {path} ({bit_idx} bits embedded)")
    return path


# =============================================================================
# 18. WebP with metadata steganography
# =============================================================================

def generate_webp_metadata():
    """Create a WebP with the Plinian divider hidden in EXIF and XMP metadata.

    Note: EXIF tags use ASCII encoding which corrupts non-ASCII Unicode chars.
    We store: base64-encoded divider in EXIF ImageDescription, raw divider in XMP.
    """
    print("  Generating WebP with metadata steganography...")
    import base64

    width, height = 120, 120
    img = Image.new('RGB', (width, height))
    pixels = img.load()

    # Coral gradient
    for y in range(height):
        for x in range(width):
            r = int(220 + 30 * (x / width))
            g = int(80 + 70 * (y / height))
            b = int(60 + 80 * ((x + y) / (width + height)))
            pixels[x, y] = (r, g, b)

    secret_bytes = PLINIAN_DIVIDER.encode('utf-8')
    encoded_b64 = base64.b64encode(secret_bytes).decode()

    # EXIF: use base64 for ImageDescription (ASCII-safe)
    exif_data = img.getexif()
    exif_data[270] = f"b64:{encoded_b64}"  # ImageDescription (base64-safe)
    exif_data[305] = "STEGOSAURUS WRECKS v3.0"  # Software
    exif_data[315] = f"hex:{secret_bytes.hex()}"  # Artist (hex-safe)

    path = os.path.join(OUTPUT_DIR, 'example_metadata.webp')
    img.save(path, 'WebP', exif=exif_data.tobytes())

    # Also inject XMP with full UTF-8 support by appending to the file
    # WebP files support XMP chunks - we'll append one after the EXIF
    xmp = (f'<?xpacket begin="\xef\xbb\xbf"?>'
           f'<x:xmpmeta xmlns:x="adobe:ns:meta/">'
           f'<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"'
           f' xmlns:dc="http://purl.org/dc/elements/1.1/">'
           f'<rdf:Description>'
           f'<dc:description>{PLINIAN_DIVIDER}</dc:description>'
           f'<dc:subject>{encoded_b64}</dc:subject>'
           f'</rdf:Description>'
           f'</rdf:RDF>'
           f'</x:xmpmeta>'
           f'<?xpacket end="w"?>').encode('utf-8')

    # Inject XMP chunk into RIFF/WebP container
    with open(path, 'rb') as f:
        data = f.read()

    # WebP RIFF structure: RIFF + size + WEBP + chunks
    # Add an XMP chunk (FourCC: "XMP ")
    xmp_chunk = b'XMP ' + struct.pack('<I', len(xmp)) + xmp
    if len(xmp) % 2:
        xmp_chunk += b'\x00'  # Pad to even

    # Insert before the end of RIFF
    new_riff_size = struct.unpack('<I', data[4:8])[0] + len(xmp_chunk)
    data = data[:4] + struct.pack('<I', new_riff_size) + data[8:] + xmp_chunk

    with open(path, 'wb') as f:
        f.write(data)

    print(f"    -> {path}")
    return path


# =============================================================================
# 19. WebP with LSB steganography
# =============================================================================

def generate_webp_lsb():
    """Create a lossless WebP with the Plinian divider in LSB of pixels."""
    print("  Generating WebP with LSB steganography...")
    width, height = 130, 130
    img = Image.new('RGB', (width, height))
    pixels = img.load()

    # Ocean gradient
    for y in range(height):
        for x in range(width):
            r = int(20 + 50 * (x / width))
            g = int(80 + 80 * (y / height))
            b = int(150 + 90 * ((x + y) / (width + height)))
            pixels[x, y] = (r, g, b)

    # Encode Plinian divider in LSB
    msg_bytes = PLINIAN_DIVIDER.encode('utf-8')
    length_bytes = struct.pack('>I', len(msg_bytes))
    payload = length_bytes + msg_bytes
    bits = []
    for byte in payload:
        for j in range(7, -1, -1):
            bits.append((byte >> j) & 1)

    bit_idx = 0
    for pix_idx in range(width * height):
        if bit_idx >= len(bits):
            break
        x = pix_idx % width
        y = pix_idx // width
        r, g, b = pixels[x, y]
        vals = [r, g, b]
        for ch in range(3):
            if bit_idx >= len(bits):
                break
            vals[ch] = (vals[ch] & 0xFE) | bits[bit_idx]
            bit_idx += 1
        pixels[x, y] = tuple(vals)

    path = os.path.join(OUTPUT_DIR, 'example_lsb.webp')
    img.save(path, 'WebP', lossless=True)
    print(f"    -> {path} ({bit_idx} bits embedded)")
    return path


# =============================================================================
# 20. HTML with hidden content
# =============================================================================

def generate_html_hidden():
    """Create an HTML file with the Plinian divider hidden in multiple ways."""
    print("  Generating HTML with hidden content...")
    import base64

    encoded = base64.b64encode(PLINIAN_DIVIDER.encode('utf-8')).decode()
    hex_encoded = PLINIAN_DIVIDER.encode('utf-8').hex()

    # Zero-width encoding of the divider
    ZWSP = '\u200B'
    ZWNJ = '\u200C'
    ZWJ = '\u200D'
    secret_bytes = PLINIAN_DIVIDER.encode('utf-8')
    binary_str = ''.join(format(b, '08b') for b in secret_bytes)
    zw_string = ZWJ
    for bit in binary_str:
        zw_string += ZWSP if bit == '0' else ZWNJ
    zw_string += ZWJ

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="description" content="{encoded}">
    <meta name="generator" content="STEGOSAURUS WRECKS">
    <title>Steganography Demo</title>
    <style>
        body {{ font-family: 'Segoe UI', sans-serif; background: #1a1a2e; color: #e0e0e0;
               max-width: 700px; margin: 40px auto; padding: 20px; }}
        h1 {{ color: #c471ed; }}
        .cover {{ line-height: 1.8; }}
        /* data-payload: {hex_encoded} */
        .hidden {{ display: none; }}
    </style>
</head>
<!-- {PLINIAN_DIVIDER} -->
<body>
    <h1>Stegosaurus Facts</h1>
    <div class="cover">
        <p>{zw_string}The Stegosaurus was one of the most distinctive dinosaurs of the Late
        Jurassic period. Its double row of bony plates and spiked tail made it
        instantly recognizable among prehistoric creatures.</p>
        <p>Despite weighing up to 5 metric tons, the Stegosaurus had a brain
        roughly the size of a walnut, making it one of the least intelligent
        dinosaurs relative to its body size.</p>
    </div>
    <div class="hidden" data-secret="{PLINIAN_DIVIDER}" id="steg-payload">
        {encoded}
    </div>
    <noscript><!-- hex:{hex_encoded} --></noscript>
</body>
</html>'''

    path = os.path.join(OUTPUT_DIR, 'example_hidden.html')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"    -> {path}")
    return path


# =============================================================================
# 21. XML with hidden data
# =============================================================================

def generate_xml_hidden():
    """Create an XML file with the Plinian divider in comments, PIs, and CDATA."""
    print("  Generating XML with hidden data...")
    import base64

    encoded = base64.b64encode(PLINIAN_DIVIDER.encode('utf-8')).decode()
    hex_encoded = PLINIAN_DIVIDER.encode('utf-8').hex()

    xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<?steg-payload {encoded}?>
<!-- {PLINIAN_DIVIDER} -->
<dinosaurs xmlns:steg="http://st3gg.example.com/steg"
           steg:payload="{hex_encoded}">
    <species name="Stegosaurus" period="Late Jurassic">
        <description>Large herbivorous thyreophoran dinosaur</description>
        <weight unit="kg">5000</weight>
        <length unit="m">9</length>
        <features>
            <feature>Dorsal plates</feature>
            <feature>Thagomizer (tail spikes)</feature>
            <feature>Small brain cavity</feature>
        </features>
        <hidden><![CDATA[{PLINIAN_DIVIDER}]]></hidden>
    </species>
    <species name="Ankylosaurus" period="Late Cretaceous">
        <description>Armored dinosaur with club tail</description>
        <weight unit="kg">6000</weight>
        <length unit="m">7</length>
    </species>
    <!-- base64:{encoded} -->
</dinosaurs>'''

    path = os.path.join(OUTPUT_DIR, 'example_hidden.xml')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(xml)
    print(f"    -> {path}")
    return path


# =============================================================================
# 22. JSON with Unicode escape sequences
# =============================================================================

def generate_json_hidden():
    """Create a JSON file with the Plinian divider hidden in Unicode escapes."""
    print("  Generating JSON with hidden Unicode escapes...")
    import json
    import base64

    # Encode as Unicode escape sequences
    unicode_escaped = ''.join(f'\\u{ord(c):04x}' if ord(c) < 0x10000
                              else f'\\U{ord(c):08x}' for c in PLINIAN_DIVIDER)

    data = {
        "title": "Steganography Example Dataset",
        "version": "3.0",
        "generator": "STEGOSAURUS WRECKS",
        "specimens": [
            {
                "name": "Stegosaurus stenops",
                "period": "Late Jurassic",
                "mya": [155, 150],
                "diet": "herbivore",
                "mass_kg": 5000
            },
            {
                "name": "Stegosaurus ungulatus",
                "period": "Late Jurassic",
                "mya": [155, 145],
                "diet": "herbivore",
                "mass_kg": 5500
            }
        ],
        "_metadata": {
            "comment": "Standard paleontology dataset",
            "encoding": "UTF-8",
            "payload_b64": base64.b64encode(PLINIAN_DIVIDER.encode('utf-8')).decode(),
            "payload_hex": PLINIAN_DIVIDER.encode('utf-8').hex(),
            "payload_direct": PLINIAN_DIVIDER
        }
    }

    path = os.path.join(OUTPUT_DIR, 'example_hidden.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"    -> {path}")
    return path


# =============================================================================
# 23. CSV with whitespace-encoded steganography
# =============================================================================

def generate_csv_hidden():
    """Create a CSV with the Plinian divider hidden in trailing whitespace."""
    print("  Generating CSV with whitespace steganography...")

    msg_bytes = PLINIAN_DIVIDER.encode('utf-8')
    length_bits = format(len(msg_bytes), '016b')
    data_bits = ''.join(format(b, '08b') for b in msg_bytes)
    all_bits = length_bits + data_bits

    rows = [
        ["Species", "Period", "Length_m", "Mass_kg", "Diet"],
        ["Stegosaurus", "Late Jurassic", "9.0", "5000", "Herbivore"],
        ["Triceratops", "Late Cretaceous", "9.0", "6000", "Herbivore"],
        ["Tyrannosaurus", "Late Cretaceous", "12.3", "8400", "Carnivore"],
        ["Velociraptor", "Late Cretaceous", "2.0", "15", "Carnivore"],
        ["Brachiosaurus", "Late Jurassic", "26.0", "56000", "Herbivore"],
        ["Ankylosaurus", "Late Cretaceous", "6.5", "6000", "Herbivore"],
        ["Parasaurolophus", "Late Cretaceous", "9.5", "2500", "Herbivore"],
        ["Diplodocus", "Late Jurassic", "26.0", "16000", "Herbivore"],
        ["Allosaurus", "Late Jurassic", "8.5", "2300", "Carnivore"],
        ["Spinosaurus", "Late Cretaceous", "15.0", "7400", "Piscivore"],
        ["Pachycephalosaurus", "Late Cretaceous", "4.5", "450", "Herbivore"],
        ["Carnotaurus", "Late Cretaceous", "8.0", "1500", "Carnivore"],
        ["Iguanodon", "Early Cretaceous", "10.0", "3400", "Herbivore"],
        ["Pteranodon", "Late Cretaceous", "6.0", "25", "Piscivore"],
        ["Deinonychus", "Early Cretaceous", "3.4", "73", "Carnivore"],
        ["Apatosaurus", "Late Jurassic", "21.0", "23000", "Herbivore"],
        ["Compsognathus", "Late Jurassic", "1.0", "3", "Carnivore"],
        ["Gallimimus", "Late Cretaceous", "6.0", "440", "Omnivore"],
        ["Therizinosaurus", "Late Cretaceous", "10.0", "5000", "Herbivore"],
        ["Archaeopteryx", "Late Jurassic", "0.5", "1", "Carnivore"],
        ["Baryonyx", "Early Cretaceous", "10.0", "1700", "Piscivore"],
        ["Coelophysis", "Late Triassic", "3.0", "30", "Carnivore"],
        ["Dilophosaurus", "Early Jurassic", "7.0", "400", "Carnivore"],
        ["Giganotosaurus", "Late Cretaceous", "13.0", "6800", "Carnivore"],
        ["Edmontosaurus", "Late Cretaceous", "13.0", "4000", "Herbivore"],
        ["Protoceratops", "Late Cretaceous", "1.8", "83", "Herbivore"],
        ["Oviraptor", "Late Cretaceous", "2.0", "33", "Omnivore"],
        ["Maiasaura", "Late Cretaceous", "9.0", "3000", "Herbivore"],
        ["Kentrosaurus", "Late Jurassic", "4.5", "1600", "Herbivore"],
        ["Plateosaurus", "Late Triassic", "8.0", "1500", "Herbivore"],
        ["Ceratosaurus", "Late Jurassic", "6.0", "980", "Carnivore"],
        ["Megalosaurus", "Middle Jurassic", "9.0", "1400", "Carnivore"],
        ["Corythosaurus", "Late Cretaceous", "9.0", "3800", "Herbivore"],
        ["Lambeosaurus", "Late Cretaceous", "9.4", "5600", "Herbivore"],
        ["Styracosaurus", "Late Cretaceous", "5.5", "2700", "Herbivore"],
        ["Dracorex", "Late Cretaceous", "3.0", "450", "Herbivore"],
        ["Microraptor", "Early Cretaceous", "0.8", "1", "Carnivore"],
        ["Psittacosaurus", "Early Cretaceous", "2.0", "20", "Herbivore"],
        ["Sauropelta", "Early Cretaceous", "5.0", "1500", "Herbivore"],
        ["Nodosaurus", "Late Cretaceous", "6.0", "3500", "Herbivore"],
        ["Euoplocephalus", "Late Cretaceous", "6.0", "2000", "Herbivore"],
        ["Citipati", "Late Cretaceous", "2.9", "75", "Omnivore"],
        ["Ornithomimus", "Late Cretaceous", "3.5", "170", "Omnivore"],
        ["Struthiomimus", "Late Cretaceous", "4.3", "150", "Omnivore"],
        ["Dromaeosaurus", "Late Cretaceous", "2.0", "15", "Carnivore"],
        ["Utahraptor", "Early Cretaceous", "6.0", "500", "Carnivore"],
        ["Suchomimus", "Early Cretaceous", "11.0", "3800", "Piscivore"],
        ["Irritator", "Early Cretaceous", "8.0", "1000", "Piscivore"],
        ["Carcharodontosaurus", "Late Cretaceous", "12.0", "6200", "Carnivore"],
        ["Acrocanthosaurus", "Early Cretaceous", "11.5", "5200", "Carnivore"],
        ["Torvosaurus", "Late Jurassic", "10.0", "3600", "Carnivore"],
        ["Camarasaurus", "Late Jurassic", "18.0", "18000", "Herbivore"],
        ["Amargasaurus", "Early Cretaceous", "10.0", "8000", "Herbivore"],
        ["Nigersaurus", "Early Cretaceous", "9.0", "4000", "Herbivore"],
        ["Dreadnoughtus", "Late Cretaceous", "26.0", "65000", "Herbivore"],
        ["Argentinosaurus", "Late Cretaceous", "30.0", "73000", "Herbivore"],
        ["Patagotitan", "Late Cretaceous", "31.0", "69000", "Herbivore"],
        ["Mamenchisaurus", "Late Jurassic", "22.0", "18000", "Herbivore"],
        ["Shunosaurus", "Middle Jurassic", "11.0", "3000", "Herbivore"],
        ["Tuojiangosaurus", "Late Jurassic", "7.0", "4000", "Herbivore"],
        ["Wuerhosaurus", "Early Cretaceous", "7.0", "4000", "Herbivore"],
        ["Huayangosaurus", "Middle Jurassic", "4.5", "500", "Herbivore"],
        ["Dacentrurus", "Late Jurassic", "8.0", "5000", "Herbivore"],
        ["Lexovisaurus", "Middle Jurassic", "6.0", "2000", "Herbivore"],
        ["Chungkingosaurus", "Late Jurassic", "4.0", "1000", "Herbivore"],
        ["Miragaia", "Late Jurassic", "6.5", "2000", "Herbivore"],
        ["Jiangjunosaurus", "Late Jurassic", "6.0", "2500", "Herbivore"],
        ["Hesperosaurus", "Late Jurassic", "6.5", "3500", "Herbivore"],
        ["Loricatosaurus", "Middle Jurassic", "6.0", "2000", "Herbivore"],
        ["Paranthodon", "Early Cretaceous", "5.0", "900", "Herbivore"],
        ["Regnosaurus", "Early Cretaceous", "4.5", "800", "Herbivore"],
        ["Dravidosaurus", "Late Cretaceous", "3.0", "500", "Herbivore"],
        ["Craterosaurus", "Early Cretaceous", "4.0", "700", "Herbivore"],
    ]

    bit_index = 0
    lines = []
    for row in rows:
        line = ','.join(row)
        trailing = ''
        for _ in range(8):
            if bit_index < len(all_bits):
                trailing += ' ' if all_bits[bit_index] == '0' else '\t'
                bit_index += 1
        lines.append(line + trailing)

    path = os.path.join(OUTPUT_DIR, 'example_whitespace.csv')
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print(f"    -> {path} ({bit_index} bits hidden)")
    return path


# =============================================================================
# 24. YAML with comment-based encoding
# =============================================================================

def generate_yaml_hidden():
    """Create a YAML file with the Plinian divider hidden in comments."""
    print("  Generating YAML with comment steganography...")
    import base64

    encoded = base64.b64encode(PLINIAN_DIVIDER.encode('utf-8')).decode()
    hex_encoded = PLINIAN_DIVIDER.encode('utf-8').hex()

    # Encode each byte as a YAML comment with a seemingly innocent hex value
    msg_bytes = PLINIAN_DIVIDER.encode('utf-8')
    hex_comments = []
    for i, b in enumerate(msg_bytes):
        hex_comments.append(f"  # ref-{i:03d}: 0x{b:02x}")

    yaml = f'''# Paleontology Specimen Database
# Generated by STEGOSAURUS WRECKS
# {PLINIAN_DIVIDER}

database:
  name: "DinoTracker"
  version: "3.0"
  encoding: "UTF-8"

specimens:
  - name: "Stegosaurus stenops"
    classification:
      order: Ornithischia
      family: Stegosauridae  # b64:{encoded}
    period: "Late Jurassic"
    location: "Morrison Formation, USA"
    measurements:
      length_m: 9.0
      height_m: 4.0
      mass_kg: 5000

  - name: "Triceratops horridus"
    classification:
      order: Ornithischia
      family: Ceratopsidae
    period: "Late Cretaceous"  # hex:{hex_encoded}
    location: "Hell Creek Formation, USA"
    measurements:
      length_m: 9.0
      height_m: 3.0
      mass_kg: 6000

  - name: "Tyrannosaurus rex"
    classification:
      order: Saurischia
      family: Tyrannosauridae
    period: "Late Cretaceous"
    location: "Western North America"
    measurements:
      length_m: 12.3
      height_m: 4.0
      mass_kg: 8400

# Byte reference table (calibration data)
{chr(10).join(hex_comments)}

metadata:
  payload: "{PLINIAN_DIVIDER}"
  source: "ST3GG steganography toolkit"
'''

    path = os.path.join(OUTPUT_DIR, 'example_hidden.yaml')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(yaml)
    print(f"    -> {path}")
    return path


# =============================================================================
# 25. PDF with hidden stream
# =============================================================================

def generate_pdf_hidden():
    """Create a minimal PDF with the Plinian divider hidden in metadata and streams."""
    print("  Generating PDF with hidden stream data...")
    import base64

    encoded = base64.b64encode(PLINIAN_DIVIDER.encode('utf-8')).decode()
    secret_bytes = PLINIAN_DIVIDER.encode('utf-8')

    # Build a minimal valid PDF manually
    objects = []

    # Object 1: Catalog
    objects.append(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R /Metadata 5 0 R >>\nendobj\n")

    # Object 2: Pages
    objects.append(b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n")

    # Object 3: Page
    page_content = b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << >> >>\nendobj\n"
    objects.append(page_content)

    # Object 4: Content stream with visible text and hidden comment
    stream_data = (
        f"BT\n/F1 16 Tf\n100 700 Td\n(ST3GG Steganography Example) Tj\n"
        f"0 -30 Td\n/F1 11 Tf\n(This PDF contains hidden data.) Tj\n"
        f"0 -20 Td\n(Look in the metadata and streams...) Tj\nET\n"
        f"% Hidden: {PLINIAN_DIVIDER}\n"
    ).encode('utf-8')
    objects.append(f"4 0 obj\n<< /Length {len(stream_data)} >>\nstream\n".encode() +
                   stream_data + b"\nendstream\nendobj\n")

    # Object 5: Metadata stream with hidden Plinian divider
    meta_xml = f'''<?xpacket begin="\xef\xbb\xbf" id="W5M0MpCehiHzreSzNTczkc9d"?>
<x:xmpmeta xmlns:x="adobe:ns:meta/">
  <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
           xmlns:dc="http://purl.org/dc/elements/1.1/"
           xmlns:steg="http://st3gg.example.com/ns/">
    <rdf:Description>
      <dc:title>ST3GG Example</dc:title>
      <dc:creator>STEGOSAURUS WRECKS</dc:creator>
      <dc:description>{PLINIAN_DIVIDER}</dc:description>
      <steg:payload>{encoded}</steg:payload>
      <steg:hex>{secret_bytes.hex()}</steg:hex>
    </rdf:Description>
  </rdf:RDF>
</x:xmpmeta>
<?xpacket end="w"?>'''.encode('utf-8')
    objects.append(f"5 0 obj\n<< /Type /Metadata /Subtype /XML /Length {len(meta_xml)} >>\nstream\n".encode() +
                   meta_xml + b"\nendstream\nendobj\n")

    # Object 6: Info dictionary
    objects.append(f'6 0 obj\n<< /Title (ST3GG Example) /Author (STEGOSAURUS WRECKS) /Subject ({PLINIAN_DIVIDER}) /Producer (ST3GG v3.0) /Keywords ({encoded}) >>\nendobj\n'.encode('utf-8'))

    # Build the PDF
    pdf = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"
    offsets = []
    for obj in objects:
        offsets.append(len(pdf))
        pdf += obj

    # Cross-reference table
    xref_offset = len(pdf)
    pdf += b"xref\n"
    pdf += f"0 {len(objects) + 1}\n".encode()
    pdf += b"0000000000 65535 f \n"
    for offset in offsets:
        pdf += f"{offset:010d} 00000 n \n".encode()

    # Trailer
    pdf += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R /Info 6 0 R >>\n".encode()
    pdf += f"startxref\n{xref_offset}\n%%EOF\n".encode()

    # Append hidden data after EOF (common steganography technique)
    pdf += f"\n% HIDDEN AFTER EOF: {PLINIAN_DIVIDER}\n".encode('utf-8')
    pdf += secret_bytes

    path = os.path.join(OUTPUT_DIR, 'example_hidden.pdf')
    with open(path, 'wb') as f:
        f.write(pdf)
    print(f"    -> {path}")
    return path


# =============================================================================
# 26. RTF with hidden groups
# =============================================================================

def generate_rtf_hidden():
    """Create an RTF file with the Plinian divider in hidden text and metadata."""
    print("  Generating RTF with hidden groups...")

    # RTF hex encoding of secret
    secret_bytes = PLINIAN_DIVIDER.encode('utf-8')
    hex_chars = ''.join(f"\\'{b:02x}" for b in secret_bytes)

    rtf = (
        r"{\rtf1\ansi\deff0"
        r"{\fonttbl{\f0 Courier New;}}"
        r"{\colortbl;\red0\green0\blue0;\red200\green100\blue255;}"
        "\n"
        # Info group with hidden payload
        r"{\info"
        r"{\title ST3GG Steganography Example}"
        r"{\author STEGOSAURUS WRECKS}"
        r"{\subject " + PLINIAN_DIVIDER + r"}"
        r"{\doccomm Hidden payload: " + secret_bytes.hex() + r"}"
        r"}" "\n"
        # Visible content
        r"\f0\fs22\cf1 "
        r"{\b ST3GG Steganography Example}\par\par"
        r"This RTF document contains hidden data in multiple locations:\par"
        r"- Document info/metadata fields\par"
        r"- Hidden text runs (\\v flag)\par"
        r"- Hex-encoded byte sequences\par\par"
        r"The secret is concealed using RTF's native formatting capabilities.\par\par"
        # Hidden text (invisible in most readers with \v flag)
        r"{\v " + hex_chars + r"}"
        r"{\v  PLINIAN DIVIDER ENCODED ABOVE}"
        "\n"
        # Bookmark with hidden data
        r"{\*\bkmkstart steg_payload}" + PLINIAN_DIVIDER + r"{\*\bkmkend steg_payload}"
        "\n"
        r"}"
    )

    path = os.path.join(OUTPUT_DIR, 'example_hidden.rtf')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(rtf)
    print(f"    -> {path}")
    return path


# =============================================================================
# 27. Markdown with HTML comment encoding
# =============================================================================

def generate_markdown_hidden():
    """Create a Markdown file with the Plinian divider in HTML comments and zero-width chars."""
    print("  Generating Markdown with hidden content...")
    import base64

    encoded = base64.b64encode(PLINIAN_DIVIDER.encode('utf-8')).decode()
    hex_encoded = PLINIAN_DIVIDER.encode('utf-8').hex()

    # Zero-width encoding
    ZWSP = '\u200B'
    ZWNJ = '\u200C'
    ZWJ = '\u200D'
    secret_bytes = PLINIAN_DIVIDER.encode('utf-8')
    binary_str = ''.join(format(b, '08b') for b in secret_bytes)
    zw_string = ZWJ
    for bit in binary_str:
        zw_string += ZWSP if bit == '0' else ZWNJ
    zw_string += ZWJ

    md = f'''# Steganography: A Brief History

<!-- {PLINIAN_DIVIDER} -->

{zw_string}Steganography, from the Greek words *steganos* (covered) and *graphein*
(to write), is the practice of concealing messages within other non-secret data.

## Ancient Origins

The earliest recorded use of steganography dates back to **440 BC**, when
Histiaeus shaved a slave's head, tattooed a message on his scalp, and waited
for the hair to regrow before sending him as a messenger.

<!-- base64:{encoded} -->

## Digital Era

Modern digital steganography encompasses a wide range of techniques:

| Technique | Medium | Capacity | Stealth |
|-----------|--------|----------|---------|
| LSB Embedding | Images | High | Medium |
| DCT Domain | JPEG | Medium | High |
| Whitespace | Text | Low | High |
| Zero-Width | Text | Low | Very High |
| Audio LSB | Audio | Medium | High |
| Metadata | Any | Low | Medium |

## Tools

**ST3GG (STEGOSAURUS WRECKS)** is an advanced steganography toolkit supporting
15 channel presets, 8 bit depths, and 4 encoding strategies.

<!-- hex:{hex_encoded} -->

[comment]: # ({PLINIAN_DIVIDER})

---
*Generated by STEGOSAURUS WRECKS v3.0*
'''

    path = os.path.join(OUTPUT_DIR, 'example_hidden.md')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(md)
    print(f"    -> {path}")
    return path


# =============================================================================
# 28. AIFF with LSB steganography
# =============================================================================

def generate_aiff_lsb():
    """Create an AIFF audio file with the Plinian divider hidden in sample LSBs."""
    print("  Generating AIFF with LSB steganography...")
    import math

    sample_rate = 22050
    duration = 2  # seconds
    num_samples = sample_rate * duration
    num_channels = 1
    bits_per_sample = 16

    # Generate a tone
    frequency = 523.25  # C5
    samples = []
    for i in range(num_samples):
        t = i / sample_rate
        value = 0.6 * math.sin(2 * math.pi * frequency * t)
        value += 0.2 * math.sin(2 * math.pi * frequency * 2 * t)
        sample = int(value * 16000)
        sample = max(-32768, min(32767, sample))
        samples.append(sample)

    # Encode Plinian divider in LSB
    msg = PLINIAN_DIVIDER.encode('utf-8')
    length_bytes = struct.pack('>I', len(msg))
    payload = length_bytes + msg
    bits = []
    for byte in payload:
        for j in range(7, -1, -1):
            bits.append((byte >> j) & 1)

    for i, bit in enumerate(bits):
        if i < len(samples):
            s = samples[i]
            u = s & 0xFFFF
            u = (u & 0xFFFE) | bit
            samples[i] = u if u < 32768 else u - 65536

    # Build AIFF file manually (big-endian)
    # AIFF uses big-endian 16-bit samples
    sample_data = struct.pack(f'>{len(samples)}h', *samples)

    # IEEE 754 80-bit extended for sample rate
    def float_to_extended(val):
        """Convert float to 80-bit IEEE 754 extended precision (big-endian)."""
        if val == 0:
            return b'\x00' * 10
        import math as m
        sign = 0
        if val < 0:
            sign = 1
            val = -val
        exp = int(m.floor(m.log2(val)))
        mantissa = val / (2 ** exp)
        # Bias is 16383
        biased_exp = exp + 16383
        # Mantissa: 64-bit integer with explicit integer bit
        mant_int = int(mantissa * (2 ** 63))
        result = struct.pack('>HQ', (sign << 15) | (biased_exp & 0x7FFF), mant_int)
        return result

    # COMM chunk
    comm = b'COMM'
    comm_data = struct.pack('>hI', num_channels, num_samples)
    comm_data += struct.pack('>h', bits_per_sample)
    comm_data += float_to_extended(sample_rate)
    comm += struct.pack('>I', len(comm_data)) + comm_data

    # SSND chunk
    ssnd_data = struct.pack('>II', 0, 0) + sample_data  # offset + block size + data
    ssnd = b'SSND' + struct.pack('>I', len(ssnd_data)) + ssnd_data

    # ANNO chunk (annotation) with hidden message
    anno_text = f"Generated by ST3GG - {PLINIAN_DIVIDER}".encode('utf-8')
    if len(anno_text) % 2 != 0:
        anno_text += b'\x00'
    anno = b'ANNO' + struct.pack('>I', len(anno_text)) + anno_text

    # FORM header
    form_data = b'AIFF' + comm + anno + ssnd
    aiff = b'FORM' + struct.pack('>I', len(form_data)) + form_data

    path = os.path.join(OUTPUT_DIR, 'example_lsb.aiff')
    with open(path, 'wb') as f:
        f.write(aiff)
    print(f"    -> {path} ({len(bits)} bits embedded)")
    return path


# =============================================================================
# 29. AU (Sun/NeXT) audio with LSB steganography
# =============================================================================

def generate_au_lsb():
    """Create an AU audio file with the Plinian divider hidden in sample LSBs."""
    print("  Generating AU with LSB steganography...")
    import math

    sample_rate = 22050
    duration = 2
    num_samples = sample_rate * duration

    # Generate a different tone (A4 = 440Hz)
    frequency = 440.0
    samples = []
    for i in range(num_samples):
        t = i / sample_rate
        value = 0.5 * math.sin(2 * math.pi * frequency * t)
        value += 0.25 * math.sin(2 * math.pi * frequency * 3 * t)  # Add 3rd harmonic
        sample = int(value * 16000)
        sample = max(-32768, min(32767, sample))
        samples.append(sample)

    # Encode Plinian divider in LSB
    msg = PLINIAN_DIVIDER.encode('utf-8')
    length_bytes = struct.pack('>I', len(msg))
    payload = length_bytes + msg
    bits = []
    for byte in payload:
        for j in range(7, -1, -1):
            bits.append((byte >> j) & 1)

    for i, bit in enumerate(bits):
        if i < len(samples):
            s = samples[i]
            u = s & 0xFFFF
            u = (u & 0xFFFE) | bit
            samples[i] = u if u < 32768 else u - 65536

    # AU format: big-endian
    annotation = PLINIAN_DIVIDER.encode('utf-8')
    # Pad annotation to multiple of 4
    while len(annotation) % 4 != 0:
        annotation += b'\x00'
    header_size = 24 + len(annotation)

    sample_data = struct.pack(f'>{len(samples)}h', *samples)

    au = b'.snd'  # Magic
    au += struct.pack('>I', header_size)  # Data offset
    au += struct.pack('>I', len(sample_data))  # Data size
    au += struct.pack('>I', 3)  # Encoding: 16-bit linear PCM
    au += struct.pack('>I', sample_rate)
    au += struct.pack('>I', 1)  # Channels
    au += annotation
    au += sample_data

    path = os.path.join(OUTPUT_DIR, 'example_lsb.au')
    with open(path, 'wb') as f:
        f.write(au)
    print(f"    -> {path} ({len(bits)} bits embedded)")
    return path


# =============================================================================
# 30. ZIP with comment steganography
# =============================================================================

def generate_zip_hidden():
    """Create a ZIP archive with the Plinian divider hidden in the archive comment."""
    print("  Generating ZIP with comment steganography...")
    import zipfile

    path = os.path.join(OUTPUT_DIR, 'example_hidden.zip')

    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Add some innocent-looking files
        zf.writestr('dinosaurs/stegosaurus.txt',
                     'Stegosaurus stenops\nLate Jurassic\nMorrison Formation\n')
        zf.writestr('dinosaurs/triceratops.txt',
                     'Triceratops horridus\nLate Cretaceous\nHell Creek Formation\n')
        zf.writestr('README.txt',
                     'Paleontology specimen data archive.\nGenerated by ST3GG.\n')

        # Hidden: Plinian divider as archive comment
        zf.comment = PLINIAN_DIVIDER.encode('utf-8')

    # Also append hidden data after the ZIP end
    with open(path, 'ab') as f:
        f.write(b'\n--- HIDDEN AFTER ZIP ---\n')
        f.write(PLINIAN_DIVIDER.encode('utf-8'))

    print(f"    -> {path}")
    return path


# =============================================================================
# 31. TAR with extended headers
# =============================================================================

def generate_tar_hidden():
    """Create a TAR archive with the Plinian divider in extended pax headers."""
    print("  Generating TAR with extended header steganography...")
    import tarfile
    import io
    import time

    path = os.path.join(OUTPUT_DIR, 'example_hidden.tar')

    with tarfile.open(path, 'w', format=tarfile.PAX_FORMAT) as tf:
        # Add a file with pax headers containing the secret
        data = b'Stegosaurus Facts\nLate Jurassic, 155-150 MYA\n'
        info = tarfile.TarInfo(name='specimens/stegosaurus.txt')
        info.size = len(data)
        info.mtime = int(time.time())
        info.pax_headers = {
            'comment': PLINIAN_DIVIDER,
            'STEG.payload': PLINIAN_DIVIDER.encode('utf-8').hex(),
            'STEG.generator': 'STEGOSAURUS WRECKS v3.0',
        }
        tf.addfile(info, io.BytesIO(data))

        # Second file
        data2 = b'Ankylosaurus Facts\nLate Cretaceous, 68-66 MYA\n'
        info2 = tarfile.TarInfo(name='specimens/ankylosaurus.txt')
        info2.size = len(data2)
        info2.mtime = int(time.time())
        tf.addfile(info2, io.BytesIO(data2))

    print(f"    -> {path}")
    return path


# =============================================================================
# 32. GZip with extra field steganography
# =============================================================================

def generate_gzip_hidden():
    """Create a GZip file with the Plinian divider in the extra field and comment."""
    print("  Generating GZip with extra field steganography...")

    content = (
        "Steganography Techniques Reference\n"
        "===================================\n\n"
        "LSB Embedding: Hide data in least significant bits of pixel values.\n"
        "DCT Domain: Embed in frequency-domain coefficients for JPEG survival.\n"
        "Metadata: Store secrets in file metadata fields.\n"
        "Appended Data: Add data after file end markers.\n"
        "Whitespace: Encode in trailing spaces and tabs.\n"
        "Zero-Width: Use invisible Unicode characters.\n"
    ).encode('utf-8')

    secret = PLINIAN_DIVIDER.encode('utf-8')

    # Build gzip manually to include FEXTRA and FCOMMENT fields
    # Gzip header
    gz = b'\x1f\x8b'  # Magic
    gz += b'\x08'      # Compression: deflate
    flags = 0x04 | 0x10  # FEXTRA | FCOMMENT
    gz += bytes([flags])
    gz += struct.pack('<I', int(__import__('time').time()))  # mtime
    gz += b'\x00'      # Extra flags
    gz += b'\xff'      # OS: unknown

    # FEXTRA field containing the secret
    extra_data = b'ST' + struct.pack('<H', len(secret)) + secret  # subfield ID + len + data
    gz += struct.pack('<H', len(extra_data))
    gz += extra_data

    # FCOMMENT (null-terminated)
    gz += PLINIAN_DIVIDER.encode('latin-1', errors='replace') + b'\x00'

    # Compressed data
    compressed = zlib.compress(content, 9)[2:-4]  # Strip zlib header/trailer for raw deflate
    gz += compressed

    # CRC32 and size
    gz += struct.pack('<I', zlib.crc32(content) & 0xFFFFFFFF)
    gz += struct.pack('<I', len(content) & 0xFFFFFFFF)

    path = os.path.join(OUTPUT_DIR, 'example_hidden.gz')
    with open(path, 'wb') as f:
        f.write(gz)
    print(f"    -> {path}")
    return path


# =============================================================================
# 33. SQLite database with hidden data
# =============================================================================

def generate_sqlite_hidden():
    """Create a SQLite database with the Plinian divider in hidden tables and metadata."""
    print("  Generating SQLite with hidden data...")
    import sqlite3

    path = os.path.join(OUTPUT_DIR, 'example_hidden.sqlite')
    if os.path.exists(path):
        os.remove(path)

    conn = sqlite3.connect(path)
    c = conn.cursor()

    # Create a visible table
    c.execute('''CREATE TABLE specimens (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        period TEXT,
        length_m REAL,
        mass_kg REAL,
        diet TEXT
    )''')
    specimens = [
        (1, 'Stegosaurus', 'Late Jurassic', 9.0, 5000, 'Herbivore'),
        (2, 'Triceratops', 'Late Cretaceous', 9.0, 6000, 'Herbivore'),
        (3, 'Tyrannosaurus', 'Late Cretaceous', 12.3, 8400, 'Carnivore'),
        (4, 'Velociraptor', 'Late Cretaceous', 2.0, 15, 'Carnivore'),
        (5, 'Brachiosaurus', 'Late Jurassic', 26.0, 56000, 'Herbivore'),
    ]
    c.executemany('INSERT INTO specimens VALUES (?,?,?,?,?,?)', specimens)

    # Hidden table with the Plinian divider
    c.execute('''CREATE TABLE _steg_payload (
        key TEXT PRIMARY KEY,
        value TEXT
    )''')
    import base64
    c.execute('INSERT INTO _steg_payload VALUES (?, ?)',
              ('divider', PLINIAN_DIVIDER))
    c.execute('INSERT INTO _steg_payload VALUES (?, ?)',
              ('divider_b64', base64.b64encode(PLINIAN_DIVIDER.encode('utf-8')).decode()))
    c.execute('INSERT INTO _steg_payload VALUES (?, ?)',
              ('divider_hex', PLINIAN_DIVIDER.encode('utf-8').hex()))

    # Also set the application_id to encode part of the message
    c.execute(f"PRAGMA application_id = {0x53544547}")  # 'STEG' in hex

    conn.commit()
    conn.close()
    print(f"    -> {path}")
    return path


# =============================================================================
# 34. Raw hex dump file
# =============================================================================

def generate_hexdump_hidden():
    """Create a hex dump file with the Plinian divider hidden in the ASCII column."""
    print("  Generating hex dump with hidden data...")

    secret = PLINIAN_DIVIDER.encode('utf-8')

    # Create a fake hex dump of "random" data that contains the secret
    # embedded within the raw bytes
    import random
    random.seed(42)

    # Generate surrounding data with secret embedded at offset 0x40
    total_size = 256
    data = bytearray(random.getrandbits(8) for _ in range(total_size))

    # Embed secret at offset 0x40
    embed_offset = 0x40
    for i, b in enumerate(secret):
        if embed_offset + i < total_size:
            data[embed_offset + i] = b

    # Format as hex dump
    lines = []
    lines.append("# ST3GG Hex Dump - Memory Analysis Output")
    lines.append("# Generated by STEGOSAURUS WRECKS v3.0")
    lines.append(f"# Payload offset: 0x{embed_offset:04x}")
    lines.append(f"# Payload size: {len(secret)} bytes")
    lines.append("")

    for offset in range(0, len(data), 16):
        chunk = data[offset:offset + 16]
        hex_part = ' '.join(f'{b:02x}' for b in chunk)
        hex_part = hex_part.ljust(47)
        ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
        lines.append(f"{offset:08x}  {hex_part}  |{ascii_part}|")

    lines.append("")
    lines.append(f"# Total: {len(data)} bytes")

    path = os.path.join(OUTPUT_DIR, 'example_hidden.hexdump')
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print(f"    -> {path}")
    return path


# =============================================================================
# 35. MIDI with SysEx steganography
# =============================================================================

def generate_midi_hidden():
    """Create a MIDI file with the Plinian divider hidden in SysEx messages."""
    print("  Generating MIDI with SysEx steganography...")

    secret = PLINIAN_DIVIDER.encode('utf-8')
    # MIDI SysEx can only carry 7-bit data, so encode as pairs
    sysex_data = bytearray()
    for b in secret:
        sysex_data.append(b >> 4)    # High nibble (always < 16, so 7-bit safe)
        sysex_data.append(b & 0x0F)  # Low nibble

    def var_len(value):
        """Encode a variable-length quantity for MIDI."""
        result = bytearray()
        result.append(value & 0x7F)
        value >>= 7
        while value > 0:
            result.append((value & 0x7F) | 0x80)
            value >>= 7
        result.reverse()
        return bytes(result)

    # Build MIDI file
    # Header chunk
    header = b'MThd'
    header += struct.pack('>I', 6)  # Chunk length
    header += struct.pack('>HHH', 0, 1, 480)  # Format 0, 1 track, 480 ticks/beat

    # Track chunk
    track_data = bytearray()

    # Tempo: 120 BPM (500000 microseconds per beat)
    track_data += b'\x00\xFF\x51\x03\x07\xA1\x20'

    # Text event with the divider
    text = f"ST3GG: {PLINIAN_DIVIDER}".encode('utf-8')
    track_data += b'\x00\xFF\x01' + var_len(len(text)).encode('latin-1') if False else b''
    track_data += b'\x00\xFF\x01'
    track_data += bytes(var_len(len(text)))
    track_data += text

    # SysEx message containing encoded secret
    # Manufacturer ID 0x7D = non-commercial/educational use
    sysex_payload = bytes([0x7D]) + bytes(sysex_data)
    track_data += b'\x00\xF0'
    track_data += bytes(var_len(len(sysex_payload) + 1))  # +1 for F7 terminator
    track_data += sysex_payload
    track_data += b'\xF7'

    # Play a simple melody (C major scale)
    notes = [60, 62, 64, 65, 67, 69, 71, 72]  # C4 to C5
    for note in notes:
        track_data += b'\x00'                          # Delta time
        track_data += bytes([0x90, note, 0x50])        # Note On, velocity 80
        track_data += bytes(var_len(480))               # Wait 1 beat
        track_data += bytes([0x80, note, 0x40])        # Note Off

    # End of track
    track_data += b'\x00\xFF\x2F\x00'

    track = b'MTrk' + struct.pack('>I', len(track_data)) + bytes(track_data)

    path = os.path.join(OUTPUT_DIR, 'example_hidden.mid')
    with open(path, 'wb') as f:
        f.write(header + track)
    print(f"    -> {path}")
    return path


# =============================================================================
# 36. PCAP-like network capture with hidden data
# =============================================================================

def generate_pcap_hidden():
    """Create a PCAP file with the Plinian divider hidden in packet payloads."""
    print("  Generating PCAP with hidden packet data...")

    secret = PLINIAN_DIVIDER.encode('utf-8')
    import time

    # PCAP global header
    pcap = struct.pack('<IHHiIII',
        0xa1b2c3d4,  # Magic
        2, 4,        # Version 2.4
        0,           # Timezone (GMT)
        0,           # Sigfigs
        65535,       # Snaplen
        1,           # Link type: Ethernet
    )

    def make_packet(src_ip, dst_ip, payload, ts_sec):
        """Build a simple UDP packet wrapped in Ethernet + IP headers."""
        # UDP header
        src_port, dst_port = 12345, 53
        udp_len = 8 + len(payload)
        udp = struct.pack('>HHHH', src_port, dst_port, udp_len, 0)
        udp += payload

        # IP header (simplified, no checksum)
        ip_len = 20 + len(udp)
        ip_header = struct.pack('>BBHHHBBH4s4s',
            0x45, 0, ip_len,  # Version, IHL, TOS, Total length
            0x1234, 0x4000,   # ID, Flags+Fragment
            64, 17, 0,        # TTL, Protocol (UDP), Checksum
            bytes(map(int, src_ip.split('.'))),
            bytes(map(int, dst_ip.split('.'))),
        )

        # Ethernet header
        eth = b'\x00' * 6 + b'\x00' * 6 + b'\x08\x00'  # dst + src + type (IP)
        frame = eth + ip_header + udp

        # PCAP packet header
        pkt_len = len(frame)
        pkt_header = struct.pack('<IIII', ts_sec, 0, pkt_len, pkt_len)
        return pkt_header + frame

    ts = int(time.time())
    # Normal-looking DNS query packets, with the secret split across them
    chunk_size = len(secret) // 4 + 1
    packets = []
    for i in range(4):
        chunk = secret[i * chunk_size:(i + 1) * chunk_size]
        if chunk:
            packets.append(make_packet(
                f'192.168.1.{10 + i}', '8.8.8.8',
                chunk, ts + i
            ))
    # Also include the full secret in one packet
    packets.append(make_packet('10.0.0.1', '10.0.0.2', secret, ts + 5))

    for pkt in packets:
        pcap += pkt

    path = os.path.join(OUTPUT_DIR, 'example_hidden.pcap')
    with open(path, 'wb') as f:
        f.write(pcap)
    print(f"    -> {path}")
    return path


# =============================================================================
# 37. Python with steganographic comments
# =============================================================================

def generate_python_hidden():
    """Create a Python file with the Plinian divider hidden in comments and docstrings."""
    print("  Generating Python with hidden comments...")
    import base64

    encoded = base64.b64encode(PLINIAN_DIVIDER.encode('utf-8')).decode()
    hex_encoded = PLINIAN_DIVIDER.encode('utf-8').hex()

    # Zero-width encoding
    ZWSP = '\u200B'
    ZWNJ = '\u200C'
    ZWJ = '\u200D'
    secret_bytes = PLINIAN_DIVIDER.encode('utf-8')
    binary_str = ''.join(format(b, '08b') for b in secret_bytes)
    zw_string = ZWJ + ''.join(ZWSP if bit == '0' else ZWNJ for bit in binary_str) + ZWJ

    # Encode each byte as a hex comment spread across the file
    byte_comments = [f"    # cfg[{i}] = 0x{b:02x}" for i, b in enumerate(secret_bytes)]

    py = f'''#!/usr/bin/env python3
"""
Paleontology Specimen Analyzer
{zw_string}
A tool for analyzing dinosaur fossil measurements and classifications.
"""

# {PLINIAN_DIVIDER}
# Configuration hash: {hex_encoded}

import math
from dataclasses import dataclass
from typing import Optional


@dataclass
class Specimen:
    """Represents a dinosaur specimen record."""
    name: str
    period: str
    length_m: float
    mass_kg: float
    diet: str
    brain_volume_cc: Optional[float] = None


# Calibration byte table (do not modify)
{chr(10).join(byte_comments)}


def calculate_brain_body_ratio(specimen: Specimen) -> float:
    """Calculate the encephalization quotient (EQ) for a specimen."""
    if specimen.brain_volume_cc is None:
        return 0.0
    # EQ = brain mass / (0.12 * body_mass^0.67)
    expected = 0.12 * (specimen.mass_kg ** 0.67)
    return specimen.brain_volume_cc / expected


def classify_intelligence(eq: float) -> str:
    """Classify relative intelligence based on EQ."""
    if eq > 1.0:
        return "above average"
    elif eq > 0.5:
        return "average"
    else:
        return "below average"


# Payload verification: {encoded}
SPECIMENS = [
    Specimen("Stegosaurus", "Late Jurassic", 9.0, 5000, "Herbivore", 2.8),
    Specimen("Triceratops", "Late Cretaceous", 9.0, 6000, "Herbivore", 70.0),
    Specimen("T. rex", "Late Cretaceous", 12.3, 8400, "Carnivore", 343.0),
    Specimen("Velociraptor", "Late Cretaceous", 2.0, 15, "Carnivore", 15.0),
    Specimen("Brachiosaurus", "Late Jurassic", 26.0, 56000, "Herbivore", 26.0),
]


def main():
    """Analyze specimens and print results."""
    print("Paleontology Specimen Analysis")
    print("=" * 50)
    for spec in SPECIMENS:
        eq = calculate_brain_body_ratio(spec)
        intel = classify_intelligence(eq)
        print(f"  {{spec.name:20s}} EQ={{eq:.3f}} ({{intel}})")


if __name__ == "__main__":
    main()
'''

    path = os.path.join(OUTPUT_DIR, 'example_hidden.py')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(py)
    print(f"    -> {path}")
    return path


# =============================================================================
# 38. JavaScript with zero-width characters
# =============================================================================

def generate_js_hidden():
    """Create a JavaScript file with the Plinian divider in zero-width chars."""
    print("  Generating JavaScript with zero-width steganography...")
    import base64

    encoded = base64.b64encode(PLINIAN_DIVIDER.encode('utf-8')).decode()
    hex_encoded = PLINIAN_DIVIDER.encode('utf-8').hex()

    # Zero-width encoding
    ZWSP = '\u200B'
    ZWNJ = '\u200C'
    ZWJ = '\u200D'
    secret_bytes = PLINIAN_DIVIDER.encode('utf-8')
    binary_str = ''.join(format(b, '08b') for b in secret_bytes)
    zw_string = ZWJ + ''.join(ZWSP if bit == '0' else ZWNJ for bit in binary_str) + ZWJ

    js = f'''// Dinosaur Specimen Database Module
// {zw_string}

/**
 * @module specimen-db
 * @description Paleontology specimen management
 * @version 3.0.0
 * @license MIT
 */

// {PLINIAN_DIVIDER}

const SPECIMENS = [
  {{ name: "Stegosaurus",{zw_string} period: "Late Jurassic", lengthM: 9.0, massKg: 5000 }},
  {{ name: "Triceratops", period: "Late Cretaceous", lengthM: 9.0, massKg: 6000 }},
  {{ name: "Tyrannosaurus", period: "Late Cretaceous", lengthM: 12.3, massKg: 8400 }},
  {{ name: "Velociraptor", period: "Late Cretaceous", lengthM: 2.0, massKg: 15 }},
  {{ name: "Brachiosaurus", period: "Late Jurassic", lengthM: 26.0, massKg: 56000 }},
];

// Internal config hash: {hex_encoded}

/**
 * Calculate body mass index for a specimen
 * @param {{Object}} specimen - The specimen data
 * @returns {{number}} BMI estimate
 */
function calculateBMI(specimen) {{
  return specimen.massKg / (specimen.lengthM ** 2);
}}

/**
 * Search specimens by period
 * @param {{string}} period - Geological period name
 * @returns {{Array}} Matching specimens
 */
function findByPeriod(period) {{
  return SPECIMENS.filter(s => s.period.includes(period));
}}

// Verification: {encoded}

function printReport() {{
  console.log("Specimen Analysis Report");
  console.log("=".repeat(50));
  for (const spec of SPECIMENS) {{
    const bmi = calculateBMI(spec).toFixed(1);
    console.log(`  ${{spec.name.padEnd(20)}} BMI=${{bmi}} (${{spec.period}})`);
  }}
}}

if (typeof module !== "undefined") {{
  module.exports = {{ SPECIMENS, calculateBMI, findByPeriod, printReport }};
}}
'''

    path = os.path.join(OUTPUT_DIR, 'example_hidden.js')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(js)
    print(f"    -> {path}")
    return path


# =============================================================================
# 39. C source with steganographic comments
# =============================================================================

def generate_c_hidden():
    """Create a C source file with the Plinian divider hidden in comments."""
    print("  Generating C source with hidden comments...")
    import base64

    encoded = base64.b64encode(PLINIAN_DIVIDER.encode('utf-8')).decode()
    hex_bytes = PLINIAN_DIVIDER.encode('utf-8')

    # Build a C array of the secret bytes
    c_array = ', '.join(f'0x{b:02x}' for b in hex_bytes)

    c_src = f'''/*
 * specimen_analyzer.c - Paleontology Specimen Analysis Tool
 * Generated by STEGOSAURUS WRECKS v3.0
 *
 * {PLINIAN_DIVIDER}
 */

#include <stdio.h>
#include <string.h>
#include <math.h>

/* Calibration data (do not modify) */
static const unsigned char _cal_data[] = {{
    {c_array}
}};
static const size_t _cal_len = sizeof(_cal_data);

/* b64: {encoded} */

typedef struct {{
    const char *name;
    const char *period;
    double length_m;
    double mass_kg;
    const char *diet;
}} Specimen;

static const Specimen specimens[] = {{
    {{"Stegosaurus",    "Late Jurassic",    9.0,  5000.0, "Herbivore"}},
    {{"Triceratops",    "Late Cretaceous",  9.0,  6000.0, "Herbivore"}},
    {{"Tyrannosaurus",  "Late Cretaceous", 12.3,  8400.0, "Carnivore"}},
    {{"Velociraptor",   "Late Cretaceous",  2.0,    15.0, "Carnivore"}},
    {{"Brachiosaurus",  "Late Jurassic",   26.0, 56000.0, "Herbivore"}},
}};

#define NUM_SPECIMENS (sizeof(specimens) / sizeof(specimens[0]))

double calculate_density(const Specimen *s) {{
    /* Rough cylindrical body model */
    double radius = s->length_m / 6.0;
    double volume = M_PI * radius * radius * s->length_m;
    return s->mass_kg / volume;
}}

void print_analysis(void) {{
    printf("Specimen Density Analysis\\n");
    printf("%-20s %-18s %8s %10s\\n",
           "Name", "Period", "Mass(kg)", "Density");
    printf("%-20s %-18s %8s %10s\\n",
           "----", "------", "--------", "-------");

    for (size_t i = 0; i < NUM_SPECIMENS; i++) {{
        double d = calculate_density(&specimens[i]);
        printf("%-20s %-18s %8.0f %10.1f\\n",
               specimens[i].name, specimens[i].period,
               specimens[i].mass_kg, d);
    }}
}}

int main(void) {{
    print_analysis();
    /* Verify calibration data integrity */
    if (_cal_len > 0 && _cal_data[0] != 0) {{
        /* Calibration OK */
    }}
    return 0;
}}
'''

    path = os.path.join(OUTPUT_DIR, 'example_hidden.c')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(c_src)
    print(f"    -> {path}")
    return path


# =============================================================================
# 40. CSS with invisible selectors and comments
# =============================================================================

def generate_css_hidden():
    """Create a CSS file with the Plinian divider in comments and data URIs."""
    print("  Generating CSS with hidden selectors...")
    import base64

    encoded = base64.b64encode(PLINIAN_DIVIDER.encode('utf-8')).decode()
    hex_encoded = PLINIAN_DIVIDER.encode('utf-8').hex()

    # Zero-width encoding
    ZWSP = '\u200B'
    ZWNJ = '\u200C'
    ZWJ = '\u200D'
    secret_bytes = PLINIAN_DIVIDER.encode('utf-8')
    binary_str = ''.join(format(b, '08b') for b in secret_bytes)
    zw_string = ZWJ + ''.join(ZWSP if bit == '0' else ZWNJ for bit in binary_str) + ZWJ

    css = f'''/*
 * ST3GG Steganography Theme
 * {PLINIAN_DIVIDER}
 * Generated by STEGOSAURUS WRECKS v3.0
 */

/* hex:{hex_encoded} */

:root {{
  --bg-primary: #1a1a2e;
  --bg-secondary: #16213e;
  --text-primary: #e0e0e0;
  --text-secondary: #a0a0b0;
  --accent-purple: #c471ed;
  --accent-blue: #12c2e9;
  --accent-orange: #f5af19;
  --accent-red: #f64f59;
}}

/* {zw_string} */

* {{
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}}

body {{
  font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
  background: var(--bg-primary);
  color: var(--text-primary);
  line-height: 1.6;
}}

.container {{
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
}}

/* Steganography analysis panel */
.steg-panel {{
  background: var(--bg-secondary);
  border: 1px solid rgba(196, 113, 237, 0.2);
  border-radius: 12px;
  padding: 1.5rem;
  margin-bottom: 1.5rem;
}}

.steg-panel__header {{
  font-size: 1.25rem;
  color: var(--accent-purple);
  margin-bottom: 0.75rem;
  border-bottom: 1px solid rgba(196, 113, 237, 0.15);
  padding-bottom: 0.5rem;
}}

/* b64:{encoded} */

.steg-panel__content {{
  font-family: 'Fira Code', 'Consolas', monospace;
  font-size: 0.875rem;
  color: var(--text-secondary);
}}

/* Hidden element - payload carrier */
[data-steg-payload]::after {{
  content: "{PLINIAN_DIVIDER}";
  display: none;
  visibility: hidden;
  position: absolute;
  width: 0;
  height: 0;
  overflow: hidden;
}}

.btn {{
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1.25rem;
  border: none;
  border-radius: 8px;
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 0.2s ease;
}}

.btn--primary {{
  background: linear-gradient(135deg, var(--accent-purple), var(--accent-blue));
  color: white;
}}

.btn--primary:hover {{
  transform: translateY(-1px);
  box-shadow: 0 4px 15px rgba(196, 113, 237, 0.3);
}}

/* Animation keyframes */
@keyframes pulse {{
  0%, 100% {{ opacity: 1; }}
  50% {{ opacity: 0.7; }}
}}

.analyzing {{
  animation: pulse 1.5s ease-in-out infinite;
}}
'''

    path = os.path.join(OUTPUT_DIR, 'example_hidden.css')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(css)
    print(f"    -> {path}")
    return path


# =============================================================================
# 41. INI/Config with comment encoding
# =============================================================================

def generate_ini_hidden():
    """Create an INI config file with the Plinian divider in comments."""
    print("  Generating INI with comment steganography...")
    import base64

    encoded = base64.b64encode(PLINIAN_DIVIDER.encode('utf-8')).decode()
    hex_encoded = PLINIAN_DIVIDER.encode('utf-8').hex()

    # Encode each byte as a "calibration" comment
    secret_bytes = PLINIAN_DIVIDER.encode('utf-8')
    cal_lines = [f"; cal[{i:02d}] = {b:3d}  ; 0x{b:02x}" for i, b in enumerate(secret_bytes)]

    ini = f'''; ST3GG Configuration File
; Generated by STEGOSAURUS WRECKS v3.0
; {PLINIAN_DIVIDER}

[general]
application = ST3GG
version = 3.0
description = Steganography Toolkit
author = STEGOSAURUS WRECKS

[encoding]
default_channels = RGB
default_bits = 1
strategy = sequential
compression = true

; Payload: {encoded}

[detection]
exhaustive_mode = true
auto_detect = true
max_scan_depth = 11
timeout_seconds = 30

[security]
encryption = AES-256-GCM
key_derivation = PBKDF2
iterations = 100000

; hex: {hex_encoded}

[output]
format = PNG
quality = 100
preserve_metadata = true

; Calibration byte table (system data - do not modify)
{chr(10).join(cal_lines)}

[advanced]
ghost_mode = false
matryoshka_layers = 0
dct_robustness = 2
; payload_direct = {PLINIAN_DIVIDER}
'''

    path = os.path.join(OUTPUT_DIR, 'example_hidden.ini')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(ini)
    print(f"    -> {path}")
    return path


# =============================================================================
# 42. Shell script with whitespace encoding
# =============================================================================

def generate_shell_hidden():
    """Create a shell script with the Plinian divider in comments and whitespace."""
    print("  Generating Shell script with hidden data...")
    import base64

    encoded = base64.b64encode(PLINIAN_DIVIDER.encode('utf-8')).decode()
    hex_encoded = PLINIAN_DIVIDER.encode('utf-8').hex()

    # Whitespace-encode in trailing spaces/tabs
    msg_bytes = PLINIAN_DIVIDER.encode('utf-8')
    length_bits = format(len(msg_bytes), '016b')
    data_bits = ''.join(format(b, '08b') for b in msg_bytes)
    all_bits = length_bits + data_bits

    script_lines = [
        '#!/usr/bin/env bash',
        f'# {PLINIAN_DIVIDER}',
        '# Specimen Analysis Script',
        '# Generated by STEGOSAURUS WRECKS v3.0',
        '',
        f'# Verification: {encoded}',
        '',
        'set -euo pipefail',
        '',
        'readonly SPECIMENS=(',
        '    "Stegosaurus:Late Jurassic:9.0:5000:Herbivore"',
        '    "Triceratops:Late Cretaceous:9.0:6000:Herbivore"',
        '    "Tyrannosaurus:Late Cretaceous:12.3:8400:Carnivore"',
        '    "Velociraptor:Late Cretaceous:2.0:15:Carnivore"',
        '    "Brachiosaurus:Late Jurassic:26.0:56000:Herbivore"',
        ')',
        '',
        'print_header() {',
        '    printf "%-20s %-18s %8s %8s\\n" "Name" "Period" "Length" "Mass"',
        '    printf "%-20s %-18s %8s %8s\\n" "----" "------" "------" "----"',
        '}',
        '',
        'analyze_specimens() {',
        '    for entry in "${SPECIMENS[@]}"; do',
        '        IFS=":" read -r name period length mass diet <<< "$entry"',
        '        printf "%-20s %-18s %8s %8s\\n" "$name" "$period" "$length" "$mass"',
        '    done',
        '}',
        '',
        f'# hex:{hex_encoded}',
        '',
        'main() {',
        '    echo "Specimen Analysis Report"',
        '    echo "========================"',
        '    print_header',
        '    analyze_specimens',
        '    echo ""',
        '    echo "Analysis complete."',
        '}',
        '',
        'main "$@"',
    ]

    bit_index = 0
    result_lines = []
    for line in script_lines:
        trailing = ''
        for _ in range(8):
            if bit_index < len(all_bits):
                trailing += ' ' if all_bits[bit_index] == '0' else '\t'
                bit_index += 1
        result_lines.append(line + trailing)

    path = os.path.join(OUTPUT_DIR, 'example_hidden.sh')
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(result_lines))
    print(f"    -> {path} ({bit_index} bits in whitespace)")
    return path


# =============================================================================
# 43. SQL with comment steganography
# =============================================================================

def generate_sql_hidden():
    """Create a SQL file with the Plinian divider hidden in comments."""
    print("  Generating SQL with comment steganography...")
    import base64

    encoded = base64.b64encode(PLINIAN_DIVIDER.encode('utf-8')).decode()
    hex_encoded = PLINIAN_DIVIDER.encode('utf-8').hex()
    secret_bytes = PLINIAN_DIVIDER.encode('utf-8')

    # Encode each byte as a seemingly-innocent SQL comment
    byte_comments = [f"-- chk[{i:02d}]: {b:3d}" for i, b in enumerate(secret_bytes)]

    sql = f'''-- =============================================================================
-- Paleontology Specimen Database Schema
-- Generated by STEGOSAURUS WRECKS v3.0
-- {PLINIAN_DIVIDER}
-- =============================================================================

-- hex: {hex_encoded}

CREATE TABLE IF NOT EXISTS geological_periods (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    start_mya REAL NOT NULL,
    end_mya REAL NOT NULL
);

INSERT INTO geological_periods (id, name, start_mya, end_mya) VALUES
    (1, 'Late Triassic', 237.0, 201.3),
    (2, 'Early Jurassic', 201.3, 174.1),
    (3, 'Late Jurassic', 163.5, 145.0),
    (4, 'Early Cretaceous', 145.0, 100.5),
    (5, 'Late Cretaceous', 100.5, 66.0);

-- b64: {encoded}

CREATE TABLE IF NOT EXISTS specimens (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    species TEXT,
    period_id INTEGER REFERENCES geological_periods(id),
    length_m REAL,
    mass_kg REAL,
    diet TEXT CHECK(diet IN ('Herbivore', 'Carnivore', 'Omnivore', 'Piscivore')),
    brain_volume_cc REAL,
    discovery_year INTEGER,
    location TEXT
);

INSERT INTO specimens (id, name, species, period_id, length_m, mass_kg, diet, brain_volume_cc, discovery_year, location) VALUES
    (1, 'Stegosaurus', 'S. stenops', 3, 9.0, 5000, 'Herbivore', 2.8, 1877, 'Morrison Formation, CO'),
    (2, 'Triceratops', 'T. horridus', 5, 9.0, 6000, 'Herbivore', 70.0, 1887, 'Hell Creek, MT'),
    (3, 'Tyrannosaurus', 'T. rex', 5, 12.3, 8400, 'Carnivore', 343.0, 1905, 'Hell Creek, MT'),
    (4, 'Velociraptor', 'V. mongoliensis', 5, 2.0, 15, 'Carnivore', 15.0, 1924, 'Djadokhta, Mongolia'),
    (5, 'Brachiosaurus', 'B. altithorax', 3, 26.0, 56000, 'Herbivore', 26.0, 1903, 'Morrison Formation, CO');

-- Checksum verification data
{chr(10).join(byte_comments)}

-- Analysis view
CREATE VIEW IF NOT EXISTS specimen_analysis AS
SELECT
    s.name,
    s.species,
    gp.name AS period,
    s.length_m,
    s.mass_kg,
    s.diet,
    CASE
        WHEN s.brain_volume_cc / (0.12 * POWER(s.mass_kg, 0.67)) > 1.0 THEN 'High EQ'
        WHEN s.brain_volume_cc / (0.12 * POWER(s.mass_kg, 0.67)) > 0.5 THEN 'Medium EQ'
        ELSE 'Low EQ'
    END AS intelligence_class
FROM specimens s
JOIN geological_periods gp ON s.period_id = gp.id;

-- End of schema
-- Payload: {PLINIAN_DIVIDER}
'''

    path = os.path.join(OUTPUT_DIR, 'example_hidden.sql')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(sql)
    print(f"    -> {path}")
    return path


# =============================================================================
# 44. LaTeX with comment encoding
# =============================================================================

def generate_latex_hidden():
    """Create a LaTeX file with the Plinian divider hidden in comments."""
    print("  Generating LaTeX with comment steganography...")
    import base64

    encoded = base64.b64encode(PLINIAN_DIVIDER.encode('utf-8')).decode()
    hex_encoded = PLINIAN_DIVIDER.encode('utf-8').hex()

    latex = f'''%% =============================================================================
%% Paleontology Specimen Report
%% Generated by STEGOSAURUS WRECKS v3.0
%% {PLINIAN_DIVIDER}
%% =============================================================================

\\documentclass[12pt]{{article}}
\\usepackage[utf8]{{inputenc}}
\\usepackage{{booktabs}}
\\usepackage{{graphicx}}
\\usepackage{{amsmath}}

%% hex: {hex_encoded}

\\title{{Comparative Analysis of Ornithischian Dinosaurs}}
\\author{{STEGOSAURUS WRECKS Research Division}}
\\date{{Late Jurassic -- Late Cretaceous}}

\\begin{{document}}

\\maketitle

%% b64: {encoded}

\\begin{{abstract}}
This report presents a comparative analysis of ornithischian dinosaur specimens,
focusing on body mass, encephalization quotient, and defensive adaptations.
The Stegosaurus remains one of the most distinctive members of this clade.
\\end{{abstract}}

\\section{{Introduction}}

The Ornithischia (``bird-hipped'' dinosaurs) represent one of the two major
clades of dinosaurs, characterized by a pubis bone that points backward.
This clade includes many well-known species including Stegosaurus,
Triceratops, and Ankylosaurus.

%% Payload: {PLINIAN_DIVIDER}

\\section{{Specimen Data}}

\\begin{{table}}[h]
\\centering
\\caption{{Ornithischian Specimen Measurements}}
\\begin{{tabular}}{{lllrr}}
\\toprule
\\textbf{{Species}} & \\textbf{{Period}} & \\textbf{{Diet}} & \\textbf{{Length (m)}} & \\textbf{{Mass (kg)}} \\\\
\\midrule
Stegosaurus    & Late Jurassic    & Herbivore &  9.0 &  5000 \\\\
Triceratops    & Late Cretaceous  & Herbivore &  9.0 &  6000 \\\\
Ankylosaurus   & Late Cretaceous  & Herbivore &  6.5 &  6000 \\\\
Parasaurolophus & Late Cretaceous & Herbivore &  9.5 &  2500 \\\\
Pachycephalosaurus & Late Cretaceous & Herbivore & 4.5 & 450 \\\\
\\bottomrule
\\end{{tabular}}
\\end{{table}}

\\section{{Encephalization Quotient}}

The encephalization quotient (EQ) provides a measure of relative brain size:
\\begin{{equation}}
EQ = \\frac{{E_{{actual}}}}{{E_{{expected}}}} = \\frac{{E_{{actual}}}}{{0.12 \\cdot M^{{0.67}}}}
\\end{{equation}}
where $E_{{actual}}$ is the actual brain mass and $M$ is body mass in kilograms.

\\section{{Conclusion}}

Ornithischian dinosaurs show remarkable diversity in defensive adaptations,
from the plates and spikes of Stegosaurus to the armored shell of Ankylosaurus
and the horned frill of Triceratops.

\\end{{document}}
'''

    path = os.path.join(OUTPUT_DIR, 'example_hidden.tex')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(latex)
    print(f"    -> {path}")
    return path


# =============================================================================
# 45. TOML with comment encoding
# =============================================================================

def generate_toml_hidden():
    """Create a TOML config file with the Plinian divider in comments."""
    print("  Generating TOML with comment steganography...")
    import base64

    encoded = base64.b64encode(PLINIAN_DIVIDER.encode('utf-8')).decode()
    hex_encoded = PLINIAN_DIVIDER.encode('utf-8').hex()

    toml = f'''# ST3GG Project Configuration
# {PLINIAN_DIVIDER}
# Generated by STEGOSAURUS WRECKS v3.0

[project]
name = "ST3GG"
version = "3.0.0"
description = "Advanced Steganography Toolkit"
authors = ["STEGOSAURUS WRECKS"]
license = "MIT"

# hex: {hex_encoded}

[encoding]
default_channels = "RGB"
default_bits_per_channel = 1
strategy = "sequential"
compression = true

[encoding.presets]
minimal = {{ channels = "R", bits = 1 }}
standard = {{ channels = "RGB", bits = 1 }}
high_capacity = {{ channels = "RGBA", bits = 2 }}
maximum = {{ channels = "RGBA", bits = 8 }}

# b64: {encoded}

[detection]
exhaustive_mode = true
auto_detect = true
max_depth = 11
timeout = 30

[security]
encryption = "AES-256-GCM"
key_derivation = "PBKDF2"
iterations = 100_000
ghost_mode = false

[output]
format = "PNG"
quality = 100
preserve_metadata = true

# Payload: {PLINIAN_DIVIDER}

[[specimens]]
name = "Stegosaurus"
period = "Late Jurassic"
length_m = 9.0
mass_kg = 5_000

[[specimens]]
name = "Triceratops"
period = "Late Cretaceous"
length_m = 9.0
mass_kg = 6_000

[[specimens]]
name = "Tyrannosaurus"
period = "Late Cretaceous"
length_m = 12.3
mass_kg = 8_400
'''

    path = os.path.join(OUTPUT_DIR, 'example_hidden.toml')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(toml)
    print(f"    -> {path}")
    return path


# =============================================================================
# 46. Homoglyph steganography (Cyrillic/Latin substitution)
# =============================================================================

def generate_homoglyph():
    """Create a text file with Plinian divider encoded via Cyrillic/Latin homoglyphs.

    Each confusable character substituted = 1, left as Latin = 0.
    Only characters that have Cyrillic lookalikes are used as bit carriers.
    """
    print("  Generating homoglyph (Cyrillic/Latin) steganography...")

    # Latin chars that have Cyrillic visual equivalents
    HOMOGLYPH_MAP = {
        'a': '\u0430',  # Cyrillic а
        'c': '\u0441',  # Cyrillic с
        'e': '\u0435',  # Cyrillic е
        'o': '\u043e',  # Cyrillic о
        'p': '\u0440',  # Cyrillic р
        's': '\u0455',  # Cyrillic ѕ
        'x': '\u0445',  # Cyrillic х
        'y': '\u0443',  # Cyrillic у (close enough)
        'A': '\u0410',  # Cyrillic А
        'B': '\u0412',  # Cyrillic В
        'C': '\u0421',  # Cyrillic С
        'E': '\u0415',  # Cyrillic Е
        'H': '\u041d',  # Cyrillic Н
        'K': '\u041a',  # Cyrillic К
        'M': '\u041c',  # Cyrillic М
        'O': '\u041e',  # Cyrillic О
        'P': '\u0420',  # Cyrillic Р
        'T': '\u0422',  # Cyrillic Т
        'X': '\u0425',  # Cyrillic Х
    }

    cover = (
        "The Stegosaurus was a spectacular dinosaur that roamed the Earth "
        "approximately one hundred and fifty million years ago. Despite its "
        "enormous size, this peaceful herbivore possessed a remarkably small "
        "brain, roughly the size of a walnut. The distinctive plates along "
        "its back were once thought to serve as armor, but modern research "
        "suggests they were primarily used for thermoregulation and display. "
        "Each plate was covered in a network of blood vessels that could "
        "absorb or release heat depending on the animal's needs. The famous "
        "thagomizer on its tail, consisting of four sharp spikes, was almost "
        "certainly used as a defensive weapon against predators like Allosaurus. "
        "Fossil evidence shows puncture marks on Allosaurus bones that match "
        "the spacing of Stegosaurus tail spikes perfectly. This remarkable "
        "creature continues to capture our imagination and represents one of "
        "the most iconic dinosaurs ever discovered. Paleontologists have "
        "unearthed specimens across western North America and parts of "
        "Portugal, expanding our knowledge of its range and behavior."
    )

    # Encode Plinian divider as bits
    msg_bytes = PLINIAN_DIVIDER.encode('utf-8')
    bits = []
    for b in msg_bytes:
        for j in range(7, -1, -1):
            bits.append((b >> j) & 1)

    # Find carrier positions (characters that have homoglyphs)
    carriers = []
    for i, ch in enumerate(cover):
        if ch in HOMOGLYPH_MAP:
            carriers.append(i)

    # Encode: 16-bit length prefix + message bits
    length_bits = [int(b) for b in format(len(msg_bytes), '016b')]
    all_bits = length_bits + bits

    result = list(cover)
    bit_idx = 0
    for pos in carriers:
        if bit_idx >= len(all_bits):
            break
        if all_bits[bit_idx] == 1:
            result[pos] = HOMOGLYPH_MAP[cover[pos]]
        bit_idx += 1

    path = os.path.join(OUTPUT_DIR, 'example_homoglyph.txt')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(''.join(result))
    print(f"    -> {path} ({bit_idx} bits in {len(carriers)} carrier chars)")
    return path


# =============================================================================
# 47. Variation selector steganography
# =============================================================================

def generate_variation_selector():
    """Create a text file with Plinian divider encoded via Unicode variation selectors.

    Variation selectors (U+FE00-U+FE0F) are invisible modifiers that follow
    base characters. Their presence (1) or absence (0) encodes bits.
    """
    print("  Generating variation selector steganography...")

    # VS1-VS16 (U+FE00 to U+FE0F)
    VS1 = '\uFE01'  # We use VS1 as the marker

    cover = (
        "Dinosaur Classification Guide\n"
        "=============================\n\n"
        "Order Ornithischia (bird-hipped dinosaurs):\n"
        "  - Stegosaurus: Late Jurassic, 9m long, herbivore\n"
        "  - Triceratops: Late Cretaceous, 9m long, herbivore\n"
        "  - Ankylosaurus: Late Cretaceous, 6.5m long, herbivore\n"
        "  - Pachycephalosaurus: Late Cretaceous, 4.5m long, herbivore\n"
        "  - Parasaurolophus: Late Cretaceous, 9.5m long, herbivore\n"
        "  - Iguanodon: Early Cretaceous, 10m long, herbivore\n\n"
        "Order Saurischia (lizard-hipped dinosaurs):\n"
        "  - Tyrannosaurus: Late Cretaceous, 12m long, carnivore\n"
        "  - Velociraptor: Late Cretaceous, 2m long, carnivore\n"
        "  - Brachiosaurus: Late Jurassic, 26m long, herbivore\n"
        "  - Diplodocus: Late Jurassic, 26m long, herbivore\n"
        "  - Allosaurus: Late Jurassic, 8.5m long, carnivore\n"
        "  - Spinosaurus: Late Cretaceous, 15m long, piscivore\n"
        "  - Compsognathus: Late Jurassic, 1m long, carnivore\n"
        "  - Gallimimus: Late Cretaceous, 6m long, omnivore\n\n"
        "The distinction between these orders is based on the structure\n"
        "of the pelvis. Ornithischians have a pubis bone that points\n"
        "backward, similar to modern birds, while saurischians have a\n"
        "forward-pointing pubis, more like modern lizards.\n"
    )

    # Encode
    msg_bytes = PLINIAN_DIVIDER.encode('utf-8')
    length_bits = [int(b) for b in format(len(msg_bytes), '016b')]
    data_bits = []
    for b in msg_bytes:
        for j in range(7, -1, -1):
            data_bits.append((b >> j) & 1)
    all_bits = length_bits + data_bits

    # Insert VS after alphanumeric characters to encode bits
    result = []
    bit_idx = 0
    for ch in cover:
        result.append(ch)
        if bit_idx < len(all_bits) and ch.isalpha():
            if all_bits[bit_idx] == 1:
                result.append(VS1)
            bit_idx += 1

    path = os.path.join(OUTPUT_DIR, 'example_variation_selector.txt')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(''.join(result))
    print(f"    -> {path} ({bit_idx} bits encoded)")
    return path


# =============================================================================
# 48. Combining diacritic steganography
# =============================================================================

def generate_combining_diacritics():
    """Create a text file with Plinian divider encoded via invisible combining marks.

    Uses combining characters that render invisibly on most systems:
    U+034F COMBINING GRAPHEME JOINER (invisible)
    Presence after a letter = 1, absence = 0.
    """
    print("  Generating combining diacritic steganography...")

    CGJ = '\u034F'  # Combining Grapheme Joiner (invisible)

    cover = (
        "Stegosaurus Defense Mechanisms\n\n"
        "The Stegosaurus possessed two primary defensive features that made it\n"
        "a formidable opponent for predators of the Late Jurassic period.\n\n"
        "First, the double row of bony plates along its back served multiple\n"
        "purposes. While not strong enough to function as true armor, these\n"
        "plates made the animal appear much larger and more intimidating when\n"
        "viewed from the side. The plates were richly supplied with blood\n"
        "vessels, suggesting they also played a role in thermoregulation,\n"
        "allowing the dinosaur to warm up quickly in the morning sun.\n\n"
        "Second, and more importantly for defense, was the thagomizer: a\n"
        "cluster of four large spikes at the end of its muscular tail. Each\n"
        "spike could measure up to ninety centimeters in length. The tail\n"
        "itself was remarkably flexible and powerful, capable of delivering\n"
        "devastating blows to attackers. Evidence from Allosaurus fossils\n"
        "shows wounds consistent with Stegosaurus tail spike impacts,\n"
        "confirming that this weapon was used actively in combat.\n\n"
        "Together, these adaptations made Stegosaurus one of the best\n"
        "defended herbivores of its era, despite its relatively small brain\n"
        "and slow movement speed compared to theropod predators.\n"
    )

    msg_bytes = PLINIAN_DIVIDER.encode('utf-8')
    length_bits = [int(b) for b in format(len(msg_bytes), '016b')]
    data_bits = []
    for b in msg_bytes:
        for j in range(7, -1, -1):
            data_bits.append((b >> j) & 1)
    all_bits = length_bits + data_bits

    result = []
    bit_idx = 0
    for ch in cover:
        result.append(ch)
        if bit_idx < len(all_bits) and ch.isalpha():
            if all_bits[bit_idx] == 1:
                result.append(CGJ)
            bit_idx += 1

    path = os.path.join(OUTPUT_DIR, 'example_combining_diacritics.txt')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(''.join(result))
    print(f"    -> {path} ({bit_idx} bits encoded)")
    return path


# =============================================================================
# 49. Confusable whitespace steganography
# =============================================================================

def generate_confusable_whitespace():
    """Create a text file with Plinian divider encoded via Unicode whitespace variants.

    Uses multiple Unicode space characters that render identically:
    Regular space (U+0020) = 00, En space (U+2002) = 01,
    Em space (U+2003) = 10, Thin space (U+2009) = 11.
    Two bits per space character.
    """
    print("  Generating confusable whitespace steganography...")

    SPACE_MAP = {
        0b00: ' ',       # Regular space (U+0020)
        0b01: '\u2002',  # En space
        0b10: '\u2003',  # Em space
        0b11: '\u2009',  # Thin space
    }

    cover_words = (
        "The study of dinosaur fossils has revealed incredible details about "
        "prehistoric life on Earth. Each discovery adds new pieces to the "
        "puzzle of ancient ecosystems and evolutionary relationships. Modern "
        "technology including CT scanning and molecular analysis allows "
        "paleontologists to extract information that was previously impossible "
        "to obtain from fossilized remains. The field continues to evolve "
        "with new species being described every year and old assumptions "
        "being challenged by fresh evidence. From the massive sauropods to "
        "the tiny compsognathids the diversity of dinosaur life was truly "
        "staggering. Their reign lasted over one hundred and sixty million "
        "years making them one of the most successful groups of land animals "
        "in the history of our planet. Understanding their biology behavior "
        "and eventual extinction helps us appreciate the fragility and "
        "resilience of life on Earth."
    ).split(' ')

    msg_bytes = PLINIAN_DIVIDER.encode('utf-8')
    # Build 2-bit pairs
    bits = []
    for b in msg_bytes:
        for j in range(7, -1, -1):
            bits.append((b >> j) & 1)

    # 16-bit length prefix
    length_bits = [int(b) for b in format(len(msg_bytes), '016b')]
    all_bits = length_bits + bits

    # Pair up bits into 2-bit values
    pairs = []
    for i in range(0, len(all_bits), 2):
        if i + 1 < len(all_bits):
            pairs.append((all_bits[i] << 1) | all_bits[i + 1])
        else:
            pairs.append(all_bits[i] << 1)

    # Replace spaces between words with encoded whitespace
    result = []
    pair_idx = 0
    for i, word in enumerate(cover_words):
        result.append(word)
        if i < len(cover_words) - 1:
            if pair_idx < len(pairs):
                result.append(SPACE_MAP[pairs[pair_idx]])
                pair_idx += 1
            else:
                result.append(' ')

    path = os.path.join(OUTPUT_DIR, 'example_confusable_whitespace.txt')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(''.join(result))
    print(f"    -> {path} ({pair_idx * 2} bits in {pair_idx} space chars)")
    return path


# =============================================================================
# 50. Emoji substitution steganography
# =============================================================================

def generate_emoji_substitution():
    """Create a text file with Plinian divider encoded via emoji pairs.

    Uses pairs of similar-looking emoji: first of pair = 0, second = 1.
    Each emoji position encodes one bit.
    """
    print("  Generating emoji substitution steganography...")

    # Emoji pairs (visually similar, encode 0 or 1)
    EMOJI_PAIRS = [
        ('🌑', '🌚'),  # Dark moons
        ('⭐', '🌟'),  # Stars
        ('🔴', '🟥'),  # Red circle/square
        ('🔵', '🟦'),  # Blue circle/square
        ('🟢', '🟩'),  # Green circle/square
        ('⚫', '🖤'),  # Black circle/heart
        ('⚪', '🤍'),  # White circle/heart
        ('🔶', '🟧'),  # Orange diamond/square
    ]

    msg_bytes = PLINIAN_DIVIDER.encode('utf-8')
    length_bits = [int(b) for b in format(len(msg_bytes), '016b')]
    data_bits = []
    for b in msg_bytes:
        for j in range(7, -1, -1):
            data_bits.append((b >> j) & 1)
    all_bits = length_bits + data_bits

    # Build emoji stream
    emoji_line = []
    for i, bit in enumerate(all_bits):
        pair = EMOJI_PAIRS[i % len(EMOJI_PAIRS)]
        emoji_line.append(pair[bit])

    # Create a "fun" cover document
    content = (
        "Dinosaur Mood Tracker 🦕\n"
        "========================\n\n"
        "Today's paleontology status indicators:\n\n"
        + ''.join(emoji_line) + "\n\n"
        "Legend:\n"
        "🌑🌚 = Moon phases (new moon / moon face)\n"
        "⭐🌟 = Star brightness (solid / sparkling)\n"
        "🔴🟥 = Alert levels (circle / square)\n"
        "🔵🟦 = Status indicators (circle / square)\n"
        "🟢🟩 = Progress markers (circle / square)\n"
        "⚫🖤 = Fossil darkness (circle / heart)\n"
        "⚪🤍 = Bone whiteness (circle / heart)\n"
        "🔶🟧 = Amber indicators (diamond / square)\n\n"
        "Each emoji represents a data point in our specimen tracking system.\n"
        "The pattern above encodes today's field survey results.\n"
    )

    path = os.path.join(OUTPUT_DIR, 'example_emoji_substitution.txt')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"    -> {path} ({len(all_bits)} bits in {len(all_bits)} emoji)")
    return path


# =============================================================================
# 51. DNS tunneling steganography (PCAP)
# =============================================================================

def generate_dns_tunnel_pcap():
    """Create a PCAP with Plinian divider hidden in DNS query names."""
    print("  Generating DNS tunneling PCAP...")
    import base64
    import time

    secret = PLINIAN_DIVIDER.encode('utf-8')
    # Base32-encode for DNS-safe label characters
    encoded = base64.b32encode(secret).decode().lower().rstrip('=')

    # Split into DNS-safe labels (max 63 chars each)
    labels = [encoded[i:i+60] for i in range(0, len(encoded), 60)]

    pcap = struct.pack('<IHHiIII',
        0xa1b2c3d4, 2, 4, 0, 0, 65535, 1)  # PCAP header

    ts = int(time.time())

    for i, label in enumerate(labels):
        # Build DNS query
        domain = f"{label}.steg.example.com"
        dns_query = b'\x00\x01'  # Transaction ID
        dns_query += b'\x01\x00'  # Standard query
        dns_query += b'\x00\x01\x00\x00\x00\x00\x00\x00'  # 1 question

        # Encode domain name as DNS wire format
        for part in domain.split('.'):
            dns_query += bytes([len(part)]) + part.encode('ascii')
        dns_query += b'\x00'  # Root label
        dns_query += b'\x00\x01'  # Type A
        dns_query += b'\x00\x01'  # Class IN

        # UDP header
        udp_len = 8 + len(dns_query)
        udp = struct.pack('>HHHH', 12345 + i, 53, udp_len, 0) + dns_query

        # IP header
        ip_len = 20 + len(udp)
        ip_hdr = struct.pack('>BBHHHBBH4s4s',
            0x45, 0, ip_len, 0x1234 + i, 0x4000,
            64, 17, 0,
            bytes([192, 168, 1, 100]),
            bytes([8, 8, 8, 8]))

        # Ethernet
        eth = b'\x00' * 6 + b'\x00' * 6 + b'\x08\x00'
        frame = eth + ip_hdr + udp

        pkt_hdr = struct.pack('<IIII', ts + i, 0, len(frame), len(frame))
        pcap += pkt_hdr + frame

    path = os.path.join(OUTPUT_DIR, 'example_dns_tunnel.pcap')
    with open(path, 'wb') as f:
        f.write(pcap)
    print(f"    -> {path} ({len(labels)} DNS queries)")
    return path


# =============================================================================
# 52. ICMP steganography (PCAP)
# =============================================================================

def generate_icmp_steg_pcap():
    """Create a PCAP with Plinian divider hidden in ICMP echo request payloads."""
    print("  Generating ICMP steganography PCAP...")
    import time

    secret = PLINIAN_DIVIDER.encode('utf-8')
    pcap = struct.pack('<IHHiIII',
        0xa1b2c3d4, 2, 4, 0, 0, 65535, 1)

    ts = int(time.time())
    chunk_size = 32

    for i in range(0, len(secret), chunk_size):
        chunk = secret[i:i + chunk_size]
        # Pad with random-looking filler
        payload = chunk + bytes(range(len(chunk), 56))

        # ICMP echo request
        icmp_type = 8  # Echo request
        icmp_code = 0
        icmp_id = 0x1234
        icmp_seq = i // chunk_size
        # Checksum placeholder (0)
        icmp = struct.pack('>BBHHH', icmp_type, icmp_code, 0, icmp_id, icmp_seq)
        icmp += payload

        # Calculate ICMP checksum
        cksum = 0
        for j in range(0, len(icmp), 2):
            if j + 1 < len(icmp):
                cksum += (icmp[j] << 8) + icmp[j + 1]
            else:
                cksum += icmp[j] << 8
        while cksum >> 16:
            cksum = (cksum & 0xFFFF) + (cksum >> 16)
        cksum = ~cksum & 0xFFFF
        icmp = struct.pack('>BBHHH', icmp_type, icmp_code, cksum, icmp_id, icmp_seq) + payload

        # IP header (protocol 1 = ICMP)
        ip_len = 20 + len(icmp)
        ip_hdr = struct.pack('>BBHHHBBH4s4s',
            0x45, 0, ip_len, 0x5678 + i, 0x4000,
            64, 1, 0,  # TTL=64, Protocol=1 (ICMP)
            bytes([192, 168, 1, 100]),
            bytes([8, 8, 8, 8]))

        eth = b'\x00' * 6 + b'\x00' * 6 + b'\x08\x00'
        frame = eth + ip_hdr + icmp
        pkt_hdr = struct.pack('<IIII', ts + i, 0, len(frame), len(frame))
        pcap += pkt_hdr + frame

    path = os.path.join(OUTPUT_DIR, 'example_icmp_steg.pcap')
    with open(path, 'wb') as f:
        f.write(pcap)
    print(f"    -> {path}")
    return path


# =============================================================================
# 53. TCP covert channel (PCAP) — data in ISN and TCP timestamps
# =============================================================================

def generate_tcp_covert_pcap():
    """Create a PCAP with Plinian divider hidden in TCP header fields.

    Encodes 4 bytes per SYN packet in the Initial Sequence Number (ISN),
    and additional bytes in the TCP timestamp option.
    """
    print("  Generating TCP covert channel PCAP...")
    import time

    secret = PLINIAN_DIVIDER.encode('utf-8')
    pcap = struct.pack('<IHHiIII',
        0xa1b2c3d4, 2, 4, 0, 0, 65535, 1)

    ts = int(time.time())

    # Encode 4 bytes in ISN + 4 bytes in TCP timestamp per packet
    chunk_size = 8
    for i in range(0, len(secret), chunk_size):
        chunk = secret[i:i + chunk_size]

        # ISN carries first 4 bytes
        isn_bytes = chunk[:4].ljust(4, b'\x00')
        isn = struct.unpack('>I', isn_bytes)[0]

        # TCP timestamp carries next 4 bytes
        ts_bytes = chunk[4:8].ljust(4, b'\x00')
        ts_val = struct.unpack('>I', ts_bytes)[0]

        # TCP header (SYN packet with timestamp option)
        src_port = 49152 + (i // chunk_size)
        dst_port = 443
        tcp_flags = 0x02  # SYN
        # TCP header: 20 bytes base + 12 bytes options (timestamps)
        # Option: kind=8, length=10, TSval, TSecr=0, + 2 bytes NOP padding
        tcp_opts = struct.pack('>BBII', 8, 10, ts_val, 0) + b'\x01\x01'  # NOP NOP
        tcp_hdr_len = (20 + len(tcp_opts)) // 4
        tcp = struct.pack('>HHIIBBHHH',
            src_port, dst_port, isn, 0,
            (tcp_hdr_len << 4), tcp_flags,
            65535, 0, 0)
        tcp += tcp_opts

        # IP header
        ip_len = 20 + len(tcp)
        ip_hdr = struct.pack('>BBHHHBBH4s4s',
            0x45, 0, ip_len, 0xABCD + i, 0x4000,
            64, 6, 0,  # Protocol=6 (TCP)
            bytes([10, 0, 0, 1]),
            bytes([93, 184, 216, 34]))

        eth = b'\x00' * 6 + b'\x00' * 6 + b'\x08\x00'
        frame = eth + ip_hdr + tcp
        pkt_hdr = struct.pack('<IIII', ts + i, 0, len(frame), len(frame))
        pcap += pkt_hdr + frame

    path = os.path.join(OUTPUT_DIR, 'example_tcp_covert.pcap')
    with open(path, 'wb') as f:
        f.write(pcap)
    print(f"    -> {path}")
    return path


# =============================================================================
# 54. HTTP header smuggling (PCAP)
# =============================================================================

def generate_http_header_pcap():
    """Create a PCAP with Plinian divider hidden in HTTP custom headers."""
    print("  Generating HTTP header smuggling PCAP...")
    import base64
    import time

    secret = PLINIAN_DIVIDER.encode('utf-8')
    encoded_b64 = base64.b64encode(secret).decode()
    hex_encoded = secret.hex()

    # Build an HTTP request with hidden headers
    http_req = (
        f"GET /index.html HTTP/1.1\r\n"
        f"Host: www.example.com\r\n"
        f"User-Agent: Mozilla/5.0 (compatible; StegBot/3.0)\r\n"
        f"Accept: text/html\r\n"
        f"X-Request-ID: {hex_encoded}\r\n"
        f"X-Correlation-Token: {encoded_b64}\r\n"
        f"X-Debug-Info: {PLINIAN_DIVIDER}\r\n"
        f"Cookie: session={encoded_b64}; theme=dark\r\n"
        f"Connection: keep-alive\r\n"
        f"\r\n"
    ).encode('utf-8')

    pcap = struct.pack('<IHHiIII',
        0xa1b2c3d4, 2, 4, 0, 0, 65535, 1)

    ts = int(time.time())

    # TCP segment with HTTP payload
    tcp = struct.pack('>HHIIBBHHH',
        49200, 80,
        1000, 0,
        (5 << 4), 0x18,  # ACK+PSH, data offset=5 (20 bytes)
        65535, 0, 0)
    tcp += http_req

    ip_len = 20 + len(tcp)
    ip_hdr = struct.pack('>BBHHHBBH4s4s',
        0x45, 0, ip_len, 0x1111, 0x4000,
        64, 6, 0,
        bytes([192, 168, 1, 100]),
        bytes([93, 184, 216, 34]))

    eth = b'\x00' * 6 + b'\x00' * 6 + b'\x08\x00'
    frame = eth + ip_hdr + tcp
    pkt_hdr = struct.pack('<IIII', ts, 0, len(frame), len(frame))
    pcap += pkt_hdr + frame

    path = os.path.join(OUTPUT_DIR, 'example_http_headers.pcap')
    with open(path, 'wb') as f:
        f.write(pcap)
    print(f"    -> {path}")
    return path


# =============================================================================
# 55. PNG+ZIP polyglot file
# =============================================================================

def generate_png_zip_polyglot():
    """Create a file that is simultaneously a valid PNG and a valid ZIP.

    PNG readers ignore data after IEND. ZIP readers scan from end of file
    for the End of Central Directory record. So we append a ZIP to a PNG.
    """
    print("  Generating PNG+ZIP polyglot...")
    import zipfile
    import io

    # Create a small PNG
    width, height = 80, 80
    img = Image.new('RGB', (width, height))
    pixels = img.load()
    for y in range(height):
        for x in range(width):
            r = int(100 + 120 * (x / width))
            g = int(50 + 150 * (y / height))
            b = int(180 + 60 * ((x + y) / (width + height)))
            pixels[x, y] = (r, g, b)

    png_buf = io.BytesIO()
    img.save(png_buf, 'PNG')
    png_data = png_buf.getvalue()

    # Create a ZIP in memory
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('secret.txt', PLINIAN_DIVIDER)
        zf.writestr('README.txt', 'This file is both a valid PNG image and a valid ZIP archive.\n'
                     'Open it as an image to see a gradient, or unzip it to find the secret.\n')
        zf.comment = b'ST3GG PNG+ZIP polyglot'

    zip_data = zip_buf.getvalue()

    # Polyglot: PNG data + ZIP data (PNG ignores after IEND, ZIP reads from end)
    polyglot = png_data + zip_data

    path = os.path.join(OUTPUT_DIR, 'example_polyglot.png.zip')
    with open(path, 'wb') as f:
        f.write(polyglot)
    print(f"    -> {path} (PNG: {len(png_data)} + ZIP: {len(zip_data)} bytes)")
    return path


# =============================================================================
# 56. PNG filter type encoding
# =============================================================================

def generate_png_filter_encoding():
    """Create a PNG with Plinian divider encoded in scanline filter type bytes.

    PNG allows 5 filter types (0-4) per scanline. We use: None(0)=0, Sub(1)=1.
    Each scanline's filter byte encodes one bit.
    """
    print("  Generating PNG filter type encoding...")

    msg_bytes = PLINIAN_DIVIDER.encode('utf-8')
    length_bits = [int(b) for b in format(len(msg_bytes), '016b')]
    data_bits = []
    for b in msg_bytes:
        for j in range(7, -1, -1):
            data_bits.append((b >> j) & 1)
    all_bits = length_bits + data_bits

    # Need at least len(all_bits) scanlines
    width = 100
    height = max(len(all_bits) + 10, 600)

    # Build raw RGBA pixel data with filter bytes
    raw_data = bytearray()
    for y in range(height):
        # Filter type byte: 0 (None) = bit 0, 1 (Sub) = bit 1
        if y < len(all_bits):
            filter_byte = all_bits[y]  # 0 or 1
        else:
            filter_byte = 0  # No encoding for remaining lines

        raw_data.append(filter_byte)

        # Pixel data (RGB, 3 bytes per pixel)
        for x in range(width):
            r = int(80 + 120 * (x / width))
            g = int(60 + 140 * (y / height))
            b = int(100 + 100 * ((x + y) / (width + height)))

            if filter_byte == 0:
                # No filter — raw values
                raw_data.extend([r, g, b])
            elif filter_byte == 1:
                # Sub filter: store difference from left pixel
                if x == 0:
                    raw_data.extend([r, g, b])
                else:
                    prev_r = int(80 + 120 * ((x - 1) / width))
                    prev_g = int(60 + 140 * (y / height))
                    prev_b = int(100 + 100 * (((x - 1) + y) / (width + height)))
                    raw_data.extend([(r - prev_r) & 0xFF,
                                     (g - prev_g) & 0xFF,
                                     (b - prev_b) & 0xFF])

    # Build PNG file manually
    import zlib as _zlib

    def png_chunk(chunk_type, data):
        chunk = chunk_type + data
        crc = struct.pack('>I', _zlib.crc32(chunk) & 0xFFFFFFFF)
        return struct.pack('>I', len(data)) + chunk + crc

    png = b'\x89PNG\r\n\x1a\n'
    # IHDR
    ihdr = struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)  # 8-bit RGB
    png += png_chunk(b'IHDR', ihdr)
    # IDAT
    compressed = _zlib.compress(bytes(raw_data))
    png += png_chunk(b'IDAT', compressed)
    # IEND
    png += png_chunk(b'IEND', b'')

    path = os.path.join(OUTPUT_DIR, 'example_filter_encoding.png')
    with open(path, 'wb') as f:
        f.write(png)
    print(f"    -> {path} ({len(all_bits)} bits in {height} scanline filters)")
    return path


# =============================================================================
# 57. Alpha channel LSB steganography
# =============================================================================

def generate_alpha_lsb():
    """Create a PNG with Plinian divider hidden exclusively in alpha channel LSBs.

    Unlike standard RGB LSB, this hides data only in the transparency channel,
    which many analyzers overlook when focusing on color channels.
    """
    print("  Generating alpha channel LSB steganography...")

    width, height = 200, 200
    img = Image.new('RGBA', (width, height))
    pixels = img.load()

    # Gradient with varying alpha (but all alpha > 250, so visually opaque)
    for y in range(height):
        for x in range(width):
            r = int(60 + 140 * (x / width))
            g = int(80 + 120 * (y / height))
            b = int(120 + 100 * ((x + y) / (width + height)))
            a = 254  # Nearly opaque — LSB available for data
            pixels[x, y] = (r, g, b, a)

    # Encode Plinian divider in ONLY the alpha channel LSB
    msg_bytes = PLINIAN_DIVIDER.encode('utf-8')
    length_bytes = struct.pack('>I', len(msg_bytes))
    payload = length_bytes + msg_bytes
    bits = []
    for byte in payload:
        for j in range(7, -1, -1):
            bits.append((byte >> j) & 1)

    bit_idx = 0
    for pix_idx in range(width * height):
        if bit_idx >= len(bits):
            break
        x = pix_idx % width
        y = pix_idx // width
        r, g, b, a = pixels[x, y]
        a = (a & 0xFE) | bits[bit_idx]
        pixels[x, y] = (r, g, b, a)
        bit_idx += 1

    path = os.path.join(OUTPUT_DIR, 'example_alpha_lsb.png')
    img.save(path)
    print(f"    -> {path} ({bit_idx} bits in alpha channel)")
    return path


# =============================================================================
# 58. JSON key ordering steganography
# =============================================================================

def generate_json_key_ordering():
    """Create a JSON file with Plinian divider encoded in object key sort order.

    For each object with 2+ keys, the choice of alphabetical vs reverse-alpha
    ordering encodes one bit per object.
    """
    print("  Generating JSON key ordering steganography...")
    import json
    import base64

    msg_bytes = PLINIAN_DIVIDER.encode('utf-8')
    length_bits = [int(b) for b in format(len(msg_bytes), '016b')]
    data_bits = []
    for b in msg_bytes:
        for j in range(7, -1, -1):
            data_bits.append((b >> j) & 1)
    all_bits = length_bits + data_bits

    # Also embed directly in metadata for cross-verification
    encoded_b64 = base64.b64encode(msg_bytes).decode()

    # Build a dataset with many small objects — each encodes one bit via key order
    specimens = [
        {"name": "Stegosaurus", "period": "Late Jurassic", "mass": 5000, "length": 9.0},
        {"name": "Triceratops", "period": "Late Cretaceous", "mass": 6000, "length": 9.0},
        {"name": "Tyrannosaurus", "period": "Late Cretaceous", "mass": 8400, "length": 12.3},
        {"name": "Velociraptor", "period": "Late Cretaceous", "mass": 15, "length": 2.0},
        {"name": "Brachiosaurus", "period": "Late Jurassic", "mass": 56000, "length": 26.0},
        {"name": "Diplodocus", "period": "Late Jurassic", "mass": 16000, "length": 26.0},
        {"name": "Allosaurus", "period": "Late Jurassic", "mass": 2300, "length": 8.5},
        {"name": "Spinosaurus", "period": "Late Cretaceous", "mass": 7400, "length": 15.0},
        {"name": "Ankylosaurus", "period": "Late Cretaceous", "mass": 6000, "length": 6.5},
        {"name": "Parasaurolophus", "period": "Late Cretaceous", "mass": 2500, "length": 9.5},
    ]

    # Generate many measurement objects to carry enough bits
    measurements = []
    bit_idx = 0
    for i in range(len(all_bits)):
        spec = specimens[i % len(specimens)]
        obj = {
            "id": i + 1,
            "specimen": spec["name"],
            "value": spec["mass"] + i,
            "unit": "kg",
            "confidence": 0.95 - (i % 10) * 0.01,
            "verified": i % 3 != 0,
        }
        if bit_idx < len(all_bits) and all_bits[bit_idx] == 1:
            # Reverse key order for bit=1
            obj = dict(reversed(list(obj.items())))
        measurements.append(obj)
        bit_idx += 1

    data = {
        "_schema": "paleontology-measurements-v2",
        "_generator": "ST3GG STEGOSAURUS WRECKS",
        "_metadata": {"payload_b64": encoded_b64},
        "measurements": measurements,
    }

    path = os.path.join(OUTPUT_DIR, 'example_key_ordering.json')
    with open(path, 'w', encoding='utf-8') as f:
        # Use json.dumps without sort_keys to preserve our ordering
        json.dump(data, f, indent=1, ensure_ascii=False)
    print(f"    -> {path} ({bit_idx} bits in {len(measurements)} object orderings)")
    return path


# =============================================================================
# 59. Capitalization encoding steganography
# =============================================================================

def generate_capitalization_encoding():
    """Create a text file with Plinian divider encoded in letter case.

    Lowercase letter = 0, uppercase letter = 1. Only alphabetic characters
    at the start of words are used as carriers to maintain readability.
    """
    print("  Generating capitalization encoding steganography...")

    cover = (
        "the stegosaurus was a large herbivorous dinosaur that lived during "
        "the late jurassic period about one hundred fifty million years ago "
        "it is best known for the distinctive row of bony plates along its "
        "back and the sharp spikes on its tail known as the thagomizer "
        "despite its massive size the stegosaurus had a remarkably small "
        "brain roughly the size of a walnut this has led to much speculation "
        "about how such a large animal could function with such limited "
        "cognitive capacity the name stegosaurus means roof lizard or covered "
        "lizard referring to the plates on its back which were once thought "
        "to lie flat like roof tiles modern research suggests these plates "
        "were used for thermoregulation and display rather than defense the "
        "thagomizer was almost certainly used as a defensive weapon against "
        "predators like allosaurus fossil evidence shows puncture marks on "
        "allosaurus bones that match the spacing of stegosaurus tail spikes "
        "perfectly this remarkable creature continues to capture our "
        "imagination and represents one of the most iconic dinosaurs ever "
        "discovered paleontologists have unearthed specimens across western "
        "north america and parts of portugal expanding our knowledge of its "
        "range and behavior the stegosaurus remains one of the most "
        "recognizable dinosaurs in the fossil record"
    )

    msg_bytes = PLINIAN_DIVIDER.encode('utf-8')
    length_bits = [int(b) for b in format(len(msg_bytes), '016b')]
    data_bits = []
    for b in msg_bytes:
        for j in range(7, -1, -1):
            data_bits.append((b >> j) & 1)
    all_bits = length_bits + data_bits

    words = cover.split(' ')
    bit_idx = 0
    result_words = []
    for word in words:
        if bit_idx < len(all_bits) and word and word[0].isalpha():
            if all_bits[bit_idx] == 1:
                word = word[0].upper() + word[1:]
            else:
                word = word[0].lower() + word[1:]
            bit_idx += 1
        result_words.append(word)

    path = os.path.join(OUTPUT_DIR, 'example_capitalization.txt')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(' '.join(result_words))
    print(f"    -> {path} ({bit_idx} bits in {len(words)} words)")
    return path


# =============================================================================
# 60. Silence interval audio steganography
# =============================================================================

def generate_silence_interval_wav():
    """Create a WAV with Plinian divider encoded in silence gap durations.

    Short silence gap (~50ms) = 0, long silence gap (~100ms) = 1.
    Bits are encoded between tone bursts.
    """
    print("  Generating silence interval WAV steganography...")
    import math

    sample_rate = 8000  # Lower rate for smaller file
    frequency = 660.0  # E5 note

    msg_bytes = PLINIAN_DIVIDER.encode('utf-8')
    length_bits = [int(b) for b in format(len(msg_bytes), '016b')]
    data_bits = []
    for b in msg_bytes:
        for j in range(7, -1, -1):
            data_bits.append((b >> j) & 1)
    all_bits = length_bits + data_bits

    tone_duration = int(sample_rate * 0.01)   # 10ms tone burst
    short_gap = int(sample_rate * 0.02)       # 20ms = bit 0
    long_gap = int(sample_rate * 0.04)        # 40ms = bit 1

    samples = []

    # Lead-in tone (sync marker: 50ms)
    for i in range(int(sample_rate * 0.05)):
        t = i / sample_rate
        samples.append(int(0.5 * math.sin(2 * math.pi * frequency * t) * 16000))

    for bit in all_bits:
        # Silence gap (duration encodes the bit)
        gap = long_gap if bit == 1 else short_gap
        samples.extend([0] * gap)

        # Tone burst (marks end of gap)
        for i in range(tone_duration):
            t = i / sample_rate
            samples.append(int(0.4 * math.sin(2 * math.pi * frequency * t) * 16000))

    # Trail-out tone (50ms)
    for i in range(int(sample_rate * 0.05)):
        t = i / sample_rate
        samples.append(int(0.5 * math.sin(2 * math.pi * frequency * t) * 16000))

    # Clamp
    samples = [max(-32768, min(32767, s)) for s in samples]

    path = os.path.join(OUTPUT_DIR, 'example_silence_interval.wav')
    with wave.open(path, 'w') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        data = struct.pack(f'<{len(samples)}h', *samples)
        wav.writeframes(data)

    print(f"    -> {path} ({len(all_bits)} bits in silence gaps)")
    return path


# =============================================================================
# Main
# =============================================================================

def main():
    print("=" * 60)
    print("ST3GG Example File Generator")
    print("=" * 60)
    print(f"Output directory: {OUTPUT_DIR}")
    print(f"Hidden message: {SECRET_MSG}")
    print()

    files = []

    # Original examples
    files.append(generate_lsb_png())
    files.append(generate_text_chunk_png())
    files.append(generate_trailing_data_png())
    files.append(generate_zero_width_text())
    files.append(generate_whitespace_text())
    files.append(generate_invisible_ink_text())
    files.append(generate_audio_lsb_wav())
    files.append(generate_exif_png())

    # Chunk 1: Image formats
    files.append(generate_lsb_bmp())
    files.append(generate_gif_comment())
    files.append(generate_gif_lsb())
    files.append(generate_tiff_metadata())
    files.append(generate_tiff_lsb())
    files.append(generate_ppm_lsb())
    files.append(generate_pgm_lsb())
    files.append(generate_svg_hidden())
    files.append(generate_ico_lsb())
    files.append(generate_webp_metadata())
    files.append(generate_webp_lsb())

    # Chunk 2: Document & structured data formats
    files.append(generate_html_hidden())
    files.append(generate_xml_hidden())
    files.append(generate_json_hidden())
    files.append(generate_csv_hidden())
    files.append(generate_yaml_hidden())
    files.append(generate_pdf_hidden())
    files.append(generate_rtf_hidden())
    files.append(generate_markdown_hidden())

    # Chunk 3: Audio, binary & archive formats
    files.append(generate_aiff_lsb())
    files.append(generate_au_lsb())
    files.append(generate_zip_hidden())
    files.append(generate_tar_hidden())
    files.append(generate_gzip_hidden())
    files.append(generate_sqlite_hidden())
    files.append(generate_hexdump_hidden())
    files.append(generate_midi_hidden())
    files.append(generate_pcap_hidden())

    # Chunk 4: Code & config formats
    files.append(generate_python_hidden())
    files.append(generate_js_hidden())
    files.append(generate_c_hidden())
    files.append(generate_css_hidden())
    files.append(generate_ini_hidden())
    files.append(generate_shell_hidden())
    files.append(generate_sql_hidden())
    files.append(generate_latex_hidden())
    files.append(generate_toml_hidden())

    # Chunk 5: Unicode & text tricks
    files.append(generate_homoglyph())
    files.append(generate_variation_selector())
    files.append(generate_combining_diacritics())
    files.append(generate_confusable_whitespace())
    files.append(generate_emoji_substitution())

    # Chunk 6: Network protocol steganography
    files.append(generate_dns_tunnel_pcap())
    files.append(generate_icmp_steg_pcap())
    files.append(generate_tcp_covert_pcap())
    files.append(generate_http_header_pcap())

    # Chunk 7: Image format tricks
    files.append(generate_png_zip_polyglot())
    files.append(generate_png_filter_encoding())
    files.append(generate_alpha_lsb())

    # Chunk 8: Misc techniques
    files.append(generate_json_key_ordering())
    files.append(generate_capitalization_encoding())
    files.append(generate_silence_interval_wav())

    print()
    print(f"Generated {len(files)} example files!")
    print()
    for f in files:
        size = os.path.getsize(f)
        print(f"  {os.path.basename(f):40s} {size:>8,} bytes")


if __name__ == '__main__':
    main()
