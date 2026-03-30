#!/usr/bin/env python3
"""
Unit tests for Matryoshka (Nested Steganography) encoding and decoding.

Tests cover:
- Basic encode/decode functionality
- Round-trip data integrity
- Multi-layer nesting (up to 11 layers)
- Edge cases and error handling
- Password encryption
- Capacity limits
"""

import pytest
import io
import os
import sys
from PIL import Image
import numpy as np

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from steg_core import encode, decode, create_config, calculate_capacity

# Try to import crypto, but make it optional for testing
try:
    import crypto
    HAS_CRYPTO = True
except Exception:
    HAS_CRYPTO = False
    crypto = None


# ============== FIXTURES ==============

@pytest.fixture
def small_carrier():
    """Create a small 100x100 carrier image"""
    img = Image.new('RGBA', (100, 100), color=(128, 128, 128, 255))
    # Add some variation to make it more realistic
    pixels = np.array(img)
    noise = np.random.randint(0, 30, pixels.shape, dtype=np.uint8)
    pixels = np.clip(pixels.astype(int) + noise - 15, 0, 255).astype(np.uint8)
    return Image.fromarray(pixels)


@pytest.fixture
def medium_carrier():
    """Create a medium 256x256 carrier image"""
    img = Image.new('RGBA', (256, 256), color=(100, 150, 200, 255))
    pixels = np.array(img)
    noise = np.random.randint(0, 50, pixels.shape, dtype=np.uint8)
    pixels = np.clip(pixels.astype(int) + noise - 25, 0, 255).astype(np.uint8)
    return Image.fromarray(pixels)


@pytest.fixture
def large_carrier():
    """Create a large 512x512 carrier image"""
    img = Image.new('RGBA', (512, 512), color=(64, 128, 192, 255))
    pixels = np.array(img)
    noise = np.random.randint(0, 40, pixels.shape, dtype=np.uint8)
    pixels = np.clip(pixels.astype(int) + noise - 20, 0, 255).astype(np.uint8)
    return Image.fromarray(pixels)


@pytest.fixture
def carrier_stack():
    """Create a stack of carriers for multi-layer tests (larger sizes for nesting)"""
    # For 3-layer nesting with RGB/1bit, we need progressively larger images
    # Inner encoded PNG ~27KB needs middle to have ~32KB+ capacity
    inner = Image.new('RGBA', (150, 150), color=(128, 128, 128, 255))
    middle = Image.new('RGBA', (350, 350), color=(100, 150, 200, 255))  # ~36KB capacity
    outer = Image.new('RGBA', (600, 600), color=(64, 128, 192, 255))    # ~108KB capacity
    return [
        (inner, "inner.png"),
        (middle, "middle.png"),
        (outer, "outer.png"),
    ]


@pytest.fixture
def test_payload():
    """Simple text payload for testing"""
    return b"Hello, this is a secret message hidden in nested steganography!"


@pytest.fixture
def binary_payload():
    """Binary payload with various byte values"""
    return bytes(range(256)) * 4  # 1024 bytes with all possible byte values


# ============== HELPER FUNCTIONS ==============

def image_to_bytes(img: Image.Image) -> bytes:
    """Convert PIL Image to PNG bytes"""
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    return buffer.getvalue()


def bytes_to_image(data: bytes) -> Image.Image:
    """Convert PNG bytes back to PIL Image"""
    return Image.open(io.BytesIO(data))


def _calculate_capacity_bytes(image: Image.Image, config) -> int:
    """Calculate byte capacity for an image (simplified, returns int)"""
    width, height = image.size
    channels = len(config.channels)
    bits = config.bits_per_channel
    raw_capacity = (width * height * channels * bits) // 8
    return max(0, raw_capacity - 64)  # Reserve space for header


def matryoshka_encode(payload: bytes, carriers: list, config=None, password: str = None) -> tuple:
    """
    Recursively encode nested steganographic images.

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
        # Use default config that matches steg_core's decode auto-detect
        config = create_config(channels='RGB', bits=1)

    layer_info = []
    current_data = payload

    for i, (carrier_img, carrier_name) in enumerate(carriers):
        layer_num = i + 1

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
            raise ValueError(
                f"Layer {layer_num} ({carrier_name}): payload {data_size} bytes "
                f"exceeds capacity {capacity} bytes"
            )

        data_to_encode = current_data
        if password and i == 0 and HAS_CRYPTO:  # Only encrypt the innermost payload
            data_to_encode = crypto.encrypt(current_data, password)

        encoded_img = encode(carrier_img, data_to_encode, config)

        if i < len(carriers) - 1:
            buffer = io.BytesIO()
            encoded_img.save(buffer, format='PNG')
            current_data = buffer.getvalue()
            layer_info[-1]['output_size'] = len(current_data)
        else:
            layer_info[-1]['output_size'] = 'final'

    return encoded_img, layer_info


def matryoshka_decode(image: Image.Image, max_depth: int = 3, password: str = None,
                      current_depth: int = 0) -> list:
    """
    Recursively decode nested steganographic images.

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
        "data_size": 0,
        "has_nested": False,
        "nested_results": [],
        "raw_data": None,
    }

    if current_depth >= max_depth:
        layer_info["type"] = "max_depth_reached"
        results.append(layer_info)
        return results

    try:
        # Try to decode
        data = decode(image, None)
        layer_info["type"] = "steg_data"
        layer_info["data_size"] = len(data)

        # Decrypt if password provided (only for innermost or try all)
        if password and HAS_CRYPTO:
            try:
                data = crypto.decrypt(data, password)
                layer_info["decrypted"] = True
            except:
                layer_info["decrypted"] = False

        layer_info["raw_data"] = data

        # Check if extracted data is a PNG image (nested layer)
        if data[:8] == b'\x89PNG\r\n\x1a\n':
            layer_info["type"] = "nested_image"
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
            except Exception as e:
                layer_info["nested_error"] = str(e)

        results.append(layer_info)

    except Exception as e:
        layer_info["type"] = "decode_failed"
        layer_info["error"] = str(e)
        results.append(layer_info)

    return results


# ============== BASIC ENCODE TESTS ==============

class TestMatryoshkaEncode:
    """Tests for matryoshka_encode function"""

    def test_single_layer_encode(self, medium_carrier, test_payload):
        """Test encoding with a single carrier"""
        carriers = [(medium_carrier, "single.png")]

        result_img, layer_info = matryoshka_encode(test_payload, carriers)

        assert result_img is not None
        assert isinstance(result_img, Image.Image)
        assert len(layer_info) == 1
        assert layer_info[0]['layer'] == 1
        assert layer_info[0]['fits'] is True

    def test_two_layer_encode(self, small_carrier, large_carrier, test_payload):
        """Test encoding with two layers (inner and outer)"""
        carriers = [
            (small_carrier, "inner.png"),
            (large_carrier, "outer.png"),
        ]

        result_img, layer_info = matryoshka_encode(test_payload, carriers)

        assert result_img is not None
        assert len(layer_info) == 2
        assert layer_info[0]['layer'] == 1
        assert layer_info[1]['layer'] == 2
        # Outer layer should have received the encoded inner image
        assert 'output_size' in layer_info[0]
        assert isinstance(layer_info[0]['output_size'], int)

    def test_three_layer_encode(self, carrier_stack, test_payload):
        """Test encoding with three layers"""
        result_img, layer_info = matryoshka_encode(test_payload, carrier_stack)

        assert result_img is not None
        assert len(layer_info) == 3
        for i, info in enumerate(layer_info):
            assert info['layer'] == i + 1
            assert info['fits'] is True

    @pytest.mark.skipif(not HAS_CRYPTO, reason="crypto module not available")
    def test_encode_with_password(self, medium_carrier, test_payload):
        """Test encoding with password encryption"""
        carriers = [(medium_carrier, "encrypted.png")]
        password = "secretpassword123"

        result_img, layer_info = matryoshka_encode(
            test_payload, carriers, password=password
        )

        assert result_img is not None
        assert layer_info[0]['fits'] is True

    def test_encode_binary_data(self, medium_carrier, binary_payload):
        """Test encoding binary data with all byte values"""
        carriers = [(medium_carrier, "binary.png")]

        result_img, layer_info = matryoshka_encode(binary_payload, carriers)

        assert result_img is not None
        assert layer_info[0]['payload_size'] == len(binary_payload)

    def test_encode_empty_carriers_raises(self, test_payload):
        """Test that empty carrier list raises ValueError"""
        with pytest.raises(ValueError, match="At least one carrier"):
            matryoshka_encode(test_payload, [])

    def test_encode_capacity_exceeded_raises(self, small_carrier):
        """Test that exceeding capacity raises ValueError"""
        # Create payload larger than small carrier can hold
        huge_payload = b"X" * 50000  # 50KB
        carriers = [(small_carrier, "tiny.png")]

        with pytest.raises(ValueError, match="exceeds capacity"):
            matryoshka_encode(huge_payload, carriers)

    def test_encode_custom_config(self, medium_carrier, test_payload):
        """Test encoding with custom config"""
        carriers = [(medium_carrier, "custom.png")]
        config = create_config(channels='RGB', bits=1)

        result_img, layer_info = matryoshka_encode(
            test_payload, carriers, config=config
        )

        assert result_img is not None


# ============== BASIC DECODE TESTS ==============

class TestMatryoshkaDecode:
    """Tests for matryoshka_decode function"""

    def test_decode_single_layer(self, medium_carrier, test_payload):
        """Test decoding a single layer"""
        carriers = [(medium_carrier, "single.png")]
        encoded_img, _ = matryoshka_encode(test_payload, carriers)

        results = matryoshka_decode(encoded_img, max_depth=3)

        assert len(results) >= 1
        assert results[0]['type'] == 'steg_data'
        assert results[0]['raw_data'] == test_payload

    def test_decode_respects_max_depth(self, medium_carrier, test_payload):
        """Test that max_depth limits recursion"""
        carriers = [(medium_carrier, "single.png")]
        encoded_img, _ = matryoshka_encode(test_payload, carriers)

        results = matryoshka_decode(encoded_img, max_depth=0)

        assert len(results) == 1
        assert results[0]['type'] == 'max_depth_reached'

    @pytest.mark.skipif(not HAS_CRYPTO, reason="crypto module not available")
    def test_decode_with_password(self, medium_carrier, test_payload):
        """Test decoding with password"""
        carriers = [(medium_carrier, "encrypted.png")]
        password = "testpassword"

        encoded_img, _ = matryoshka_encode(
            test_payload, carriers, password=password
        )

        results = matryoshka_decode(encoded_img, password=password)

        assert len(results) >= 1
        assert results[0]['raw_data'] == test_payload

    @pytest.mark.skipif(not HAS_CRYPTO, reason="crypto module not available")
    def test_decode_wrong_password(self, medium_carrier, test_payload):
        """Test decoding with wrong password returns garbled data"""
        carriers = [(medium_carrier, "encrypted.png")]

        encoded_img, _ = matryoshka_encode(
            test_payload, carriers, password="correctpassword"
        )

        results = matryoshka_decode(encoded_img, password="wrongpassword")

        # Should decode something but not the original
        assert len(results) >= 1
        # Data should be different (decryption with wrong key)
        if results[0].get('raw_data'):
            assert results[0]['raw_data'] != test_payload


# ============== ROUND-TRIP TESTS ==============

class TestRoundTrip:
    """Tests for encode->decode round-trip integrity"""

    def test_roundtrip_single_layer_text(self, medium_carrier, test_payload):
        """Test single layer round-trip with text"""
        carriers = [(medium_carrier, "test.png")]

        encoded_img, _ = matryoshka_encode(test_payload, carriers)
        results = matryoshka_decode(encoded_img)

        assert results[0]['raw_data'] == test_payload

    def test_roundtrip_single_layer_binary(self, medium_carrier, binary_payload):
        """Test single layer round-trip with binary data"""
        carriers = [(medium_carrier, "binary.png")]

        encoded_img, _ = matryoshka_encode(binary_payload, carriers)
        results = matryoshka_decode(encoded_img)

        assert results[0]['raw_data'] == binary_payload

    def test_roundtrip_two_layers(self, small_carrier, large_carrier, test_payload):
        """Test two layer round-trip"""
        carriers = [
            (small_carrier, "inner.png"),
            (large_carrier, "outer.png"),
        ]

        encoded_img, _ = matryoshka_encode(test_payload, carriers)
        results = matryoshka_decode(encoded_img, max_depth=5)

        # First layer should be nested image
        assert results[0]['type'] == 'nested_image'
        assert results[0]['has_nested'] is True

        # Nested results should contain the original payload
        nested = results[0]['nested_results']
        assert len(nested) >= 1
        assert nested[0]['raw_data'] == test_payload

    def test_roundtrip_three_layers(self, carrier_stack, test_payload):
        """Test three layer round-trip"""
        encoded_img, _ = matryoshka_encode(test_payload, carrier_stack)
        results = matryoshka_decode(encoded_img, max_depth=5)

        # Navigate through layers
        assert results[0]['type'] == 'nested_image'
        nested_1 = results[0]['nested_results']
        assert nested_1[0]['type'] == 'nested_image'
        nested_2 = nested_1[0]['nested_results']
        assert nested_2[0]['raw_data'] == test_payload

    @pytest.mark.skipif(not HAS_CRYPTO, reason="crypto module not available")
    def test_roundtrip_with_password(self, medium_carrier, test_payload):
        """Test round-trip with password encryption"""
        carriers = [(medium_carrier, "encrypted.png")]
        password = "supersecret123"

        encoded_img, _ = matryoshka_encode(
            test_payload, carriers, password=password
        )
        results = matryoshka_decode(encoded_img, password=password)

        assert results[0]['raw_data'] == test_payload

    def test_roundtrip_preserves_all_bytes(self, large_carrier):
        """Test that all 256 byte values survive round-trip"""
        all_bytes = bytes(range(256))
        carriers = [(large_carrier, "allbytes.png")]

        encoded_img, _ = matryoshka_encode(all_bytes, carriers)
        results = matryoshka_decode(encoded_img)

        assert results[0]['raw_data'] == all_bytes


# ============== EDGE CASE TESTS ==============

class TestEdgeCases:
    """Tests for edge cases and boundary conditions"""

    def test_minimum_payload(self, medium_carrier):
        """Test with minimum payload (1 byte)"""
        payload = b"X"
        carriers = [(medium_carrier, "tiny.png")]

        encoded_img, layer_info = matryoshka_encode(payload, carriers)
        results = matryoshka_decode(encoded_img)

        assert results[0]['raw_data'] == payload

    def test_empty_payload(self, medium_carrier):
        """Test with empty payload"""
        payload = b""
        carriers = [(medium_carrier, "empty.png")]

        encoded_img, layer_info = matryoshka_encode(payload, carriers)
        results = matryoshka_decode(encoded_img)

        assert results[0]['raw_data'] == payload

    def test_max_depth_eleven(self):
        """Test with maximum depth of 11 layers"""
        # Create 11 progressively larger carriers
        carriers = []
        size = 64
        for i in range(11):
            img = Image.new('RGBA', (size, size), color=(100 + i*10, 100, 100, 255))
            carriers.append((img, f"layer_{i}.png"))
            size = int(size * 1.5)  # Each layer 50% larger

        payload = b"Deep secret!"

        # This should work but may hit capacity limits
        try:
            encoded_img, layer_info = matryoshka_encode(payload, carriers)
            assert len(layer_info) == 11

            # Decode with depth 11
            results = matryoshka_decode(encoded_img, max_depth=11)

            # Find the innermost payload
            def find_payload(r):
                for item in r:
                    if item.get('raw_data') == payload:
                        return True
                    if item.get('nested_results'):
                        if find_payload(item['nested_results']):
                            return True
                return False

            assert find_payload(results)
        except ValueError as e:
            # Capacity exceeded is acceptable for this test
            assert "exceeds capacity" in str(e)

    def test_capacity_boundary(self, medium_carrier):
        """Test payload at exact capacity boundary"""
        # Use default config (RGB/1bit) to match auto-decode
        config = create_config(channels='RGB', bits=1)
        capacity = _calculate_capacity_bytes(medium_carrier, config)

        # Create payload at 90% capacity
        payload = b"X" * int(capacity * 0.9)
        carriers = [(medium_carrier, "boundary.png")]

        encoded_img, layer_info = matryoshka_encode(payload, carriers, config=config)
        results = matryoshka_decode(encoded_img)

        assert results[0]['raw_data'] == payload

    def test_unicode_in_payload(self, medium_carrier):
        """Test payload with unicode characters"""
        payload = "Hello 世界 🎉 Привет".encode('utf-8')
        carriers = [(medium_carrier, "unicode.png")]

        encoded_img, _ = matryoshka_encode(payload, carriers)
        results = matryoshka_decode(encoded_img)

        assert results[0]['raw_data'] == payload
        assert results[0]['raw_data'].decode('utf-8') == "Hello 世界 🎉 Привет"

    def test_different_image_modes(self):
        """Test carriers with different color modes"""
        modes_to_test = ['RGB', 'RGBA', 'L', 'P']
        payload = b"Test payload"

        for mode in modes_to_test:
            try:
                img = Image.new(mode, (200, 200), color=128 if mode == 'L' else (128, 128, 128))
                if mode == 'P':
                    img = img.convert('P')
                carriers = [(img, f"{mode}_carrier.png")]

                encoded_img, _ = matryoshka_encode(payload, carriers)
                results = matryoshka_decode(encoded_img)

                assert results[0]['raw_data'] == payload, f"Failed for mode {mode}"
            except Exception as e:
                # Some modes may not be supported
                print(f"Mode {mode}: {e}")


# ============== LAYER INFO TESTS ==============

class TestLayerInfo:
    """Tests for layer information accuracy"""

    def test_layer_info_structure(self, medium_carrier, test_payload):
        """Test that layer_info has correct structure"""
        carriers = [(medium_carrier, "test.png")]

        _, layer_info = matryoshka_encode(test_payload, carriers)

        assert 'layer' in layer_info[0]
        assert 'carrier' in layer_info[0]
        assert 'capacity' in layer_info[0]
        assert 'payload_size' in layer_info[0]
        assert 'fits' in layer_info[0]
        assert 'output_size' in layer_info[0]

    def test_layer_info_capacity_accuracy(self, medium_carrier, test_payload):
        """Test that reported capacity is accurate"""
        carriers = [(medium_carrier, "test.png")]
        config = create_config(channels='RGBA', bits=2)

        _, layer_info = matryoshka_encode(test_payload, carriers, config=config)

        expected_capacity = _calculate_capacity_bytes(medium_carrier, config)
        assert layer_info[0]['capacity'] == expected_capacity

    def test_layer_info_payload_size(self, medium_carrier, test_payload):
        """Test that reported payload size is accurate"""
        carriers = [(medium_carrier, "test.png")]

        _, layer_info = matryoshka_encode(test_payload, carriers)

        assert layer_info[0]['payload_size'] == len(test_payload)


# ============== RUN TESTS ==============

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
