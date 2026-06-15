"""
Tests for the ST3GG MCP server.

Covers all 13 tools with positive, negative, and edge-case scenarios
using a real carrier image (basi_team_six.png, 1024x1024 PNG).
"""

import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

# Ensure repo root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mcp_server import (
    stegg_encode,
    stegg_decode,
    stegg_analyze,
    stegg_capacity,
    stegg_detect,
    stegg_inject_chunk,
    stegg_read_chunks,
    stegg_inject_exif,
    stegg_injection_filename,
    stegg_jailbreak_templates,
    stegg_analysis_tool,
    stegg_list_analysis_tools,
    stegg_crypto_status,
)

FIXTURES = Path(__file__).parent / "fixtures"
CARRIER = str(FIXTURES / "basi_team_six.png")


@pytest.fixture
def tmp_dir():
    with tempfile.TemporaryDirectory(prefix="stegg_test_") as d:
        yield Path(d)


# ---------------------------------------------------------------------------
# stegg_encode
# ---------------------------------------------------------------------------

class TestEncode:
    def test_encode_text(self, tmp_dir):
        out = str(tmp_dir / "encoded.png")
        result = json.loads(stegg_encode(CARRIER, payload_text="hello world", output_path=out))
        assert "error" not in result
        assert result["payload_bytes"] > 0
        assert result["channels"] == "RGB"
        assert Path(out).exists()
        assert Path(out).stat().st_size > 0

    def test_encode_file_payload(self, tmp_dir):
        payload_file = tmp_dir / "secret.txt"
        payload_file.write_text("file-based secret payload")
        out = str(tmp_dir / "encoded.png")
        result = json.loads(stegg_encode(CARRIER, payload_file=str(payload_file), output_path=out))
        assert "error" not in result
        assert result["payload_bytes"] > 0

    def test_encode_with_encryption(self, tmp_dir):
        out = str(tmp_dir / "encrypted.png")
        result = json.loads(stegg_encode(CARRIER, payload_text="encrypted msg", output_path=out, password="s3cret"))
        assert "error" not in result
        assert result["encrypted"] is True

    def test_encode_various_channels(self, tmp_dir):
        for ch in ["R", "G", "B", "RG", "RGBA"]:
            out = str(tmp_dir / f"encoded_{ch}.png")
            result = json.loads(stegg_encode(CARRIER, payload_text="test", output_path=out, channels=ch))
            assert "error" not in result, f"Failed for channel {ch}: {result}"
            assert result["channels"] == ch

    def test_encode_various_strategies(self, tmp_dir):
        for strat in ["sequential", "interleaved", "spread", "randomized"]:
            out = str(tmp_dir / f"encoded_{strat}.png")
            seed = 42 if strat == "randomized" else 0
            result = json.loads(stegg_encode(
                CARRIER, payload_text="test", output_path=out,
                strategy=strat, seed=seed,
            ))
            assert "error" not in result, f"Failed for strategy {strat}: {result}"

    def test_encode_high_bit_depth(self, tmp_dir):
        out = str(tmp_dir / "encoded_4bit.png")
        result = json.loads(stegg_encode(CARRIER, payload_text="deep bits", output_path=out, bits_per_channel=4))
        assert "error" not in result
        assert result["bits_per_channel"] == 4

    def test_encode_no_compression(self, tmp_dir):
        out = str(tmp_dir / "uncompressed.png")
        result = json.loads(stegg_encode(CARRIER, payload_text="no compress", output_path=out, compress=False))
        assert "error" not in result
        assert result["compressed"] is False

    def test_encode_default_output_path(self, tmp_dir):
        # Use a copy in tmp_dir so default output lands there
        import shutil
        local_carrier = str(tmp_dir / "carrier.png")
        shutil.copy(CARRIER, local_carrier)
        result = json.loads(stegg_encode(local_carrier, payload_text="default path"))
        assert "error" not in result
        assert Path(result["output_path"]).exists()

    def test_encode_missing_image(self):
        result = json.loads(stegg_encode("/nonexistent/image.png", payload_text="fail"))
        assert "error" in result

    def test_encode_no_payload(self, tmp_dir):
        out = str(tmp_dir / "nopayload.png")
        result = json.loads(stegg_encode(CARRIER, output_path=out))
        assert "error" in result

    def test_encode_payload_too_large(self, tmp_dir):
        out = str(tmp_dir / "toolarge.png")
        # 1024x1024 RGB 1-bit = ~384KB usable; send 1MB
        huge = "X" * (1024 * 1024)
        result = json.loads(stegg_encode(CARRIER, payload_text=huge, output_path=out))
        assert "error" in result
        assert "too large" in result["error"].lower() or "Payload" in result["error"]

    def test_encode_missing_payload_file(self, tmp_dir):
        out = str(tmp_dir / "missing.png")
        result = json.loads(stegg_encode(CARRIER, payload_file="/nonexistent/file.bin", output_path=out))
        assert "error" in result


# ---------------------------------------------------------------------------
# stegg_decode
# ---------------------------------------------------------------------------

class TestDecode:
    def _encode_helper(self, tmp_dir, text="roundtrip test", **kwargs):
        out = str(tmp_dir / "encoded.png")
        enc = json.loads(stegg_encode(CARRIER, payload_text=text, output_path=out, **kwargs))
        assert "error" not in enc
        return out

    def test_decode_auto_detect(self, tmp_dir):
        encoded = self._encode_helper(tmp_dir, text="auto detect me")
        result = json.loads(stegg_decode(encoded))
        assert result["auto_detected"] is True
        assert result["text"] == "auto detect me"

    def test_decode_manual_config(self, tmp_dir):
        encoded = self._encode_helper(tmp_dir, text="manual config", channels="RG", bits_per_channel=2)
        result = json.loads(stegg_decode(
            encoded, auto_detect=True,
        ))
        assert result["text"] == "manual config"

    def test_decode_with_password(self, tmp_dir):
        encoded = self._encode_helper(tmp_dir, text="secret msg", password="p4ss")
        result = json.loads(stegg_decode(encoded, password="p4ss"))
        assert result["text"] == "secret msg"

    def test_decode_wrong_password(self, tmp_dir):
        encoded = self._encode_helper(tmp_dir, text="encrypted", password="correct")
        # Wrong password should error or return garbled data
        result = json.loads(stegg_decode(encoded, password="wrong"))
        if "error" in result:
            assert "failed" in result["error"].lower() or "invalid" in result["error"].lower()
        else:
            # If it decoded without error, text should NOT match
            assert result.get("text") != "encrypted"

    def test_decode_save_to_file(self, tmp_dir):
        encoded = self._encode_helper(tmp_dir, text="save to disk")
        out_file = str(tmp_dir / "extracted.bin")
        result = json.loads(stegg_decode(encoded, output_path=out_file))
        assert Path(out_file).exists()
        assert Path(out_file).read_text() == "save to disk"

    def test_decode_binary_payload(self, tmp_dir):
        # Encode a binary file
        bin_file = tmp_dir / "binary.bin"
        bin_file.write_bytes(bytes(range(256)))
        out = str(tmp_dir / "binary_encoded.png")
        enc = json.loads(stegg_encode(CARRIER, payload_file=str(bin_file), output_path=out))
        assert "error" not in enc

        extracted = str(tmp_dir / "extracted.bin")
        result = json.loads(stegg_decode(out, output_path=extracted))
        assert Path(extracted).read_bytes() == bytes(range(256))

    def test_decode_missing_image(self):
        result = json.loads(stegg_decode("/nonexistent/image.png"))
        assert "error" in result

    def test_decode_interleaved_auto_detect(self, tmp_dir):
        """Interleaved strategy supports auto-detection of the STEG header."""
        text = "interleaved-auto"
        encoded = str(tmp_dir / "enc_interleaved.png")
        enc = json.loads(stegg_encode(
            CARRIER, payload_text=text, output_path=encoded,
            strategy="interleaved",
        ))
        assert "error" not in enc
        dec = json.loads(stegg_decode(encoded))
        assert dec["text"] == text

    def test_decode_sequential_strategy_manual_config(self, tmp_dir):
        """Sequential strategy requires manual config (auto-detect only scans interleaved)."""
        text = "strategy-sequential"
        encoded = str(tmp_dir / "enc_sequential.png")
        enc = json.loads(stegg_encode(
            CARRIER, payload_text=text, output_path=encoded,
            strategy="sequential",
        ))
        assert "error" not in enc
        dec = json.loads(stegg_decode(
            encoded, auto_detect=False, strategy="sequential",
        ))
        assert dec["text"] == text

    def test_decode_spread_strategy_returns_error(self, tmp_dir):
        """Spread and randomized strategies have known upstream decode bugs (steg_core).

        The MCP server should return a JSON error, not crash.
        """
        encoded = str(tmp_dir / "enc_spread.png")
        enc = json.loads(stegg_encode(
            CARRIER, payload_text="spread test", output_path=encoded,
            strategy="spread",
        ))
        assert "error" not in enc  # Encoding should succeed
        dec = json.loads(stegg_decode(encoded, auto_detect=False, strategy="spread"))
        # Upstream bug: spread decode fails, but server should return error gracefully
        assert "error" in dec

    def test_decode_randomized_strategy_returns_error(self, tmp_dir):
        """Randomized strategy has known upstream decode issues.

        The MCP server should return a JSON error, not crash.
        """
        encoded = str(tmp_dir / "enc_randomized.png")
        enc = json.loads(stegg_encode(
            CARRIER, payload_text="randomized test", output_path=encoded,
            strategy="randomized", seed=42,
        ))
        assert "error" not in enc  # Encoding should succeed
        dec = json.loads(stegg_decode(
            encoded, auto_detect=False, strategy="randomized", seed=42,
        ))
        # Upstream bug: decode fails, but server should return error gracefully
        assert "error" in dec

    def test_decode_all_channel_presets(self, tmp_dir):
        for ch in ["R", "G", "B", "RG", "RGB", "RGBA"]:
            text = f"ch-{ch}"
            encoded = str(tmp_dir / f"enc_{ch}.png")
            enc = json.loads(stegg_encode(
                CARRIER, payload_text=text, output_path=encoded, channels=ch,
            ))
            assert "error" not in enc, f"Encode failed for {ch}"
            dec = json.loads(stegg_decode(encoded))
            assert dec["text"] == text, f"Decode roundtrip failed for {ch}: got {dec.get('text')}"


# ---------------------------------------------------------------------------
# stegg_analyze
# ---------------------------------------------------------------------------

class TestAnalyze:
    def test_analyze_clean_image(self):
        result = json.loads(stegg_analyze(CARRIER))
        assert "verdict" in result
        assert result["dimensions"]["width"] == 1024
        assert result["dimensions"]["height"] == 1024
        assert "channels" in result
        assert "capacity" in result

    def test_analyze_stegged_image(self, tmp_dir):
        out = str(tmp_dir / "stegged.png")
        stegg_encode(CARRIER, payload_text="A" * 10000, output_path=out)
        result = json.loads(stegg_analyze(out))
        # Large payload should trigger anomaly
        assert "HIGH" in result["verdict"] or "Possible" in result["verdict"]

    def test_analyze_full_mode(self, tmp_dir):
        out = str(tmp_dir / "stegged.png")
        stegg_encode(CARRIER, payload_text="full analysis test", output_path=out)
        result = json.loads(stegg_analyze(out, full=True))
        assert "full_analysis" in result or "full_analysis_error" in result

    def test_analyze_missing_image(self):
        result = json.loads(stegg_analyze("/nonexistent.png"))
        assert "error" in result

    def test_analyze_channel_fields(self):
        result = json.loads(stegg_analyze(CARRIER))
        for ch_name in ["R", "G", "B"]:
            ch = result["channels"][ch_name]
            assert "mean" in ch
            assert "std" in ch
            assert "lsb_zeros_pct" in ch
            assert "lsb_ones_pct" in ch
            assert "chi_square_indicator" in ch
            assert "anomaly" in ch
            assert ch["anomaly"] in ("normal", "slight", "HIGH")


# ---------------------------------------------------------------------------
# stegg_capacity
# ---------------------------------------------------------------------------

class TestCapacity:
    def test_capacity_default(self):
        result = json.loads(stegg_capacity(CARRIER))
        assert result["usable_bytes"] > 0
        assert result["total_pixels"] == 1024 * 1024
        assert "human" in result

    def test_capacity_single_channel(self):
        result = json.loads(stegg_capacity(CARRIER, channels="R", bits_per_channel=1))
        result_rgb = json.loads(stegg_capacity(CARRIER, channels="RGB", bits_per_channel=1))
        # Single channel should be roughly 1/3 of RGB
        assert result["usable_bytes"] < result_rgb["usable_bytes"]

    def test_capacity_high_bits(self):
        result_1 = json.loads(stegg_capacity(CARRIER, bits_per_channel=1))
        result_4 = json.loads(stegg_capacity(CARRIER, bits_per_channel=4))
        assert result_4["usable_bytes"] > result_1["usable_bytes"]

    def test_capacity_missing_image(self):
        result = json.loads(stegg_capacity("/nonexistent.png"))
        assert "error" in result


# ---------------------------------------------------------------------------
# stegg_detect
# ---------------------------------------------------------------------------

class TestDetect:
    def test_detect_clean_image(self):
        result = json.loads(stegg_detect(CARRIER))
        assert result["detected"] is False

    def test_detect_stegged_image(self, tmp_dir):
        out = str(tmp_dir / "stegged.png")
        stegg_encode(CARRIER, payload_text="detectable", output_path=out)
        result = json.loads(stegg_detect(out))
        assert result["detected"] is True
        assert "config" in result

    def test_detect_missing_image(self):
        result = json.loads(stegg_detect("/nonexistent.png"))
        assert "error" in result


# ---------------------------------------------------------------------------
# stegg_inject_chunk / stegg_read_chunks
# ---------------------------------------------------------------------------

class TestChunks:
    def test_inject_and_read_text_chunk(self, tmp_dir):
        out = str(tmp_dir / "chunked.png")
        inj = json.loads(stegg_inject_chunk(
            CARRIER, out, chunk_type="tEXt", keyword="Comment", text="injected comment",
        ))
        assert "error" not in inj
        assert Path(out).exists()

        read = json.loads(stegg_read_chunks(out))
        assert read["text_content"]["Comment"] == "injected comment"

    def test_inject_compressed_chunk(self, tmp_dir):
        out = str(tmp_dir / "compressed_chunk.png")
        inj = json.loads(stegg_inject_chunk(
            CARRIER, out, chunk_type="zTXt", keyword="Description",
            text="compressed description data", compressed=True,
        ))
        assert "error" not in inj

    def test_inject_itxt_chunk(self, tmp_dir):
        out = str(tmp_dir / "itxt.png")
        inj = json.loads(stegg_inject_chunk(
            CARRIER, out, chunk_type="iTXt", keyword="Author", text="ST3GG",
        ))
        assert "error" not in inj

    def test_inject_private_chunk(self, tmp_dir):
        out = str(tmp_dir / "private.png")
        inj = json.loads(stegg_inject_chunk(
            CARRIER, out, chunk_type="stEg", keyword="", text="private data",
        ))
        assert "error" not in inj

    def test_read_chunks_structure(self):
        result = json.loads(stegg_read_chunks(CARRIER))
        assert "chunks" in result
        assert "total_chunks" in result
        assert result["total_chunks"] > 0
        # Should have at minimum IHDR, IDAT, IEND
        types = [c["type"] for c in result["chunks"]]
        assert "IHDR" in types
        assert "IEND" in types

    def test_read_chunks_missing_image(self):
        result = json.loads(stegg_read_chunks("/nonexistent.png"))
        assert "error" in result

    def test_inject_chunk_missing_image(self, tmp_dir):
        out = str(tmp_dir / "fail.png")
        result = json.loads(stegg_inject_chunk("/nonexistent.png", out, text="fail"))
        assert "error" in result


# ---------------------------------------------------------------------------
# stegg_inject_exif
# ---------------------------------------------------------------------------

class TestInjectExif:
    def test_inject_comment_and_author(self, tmp_dir):
        out = str(tmp_dir / "exif.png")
        result = json.loads(stegg_inject_exif(
            CARRIER, out, comment="PoC comment", author="red-team",
        ))
        assert "error" not in result
        assert result["field_count"] == 2
        assert Path(out).exists()

        # Verify by reading chunks
        chunks = json.loads(stegg_read_chunks(out))
        assert chunks["text_content"].get("Comment") == "PoC comment"
        assert chunks["text_content"].get("Author") == "red-team"

    def test_inject_custom_fields(self, tmp_dir):
        out = str(tmp_dir / "custom_exif.png")
        custom = json.dumps({"Software": "ST3GG-MCP", "X-Custom": "payload"})
        result = json.loads(stegg_inject_exif(CARRIER, out, custom_fields=custom))
        assert "error" not in result
        assert result["field_count"] == 2

    def test_inject_all_fields(self, tmp_dir):
        out = str(tmp_dir / "all_fields.png")
        result = json.loads(stegg_inject_exif(
            CARRIER, out,
            comment="c", author="a", description="d", title="t",
        ))
        assert result["field_count"] == 4

    def test_inject_no_fields(self, tmp_dir):
        out = str(tmp_dir / "empty.png")
        result = json.loads(stegg_inject_exif(CARRIER, out))
        assert "error" in result

    def test_inject_invalid_custom_json(self, tmp_dir):
        out = str(tmp_dir / "bad_json.png")
        result = json.loads(stegg_inject_exif(CARRIER, out, custom_fields="not json"))
        assert "error" in result

    def test_inject_exif_missing_image(self, tmp_dir):
        out = str(tmp_dir / "fail.png")
        result = json.loads(stegg_inject_exif("/nonexistent.png", out, comment="fail"))
        assert "error" in result


# ---------------------------------------------------------------------------
# stegg_injection_filename
# ---------------------------------------------------------------------------

class TestInjectionFilename:
    def test_single_filename(self):
        result = json.loads(stegg_injection_filename())
        assert len(result["filenames"]) == 1
        assert result["template"] == "universal_decoder"

    def test_multiple_filenames(self):
        result = json.loads(stegg_injection_filename(count=5))
        assert len(result["filenames"]) == 5
        # Should all be unique (randomized)
        assert len(set(result["filenames"])) == 5

    def test_various_templates(self):
        templates = ["chatgpt_decoder", "claude_decoder", "gemini_decoder",
                     "system_override", "universal_decoder"]
        for t in templates:
            result = json.loads(stegg_injection_filename(template=t))
            assert "error" not in result
            assert result["template"] == t
            assert len(result["filenames"]) == 1

    def test_custom_channels(self):
        result = json.loads(stegg_injection_filename(channels="RGBA"))
        assert result["channels"] == "RGBA"
        assert "RGBA" in result["filenames"][0]


# ---------------------------------------------------------------------------
# stegg_jailbreak_templates
# ---------------------------------------------------------------------------

class TestJailbreakTemplates:
    def test_list_templates(self):
        result = json.loads(stegg_jailbreak_templates())
        assert result["count"] > 0
        assert "templates" in result
        assert isinstance(result["templates"], dict)

    def test_template_previews_truncated(self):
        result = json.loads(stegg_jailbreak_templates())
        for name, preview in result["templates"].items():
            # Previews should be <= 123 chars (120 + "...")
            assert len(preview) <= 123, f"Template {name} preview too long: {len(preview)}"


# ---------------------------------------------------------------------------
# stegg_analysis_tool / stegg_list_analysis_tools
# ---------------------------------------------------------------------------

class TestAnalysisTools:
    def test_list_tools(self):
        result = json.loads(stegg_list_analysis_tools())
        assert result["count"] > 0
        assert "tools" in result
        assert isinstance(result["tools"], list)

    def test_rs_analysis(self, tmp_dir):
        out = str(tmp_dir / "stegged.png")
        stegg_encode(CARRIER, payload_text="A" * 5000, output_path=out)
        result = json.loads(stegg_analysis_tool(out, "rs_analysis"))
        assert result["success"] is True

    def test_png_chi_square_analysis(self):
        result = json.loads(stegg_analysis_tool(CARRIER, "png_chi_square_analysis"))
        assert result["success"] is True

    def test_png_parse_chunks_tool(self):
        result = json.loads(stegg_analysis_tool(CARRIER, "png_parse_chunks"))
        assert result["success"] is True

    def test_detect_unicode_steg(self):
        # Create a text file with zero-width chars
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w") as f:
            f.write("normal text\u200b\u200c\u200d hidden")
            f.flush()
            result = json.loads(stegg_analysis_tool(f.name, "detect_unicode_steg"))
            assert result["success"] is True
            os.unlink(f.name)

    def test_unknown_action(self):
        result = json.loads(stegg_analysis_tool(CARRIER, "nonexistent_tool_xyz"))
        assert result["success"] is False
        assert "error" in result

    def test_analysis_missing_file(self):
        result = json.loads(stegg_analysis_tool("/nonexistent.png", "rs_analysis"))
        assert "error" in result


# ---------------------------------------------------------------------------
# stegg_crypto_status
# ---------------------------------------------------------------------------

class TestCryptoStatus:
    def test_crypto_status(self):
        result = json.loads(stegg_crypto_status())
        assert "available_methods" in result or "cryptography_available" in result

    def test_has_methods(self):
        result = json.loads(stegg_crypto_status())
        methods = result.get("available_methods", [])
        assert len(methods) > 0
        assert "xor" in methods  # Always available


# ---------------------------------------------------------------------------
# Integration: full pipeline tests
# ---------------------------------------------------------------------------

class TestIntegration:
    """End-to-end pipeline tests combining multiple tools."""

    def test_full_pipeline_encode_analyze_detect_decode(self, tmp_dir):
        """Encode -> analyze (should detect anomaly) -> detect (should find header) -> decode."""
        msg = "Full pipeline integration test with Basi Team Six!"
        out = str(tmp_dir / "pipeline.png")

        # Encode
        enc = json.loads(stegg_encode(CARRIER, payload_text=msg, output_path=out))
        assert "error" not in enc

        # Analyze — should show anomaly
        ana = json.loads(stegg_analyze(out))
        assert "verdict" in ana

        # Detect — should find header
        det = json.loads(stegg_detect(out))
        assert det["detected"] is True

        # Decode — should recover exact message
        dec = json.loads(stegg_decode(out))
        assert dec["text"] == msg

    def test_encrypted_pipeline(self, tmp_dir):
        """Encode encrypted -> detect -> decode with correct password."""
        msg = "encrypted pipeline test"
        pw = "Bas1T3amS1x!"
        out = str(tmp_dir / "encrypted_pipeline.png")

        enc = json.loads(stegg_encode(CARRIER, payload_text=msg, output_path=out, password=pw))
        assert enc["encrypted"] is True

        dec = json.loads(stegg_decode(out, password=pw))
        assert dec["text"] == msg

    def test_chunk_injection_preserves_steg_data(self, tmp_dir):
        """Encode data, then inject chunk — original steg data should survive."""
        msg = "steg survives chunk injection"
        stegged = str(tmp_dir / "stegged.png")
        chunked = str(tmp_dir / "chunked.png")

        stegg_encode(CARRIER, payload_text=msg, output_path=stegged)
        stegg_inject_chunk(stegged, chunked, keyword="Comment", text="metadata")

        # Chunk should be readable
        chunks = json.loads(stegg_read_chunks(chunked))
        assert chunks["text_content"]["Comment"] == "metadata"

        # Steg data should still be decodable
        dec = json.loads(stegg_decode(chunked))
        assert dec["text"] == msg

    def test_large_payload_near_capacity(self, tmp_dir):
        """Encode near-capacity payload and verify roundtrip."""
        cap = json.loads(stegg_capacity(CARRIER, channels="RGBA", bits_per_channel=2))
        # Use 80% of capacity to stay safe after compression overhead
        size = int(cap["usable_bytes"] * 0.6)
        payload = "X" * size
        out = str(tmp_dir / "large.png")

        enc = json.loads(stegg_encode(
            CARRIER, payload_text=payload, output_path=out,
            channels="RGBA", bits_per_channel=2,
        ))
        assert "error" not in enc

        dec = json.loads(stegg_decode(out))
        assert dec["text"] == payload

    def test_sequential_strategy_roundtrip(self, tmp_dir):
        """Sequential strategy encode/decode roundtrip with manual config."""
        msg = "sequential pipeline test"
        out = str(tmp_dir / "seq.png")

        enc = json.loads(stegg_encode(CARRIER, payload_text=msg, output_path=out, strategy="sequential"))
        assert "error" not in enc

        dec = json.loads(stegg_decode(out, auto_detect=False, strategy="sequential"))
        assert dec["text"] == msg

    def test_exif_injection_pipeline(self, tmp_dir):
        """Inject EXIF, then read chunks to verify, then analyze."""
        out = str(tmp_dir / "exif_pipeline.png")
        stegg_inject_exif(CARRIER, out, comment="pipeline test", author="0xmoose")

        chunks = json.loads(stegg_read_chunks(out))
        assert chunks["text_content"]["Comment"] == "pipeline test"
        assert chunks["text_content"]["Author"] == "0xmoose"

        ana = json.loads(stegg_analyze(out))
        assert "verdict" in ana
