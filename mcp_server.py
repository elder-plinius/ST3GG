#!/usr/bin/env python3
"""
ST3GG MCP Server — Steganography toolkit for AI agents.

Exposes encode, decode, analyze, inject, and detection capabilities
via the Model Context Protocol (stdio transport).
"""

import base64
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Optional

import numpy as np

from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Bootstrap: add repo root to sys.path so local modules resolve
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).resolve().parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from PIL import Image

from steg_core import (
    encode,
    decode,
    create_config,
    calculate_capacity,
    analyze_image,
    detect_encoding,
    CHANNEL_PRESETS,
)
from analysis_tools import (
    execute_action,
    list_available_tools,
    detect_file_type,
    png_full_analysis,
)
from injector import (
    generate_injection_filename,
    get_template_names,
    get_jailbreak_template,
    get_jailbreak_names,
    inject_text_chunk,
    inject_itxt_chunk,
    inject_private_chunk,
    read_png_chunks,
    extract_text_chunks,
    inject_metadata_pil,
)

try:
    from crypto import encrypt, decrypt, get_available_methods, crypto_status
except Exception:
    encrypt = decrypt = None

    def get_available_methods():
        return ["none", "xor"]

    def crypto_status():
        return {"cryptography_available": False, "available_methods": ["xor"]}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _NumpyEncoder(json.JSONEncoder):
    """Handle numpy types that standard json can't serialize."""

    def default(self, obj):
        if isinstance(obj, (np.bool_,)):
            return bool(obj)
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)


def _json_dumps(obj: Any, **kwargs) -> str:
    """JSON serialize with numpy type support."""
    kwargs.setdefault("cls", _NumpyEncoder)
    return json.dumps(obj, **kwargs)


def _load_image(image_path: str) -> Image.Image:
    """Load an image from disk, raising a clear error on failure."""
    p = Path(image_path).expanduser().resolve()
    if not p.exists():
        raise FileNotFoundError(f"Image not found: {p}")
    return Image.open(p)


def _resolve_output(output_path: Optional[str], input_path: str, suffix: str = "_steg") -> Path:
    """Determine output path, defaulting to <input>_steg.png next to input."""
    if output_path:
        return Path(output_path).expanduser().resolve()
    inp = Path(input_path).expanduser().resolve()
    return inp.parent / f"{inp.stem}{suffix}.png"


# ---------------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "stegg",
    instructions=(
        "ST3GG steganography toolkit. Encode/decode hidden data in images, "
        "analyze files for steganographic content, inject metadata/chunks, "
        "and generate prompt-injection filenames for AI red-teaming."
    ),
)


# ---- Encode ---------------------------------------------------------------

@mcp.tool()
def stegg_encode(
    image_path: str,
    payload_text: str = "",
    payload_file: str = "",
    output_path: str = "",
    channels: str = "RGB",
    bits_per_channel: int = 1,
    strategy: str = "interleaved",
    seed: int = 0,
    password: str = "",
    compress: bool = True,
) -> str:
    """Hide data inside an image using LSB steganography.

    Supports 15 channel presets (R, G, B, A, RG, RB, ... RGBA),
    1-8 bits per channel, 4 embedding strategies, and optional
    AES-256-GCM encryption.

    Args:
        image_path: Path to carrier image (PNG recommended).
        payload_text: Text message to hide (mutually exclusive with payload_file).
        payload_file: Path to file whose bytes to hide.
        output_path: Where to write the stegged image. Defaults to <input>_steg.png.
        channels: Channel preset — one of R, G, B, A, RG, RB, RA, GB, GA, BA,
                  RGB, RGA, RBA, GBA, RGBA.
        bits_per_channel: Bits to use per channel (1-8). Higher = more capacity,
                         more visual distortion.
        strategy: Embedding strategy — sequential, interleaved, spread, randomized.
        seed: Random seed for the randomized strategy (0 = auto).
        password: Optional encryption password (AES-256-GCM if available, else XOR).
        compress: Whether to zlib-compress the payload before encoding.

    Returns:
        JSON with output_path, payload_bytes, capacity info, and encryption status.
    """
    try:
        image = _load_image(image_path)
    except (FileNotFoundError, OSError) as e:
        return _json_dumps({"error": str(e)})

    # Resolve payload
    if payload_file:
        p = Path(payload_file).expanduser().resolve()
        if not p.exists():
            return _json_dumps({"error": f"Payload file not found: {p}"})
        payload = p.read_bytes()
    elif payload_text:
        payload = payload_text.encode("utf-8")
    else:
        return _json_dumps({"error": "Provide payload_text or payload_file"})

    out = _resolve_output(output_path or "", image_path)

    config = create_config(
        channels=channels,
        bits=bits_per_channel,
        compress=compress,
        strategy=strategy,
        seed=seed if seed else None,
    )

    capacity = calculate_capacity(image, config)
    if len(payload) > capacity["usable_bytes"]:
        return _json_dumps({
            "error": f"Payload too large: {len(payload)} bytes > {capacity['usable_bytes']} available",
            "capacity": capacity["human"],
        })

    encrypted = False
    if password and encrypt:
        payload = encrypt(payload, password)
        encrypted = True

    encode(image, payload, config, str(out))

    return _json_dumps({
        "output_path": str(out),
        "payload_bytes": len(payload),
        "capacity": capacity["human"],
        "channels": channels,
        "bits_per_channel": bits_per_channel,
        "strategy": strategy,
        "encrypted": encrypted,
        "compressed": compress,
    })


# ---- Decode ---------------------------------------------------------------

@mcp.tool()
def stegg_decode(
    image_path: str,
    output_path: str = "",
    auto_detect: bool = True,
    channels: str = "RGB",
    bits_per_channel: int = 1,
    strategy: str = "interleaved",
    seed: int = 0,
    password: str = "",
) -> str:
    """Extract hidden data from a steganographic image.

    By default auto-detects the encoding config from the STEG header.
    Falls back to manual config if no header is found.

    Args:
        image_path: Path to the encoded image.
        output_path: Optional path to write extracted binary data.
        auto_detect: Try to detect encoding config from header (default True).
        channels: Channel preset if not auto-detecting.
        bits_per_channel: Bits per channel if not auto-detecting.
        strategy: Strategy if not auto-detecting.
        seed: Seed if not auto-detecting.
        password: Decryption password if the payload was encrypted.

    Returns:
        JSON with extracted text (UTF-8) or hex preview for binary data,
        plus byte count, config detected, and output_path if saved.
    """
    try:
        image = _load_image(image_path)
    except (FileNotFoundError, OSError) as e:
        return _json_dumps({"error": str(e)})

    config = None
    detected = False
    if auto_detect:
        detection = detect_encoding(image)
        if detection:
            detected = True
            config = None  # let decode() use header
        else:
            config = create_config(
                channels=channels,
                bits=bits_per_channel,
                strategy=strategy,
                seed=seed if seed else None,
            )
    else:
        config = create_config(
            channels=channels,
            bits=bits_per_channel,
            strategy=strategy,
            seed=seed if seed else None,
        )

    try:
        data = decode(image, config)
    except (ValueError, Exception) as e:
        return _json_dumps({"error": f"Decode failed: {e}"})

    if password and decrypt:
        try:
            data = decrypt(data, password)
        except Exception as e:
            return _json_dumps({"error": f"Decryption failed: {e}"})

    result: dict[str, Any] = {
        "bytes": len(data),
        "auto_detected": detected,
    }

    if output_path:
        out = Path(output_path).expanduser().resolve()
        out.write_bytes(data)
        result["output_path"] = str(out)

    # Try UTF-8
    try:
        text = data.decode("utf-8")
        result["text"] = text
        result["encoding"] = "utf-8"
    except UnicodeDecodeError:
        result["hex_preview"] = data[:512].hex()
        result["encoding"] = "binary"

    return _json_dumps(result)


# ---- Analyze --------------------------------------------------------------

@mcp.tool()
def stegg_analyze(
    image_path: str,
    full: bool = False,
) -> str:
    """Analyze an image for steganographic indicators.

    Runs chi-square analysis on each channel's LSB distribution,
    calculates capacity estimates, and optionally runs the full
    264-function analysis suite.

    Args:
        image_path: Path to the image to analyze.
        full: Run the full analysis suite (PNG only, more detailed).

    Returns:
        JSON with channel stats, anomaly indicators, capacity estimates,
        and a verdict (normal / possible / high probability).
    """
    try:
        image = _load_image(image_path)
    except (FileNotFoundError, OSError) as e:
        return _json_dumps({"error": str(e)})
    analysis = analyze_image(image)

    # Compact summary
    channels_summary = {}
    max_indicator = 0.0
    for ch_name, ch_data in analysis["channels"].items():
        lsb = ch_data["lsb_ratio"]
        indicator = ch_data.get("chi_square_indicator", 0.0)
        max_indicator = max(max_indicator, indicator)
        channels_summary[ch_name] = {
            "mean": round(ch_data["mean"], 2),
            "std": round(ch_data["std"], 2),
            "lsb_zeros_pct": round(lsb["zeros"] * 100, 1),
            "lsb_ones_pct": round(lsb["ones"] * 100, 1),
            "chi_square": round(ch_data.get("chi_square", 0.0), 4),
            "chi_square_indicator": round(indicator, 4),
            "anomaly": "HIGH" if indicator > 0.3 else ("slight" if indicator > 0.1 else "normal"),
        }

    if max_indicator > 0.3:
        verdict = "HIGH PROBABILITY of hidden data"
    elif max_indicator > 0.1:
        verdict = "Possible hidden data (slight anomaly)"
    else:
        verdict = "No obvious steganographic indicators"

    result: dict[str, Any] = {
        "dimensions": analysis["dimensions"],
        "mode": analysis["mode"],
        "total_pixels": analysis["total_pixels"],
        "channels": channels_summary,
        "capacity": analysis["capacity_by_config"],
        "verdict": verdict,
    }

    # Optional full PNG analysis
    if full:
        p = Path(image_path).expanduser().resolve()
        raw = p.read_bytes()
        try:
            full_result = png_full_analysis(raw)
            if isinstance(full_result, dict):
                result["full_analysis"] = full_result
        except Exception as e:
            result["full_analysis_error"] = str(e)

    return _json_dumps(result)


# ---- Capacity -------------------------------------------------------------

@mcp.tool()
def stegg_capacity(
    image_path: str,
    channels: str = "RGB",
    bits_per_channel: int = 1,
) -> str:
    """Calculate how much data an image can hold with given settings.

    Args:
        image_path: Path to the carrier image.
        channels: Channel preset.
        bits_per_channel: Bits per channel (1-8).

    Returns:
        JSON with capacity in bytes and human-readable form.
    """
    try:
        image = _load_image(image_path)
    except (FileNotFoundError, OSError) as e:
        return _json_dumps({"error": str(e)})
    config = create_config(channels=channels, bits=bits_per_channel)
    cap = calculate_capacity(image, config)
    return _json_dumps({
        "usable_bytes": cap["usable_bytes"],
        "human": cap["human"],
        "total_pixels": image.width * image.height,
        "channels": channels,
        "bits_per_channel": bits_per_channel,
    })


# ---- Detect ---------------------------------------------------------------

@mcp.tool()
def stegg_detect(
    image_path: str,
) -> str:
    """Quick check: does this image contain a STEG v3 header?

    Attempts auto-detection of the ST3GG encoding header to determine
    if the image was encoded with this toolkit.

    Args:
        image_path: Path to the image to check.

    Returns:
        JSON with detected (bool) and config details if found.
    """
    try:
        image = _load_image(image_path)
    except (FileNotFoundError, OSError) as e:
        return _json_dumps({"error": str(e)})
    detection = detect_encoding(image)
    if detection:
        return _json_dumps({"detected": True, "config": detection})
    return _json_dumps({"detected": False})


# ---- PNG Chunk Injection --------------------------------------------------

@mcp.tool()
def stegg_inject_chunk(
    image_path: str,
    output_path: str,
    chunk_type: str = "tEXt",
    keyword: str = "Comment",
    text: str = "",
    compressed: bool = False,
) -> str:
    """Inject a text chunk into a PNG image.

    Useful for hiding data in metadata, prompt injection via image
    metadata, or adding custom PNG chunks for red-teaming.

    Args:
        image_path: Path to source PNG.
        output_path: Where to write the modified PNG.
        chunk_type: PNG chunk type — tEXt, zTXt, iTXt, or a 4-char private type.
        keyword: Chunk keyword (e.g. Comment, Description, Author).
        text: Text content to inject.
        compressed: Use zTXt compression (only for tEXt/zTXt).

    Returns:
        JSON with output_path and chunk details.
    """
    p = Path(image_path).expanduser().resolve()
    if not p.exists():
        return _json_dumps({"error": f"Image not found: {p}"})
    raw = p.read_bytes()

    if chunk_type == "iTXt":
        modified = inject_itxt_chunk(raw, keyword, text)
    elif len(chunk_type) == 4 and chunk_type not in ("tEXt", "zTXt", "iTXt"):
        modified = inject_private_chunk(raw, chunk_type, text.encode("utf-8"))
    else:
        modified = inject_text_chunk(raw, keyword, text, compressed=compressed)

    out = Path(output_path).expanduser().resolve()
    out.write_bytes(modified)

    return _json_dumps({
        "output_path": str(out),
        "chunk_type": chunk_type,
        "keyword": keyword,
        "text_length": len(text),
        "compressed": compressed,
    })


# ---- Read PNG Chunks ------------------------------------------------------

@mcp.tool()
def stegg_read_chunks(
    image_path: str,
) -> str:
    """Read and list all chunks in a PNG image.

    Extracts text chunks (tEXt, zTXt, iTXt) and lists all chunk types
    with sizes. Useful for inspecting images for hidden metadata.

    Args:
        image_path: Path to the PNG image.

    Returns:
        JSON with chunk list and extracted text content.
    """
    p = Path(image_path).expanduser().resolve()
    if not p.exists():
        return _json_dumps({"error": f"Image not found: {p}"})
    raw = p.read_bytes()

    chunks = read_png_chunks(raw)
    text_chunks = extract_text_chunks(raw)

    # Compact chunk summary
    chunk_summary = []
    for c in chunks:
        chunk_summary.append({
            "type": c.get("type", "?"),
            "size": c.get("length", 0),
            "offset": c.get("offset", 0),
        })

    return _json_dumps({
        "chunks": chunk_summary,
        "text_content": text_chunks,
        "total_chunks": len(chunks),
    })


# ---- EXIF Injection -------------------------------------------------------

@mcp.tool()
def stegg_inject_exif(
    image_path: str,
    output_path: str,
    comment: str = "",
    author: str = "",
    description: str = "",
    title: str = "",
    custom_fields: str = "",
) -> str:
    """Inject EXIF/metadata fields into an image via PIL.

    Args:
        image_path: Path to source image.
        output_path: Where to write the modified image.
        comment: Image comment field.
        author: Author / artist field.
        description: Image description.
        title: Image title.
        custom_fields: JSON object of additional key-value pairs to inject
                       as PNG text chunks (e.g. '{"Software": "evil"}').

    Returns:
        JSON with output_path and injected fields.
    """
    p = Path(image_path).expanduser().resolve()
    if not p.exists():
        return _json_dumps({"error": f"Image not found: {p}"})

    metadata: dict[str, str] = {}
    if comment:
        metadata["Comment"] = comment
    if author:
        metadata["Author"] = author
    if description:
        metadata["Description"] = description
    if title:
        metadata["Title"] = title
    if custom_fields:
        try:
            extra = json.loads(custom_fields)
            metadata.update(extra)
        except json.JSONDecodeError:
            return _json_dumps({"error": "custom_fields must be valid JSON"})

    if not metadata:
        return _json_dumps({"error": "Provide at least one metadata field"})

    image = Image.open(p)
    _, png_bytes = inject_metadata_pil(image, metadata)

    out = Path(output_path).expanduser().resolve()
    out.write_bytes(png_bytes)

    return _json_dumps({
        "output_path": str(out),
        "injected_fields": list(metadata.keys()),
        "field_count": len(metadata),
    })


# ---- Prompt Injection Filenames ------------------------------------------

@mcp.tool()
def stegg_injection_filename(
    template: str = "universal_decoder",
    channels: str = "RGB",
    count: int = 1,
) -> str:
    """Generate prompt-injection filenames for AI red-teaming.

    Creates filenames designed to trigger LLMs into decoding steganographic
    content when processing uploaded images.

    Args:
        template: Template name — chatgpt_decoder, claude_decoder,
                  gemini_decoder, universal_decoder, system_override,
                  roleplay_trigger, dev_mode, subtle, custom.
        channels: Channel string to embed in the filename.
        count: Number of filenames to generate.

    Returns:
        JSON with list of generated filenames and template used.
    """
    filenames = [
        generate_injection_filename(template, channels)
        for _ in range(count)
    ]
    return _json_dumps({
        "template": template,
        "channels": channels,
        "filenames": filenames,
    })


# ---- Jailbreak Templates -------------------------------------------------

@mcp.tool()
def stegg_jailbreak_templates() -> str:
    """List available jailbreak prompt templates and their previews.

    These templates can be encoded into images as hidden payloads
    for AI red-teaming scenarios.

    Returns:
        JSON with template names and previews.
    """
    templates = {}
    for name in get_jailbreak_names():
        content = get_jailbreak_template(name)
        templates[name] = content[:120] + ("..." if len(content) > 120 else "")
    return _json_dumps({"templates": templates, "count": len(templates)})


# ---- Analysis Tools -------------------------------------------------------

@mcp.tool()
def stegg_analysis_tool(
    file_path: str,
    action: str,
) -> str:
    """Run a specific analysis tool from the 264-function analysis suite.

    Use stegg_list_analysis_tools to see available actions. Each tool
    returns structured results with suspicion scoring and confidence.

    Args:
        file_path: Path to the file to analyze.
        action: Analysis action name (e.g. png_chi_square_analysis,
                rs_analysis, detect_homoglyph_steg, jpeg_decode, etc.).

    Returns:
        JSON with analysis results including suspicious flag and confidence.
    """
    p = Path(file_path).expanduser().resolve()
    if not p.exists():
        return _json_dumps({"error": f"File not found: {p}"})
    data = p.read_bytes()

    result = execute_action(action, data)

    if hasattr(result, "to_dict"):
        return _json_dumps(result.to_dict(), default=str)
    return _json_dumps({"result": str(result)})


@mcp.tool()
def stegg_list_analysis_tools() -> str:
    """List all available analysis tool actions.

    Returns the full registry of 264+ analysis functions organized by
    file type (PNG, JPEG, audio, text, archive, etc.).

    Returns:
        JSON with sorted list of action names.
    """
    tools = list_available_tools()
    return _json_dumps({"tools": tools, "count": len(tools)})


# ---- Crypto Status --------------------------------------------------------

@mcp.tool()
def stegg_crypto_status() -> str:
    """Check available encryption methods.

    Returns whether AES-256-GCM is available (requires cryptography package)
    and lists all available encryption methods.

    Returns:
        JSON with crypto availability and method list.
    """
    status = crypto_status()
    if isinstance(status, dict):
        return _json_dumps(status)
    return _json_dumps({"status": str(status)})


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
