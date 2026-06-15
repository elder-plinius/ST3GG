#!/usr/bin/env python3
"""
stegg-cli: Thin CLI wrapper around the ST3GG steganography engine.

Designed for agent consumption — compact JSON output, subprocess-friendly,
zero context cost. Runs as a subprocess so output stays out of LLM context.

Subcommands:
    encode   -i IMAGE [-t TEXT|-f FILE] [-o OUT] [--channels C] [--bits N] [--password P]
    decode   -i IMAGE [-o OUT] [--no-auto] [--channels C] [--bits N] [--password P]
    analyze  IMAGE [--full]
    detect   IMAGE
    capacity IMAGE [--channels C] [--bits N]
    inject-chunk  -i IMAGE -o OUT [--type TYPE] [--keyword K] --text TEXT
    read-chunks   IMAGE
    inject-exif   -i IMAGE -o OUT [--comment C] [--author A] [--custom-fields JSON]
    inject-name   [--template T] [--channels C] [--count N]
    templates
    analysis-tool IMAGE ACTION
    list-tools
    crypto-status
"""

import argparse
import io
import json
import sys
from pathlib import Path

# Add repo root to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from PIL import Image

from steg_core import (
    encode, decode, create_config, calculate_capacity,
    analyze_image, detect_encoding,
)
from analysis_tools import execute_action, list_available_tools
from injector import (
    generate_injection_filename, get_jailbreak_template,
    get_jailbreak_names, inject_text_chunk, inject_itxt_chunk,
    inject_private_chunk, read_png_chunks, extract_text_chunks,
    inject_metadata_pil,
)

try:
    from crypto import encrypt, decrypt, get_available_methods, crypto_status
except Exception:
    encrypt = decrypt = None
    def get_available_methods(): return ["xor"]
    def crypto_status(): return {"cryptography_available": False, "available_methods": ["xor"]}

import numpy as np


class _Encoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.bool_,)): return bool(obj)
        if isinstance(obj, (np.integer,)): return int(obj)
        if isinstance(obj, (np.floating,)): return float(obj)
        if isinstance(obj, np.ndarray): return obj.tolist()
        return super().default(obj)


def _out(obj):
    print(json.dumps(obj, cls=_Encoder))


def _err(msg):
    _out({"error": msg})
    sys.exit(1)


def _load_image(path):
    p = Path(path).expanduser().resolve()
    if not p.exists():
        _err(f"Image not found: {p}")
    return Image.open(p), p


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------

def cmd_encode(args):
    image, _ = _load_image(args.input)

    if args.file:
        fp = Path(args.file).expanduser().resolve()
        if not fp.exists():
            _err(f"Payload file not found: {fp}")
        payload = fp.read_bytes()
    elif args.text:
        payload = args.text.encode("utf-8")
    else:
        _err("Provide --text or --file")

    out = Path(args.output).expanduser().resolve() if args.output else Path(args.input).with_name(
        Path(args.input).stem + "_steg.png"
    )

    config = create_config(
        channels=args.channels, bits=args.bits,
        compress=not args.no_compress,
        strategy=args.strategy, seed=args.seed or None,
    )

    cap = calculate_capacity(image, config)
    if len(payload) > cap["usable_bytes"]:
        _err(f"Payload too large: {len(payload)} > {cap['usable_bytes']} bytes")

    encrypted = False
    if args.password and encrypt:
        payload = encrypt(payload, args.password)
        encrypted = True

    encode(image, payload, config, str(out))
    _out({
        "output": str(out), "payload_bytes": len(payload),
        "capacity": cap["human"], "encrypted": encrypted,
    })


def cmd_decode(args):
    image, _ = _load_image(args.input)

    config = None
    detected = False
    if not args.no_auto:
        det = detect_encoding(image)
        if det:
            detected = True
            config = None
        else:
            config = create_config(
                channels=args.channels, bits=args.bits,
                strategy=args.strategy, seed=args.seed or None,
            )
    else:
        config = create_config(
            channels=args.channels, bits=args.bits,
            strategy=args.strategy, seed=args.seed or None,
        )

    try:
        data = decode(image, config)
    except Exception as e:
        _err(f"Decode failed: {e}")

    if args.password and decrypt:
        try:
            data = decrypt(data, args.password)
        except Exception as e:
            _err(f"Decryption failed: {e}")

    result = {"bytes": len(data), "auto_detected": detected}

    if args.output:
        out = Path(args.output).expanduser().resolve()
        out.write_bytes(data)
        result["output"] = str(out)

    try:
        result["text"] = data.decode("utf-8")
    except UnicodeDecodeError:
        result["hex_preview"] = data[:512].hex()

    _out(result)


def cmd_analyze(args):
    image, p = _load_image(args.image)
    analysis = analyze_image(image)

    channels = {}
    max_ind = 0.0
    for ch, d in analysis["channels"].items():
        lsb = d["lsb_ratio"]
        ind = d.get("chi_square_indicator", 0.0)
        max_ind = max(max_ind, ind)
        channels[ch] = {
            "mean": round(d["mean"], 2), "std": round(d["std"], 2),
            "lsb_zeros_pct": round(lsb["zeros"] * 100, 1),
            "chi_sq_indicator": round(ind, 4),
            "anomaly": "HIGH" if ind > 0.3 else ("slight" if ind > 0.1 else "normal"),
        }

    verdict = ("HIGH PROBABILITY" if max_ind > 0.3
               else "Possible" if max_ind > 0.1
               else "No indicators")

    result = {
        "dimensions": analysis["dimensions"], "mode": analysis["mode"],
        "pixels": analysis["total_pixels"], "channels": channels,
        "capacity": analysis["capacity_by_config"], "verdict": verdict,
    }

    if args.full:
        from analysis_tools import png_full_analysis
        try:
            result["full_analysis"] = png_full_analysis(p.read_bytes())
        except Exception as e:
            result["full_analysis_error"] = str(e)

    _out(result)


def cmd_detect(args):
    image, _ = _load_image(args.image)
    det = detect_encoding(image)
    _out({"detected": bool(det), "config": det} if det else {"detected": False})


def cmd_capacity(args):
    image, _ = _load_image(args.image)
    config = create_config(channels=args.channels, bits=args.bits)
    cap = calculate_capacity(image, config)
    _out({
        "usable_bytes": cap["usable_bytes"], "human": cap["human"],
        "pixels": image.width * image.height,
    })


def cmd_inject_chunk(args):
    p = Path(args.input).expanduser().resolve()
    if not p.exists():
        _err(f"Image not found: {p}")
    raw = p.read_bytes()

    ct = args.type
    if ct == "iTXt":
        modified = inject_itxt_chunk(raw, args.keyword, args.text)
    elif len(ct) == 4 and ct not in ("tEXt", "zTXt", "iTXt"):
        modified = inject_private_chunk(raw, ct, args.text.encode("utf-8"))
    else:
        modified = inject_text_chunk(raw, args.keyword, args.text, compressed=args.compressed)

    out = Path(args.output).expanduser().resolve()
    out.write_bytes(modified)
    _out({"output": str(out), "chunk_type": ct, "keyword": args.keyword, "bytes": len(args.text)})


def cmd_read_chunks(args):
    p = Path(args.image).expanduser().resolve()
    if not p.exists():
        _err(f"Image not found: {p}")
    raw = p.read_bytes()
    chunks = read_png_chunks(raw)
    text = extract_text_chunks(raw)

    summary = [{"type": c.get("type", "?"), "size": c.get("length", 0)} for c in chunks]
    _out({"chunks": summary, "text": text, "total": len(chunks)})


def cmd_inject_exif(args):
    p = Path(args.input).expanduser().resolve()
    if not p.exists():
        _err(f"Image not found: {p}")

    meta = {}
    if args.comment: meta["Comment"] = args.comment
    if args.author: meta["Author"] = args.author
    if args.description: meta["Description"] = args.description
    if args.title: meta["Title"] = args.title
    if args.custom_fields:
        try:
            meta.update(json.loads(args.custom_fields))
        except json.JSONDecodeError:
            _err("--custom-fields must be valid JSON")

    if not meta:
        _err("Provide at least one metadata field")

    image = Image.open(p)
    _, png_bytes = inject_metadata_pil(image, meta)
    out = Path(args.output).expanduser().resolve()
    out.write_bytes(png_bytes)
    _out({"output": str(out), "fields": list(meta.keys())})


def cmd_inject_name(args):
    names = [generate_injection_filename(args.template, args.channels) for _ in range(args.count)]
    _out({"filenames": names})


def cmd_templates(_args):
    templates = {}
    for name in get_jailbreak_names():
        content = get_jailbreak_template(name)
        templates[name] = content[:120] + ("..." if len(content) > 120 else "")
    _out({"templates": templates, "count": len(templates)})


def cmd_analysis_tool(args):
    p = Path(args.image).expanduser().resolve()
    if not p.exists():
        _err(f"File not found: {p}")

    result = execute_action(args.action, p.read_bytes())
    if hasattr(result, "to_dict"):
        _out(result.to_dict())
    else:
        _out({"result": str(result)})


def cmd_list_tools(_args):
    tools = list_available_tools()
    _out({"tools": tools, "count": len(tools)})


def cmd_crypto_status(_args):
    s = crypto_status()
    _out(s if isinstance(s, dict) else {"status": str(s)})


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def build_parser():
    p = argparse.ArgumentParser(prog="stegg-cli", description="ST3GG steganography CLI for agents")
    sub = p.add_subparsers(dest="command", required=True)

    # encode
    enc = sub.add_parser("encode", help="Encode data into an image")
    enc.add_argument("-i", "--input", required=True, help="Carrier image")
    enc.add_argument("-t", "--text", help="Text payload")
    enc.add_argument("-f", "--file", help="File payload")
    enc.add_argument("-o", "--output", help="Output path")
    enc.add_argument("--channels", default="RGB")
    enc.add_argument("--bits", type=int, default=1)
    enc.add_argument("--strategy", default="interleaved")
    enc.add_argument("--seed", type=int, default=0)
    enc.add_argument("--password", default="")
    enc.add_argument("--no-compress", action="store_true")
    enc.set_defaults(func=cmd_encode)

    # decode
    dec = sub.add_parser("decode", help="Decode data from an image")
    dec.add_argument("-i", "--input", required=True, help="Encoded image")
    dec.add_argument("-o", "--output", help="Save extracted data to file")
    dec.add_argument("--no-auto", action="store_true", help="Disable auto-detect")
    dec.add_argument("--channels", default="RGB")
    dec.add_argument("--bits", type=int, default=1)
    dec.add_argument("--strategy", default="interleaved")
    dec.add_argument("--seed", type=int, default=0)
    dec.add_argument("--password", default="")
    dec.set_defaults(func=cmd_decode)

    # analyze
    ana = sub.add_parser("analyze", help="Analyze image for steg indicators")
    ana.add_argument("image", help="Image to analyze")
    ana.add_argument("--full", action="store_true", help="Full 264-function analysis")
    ana.set_defaults(func=cmd_analyze)

    # detect
    det = sub.add_parser("detect", help="Quick STEG v3 header check")
    det.add_argument("image")
    det.set_defaults(func=cmd_detect)

    # capacity
    cap = sub.add_parser("capacity", help="Calculate carrier capacity")
    cap.add_argument("image")
    cap.add_argument("--channels", default="RGB")
    cap.add_argument("--bits", type=int, default=1)
    cap.set_defaults(func=cmd_capacity)

    # inject-chunk
    ic = sub.add_parser("inject-chunk", help="Inject PNG text chunk")
    ic.add_argument("-i", "--input", required=True)
    ic.add_argument("-o", "--output", required=True)
    ic.add_argument("--type", default="tEXt")
    ic.add_argument("--keyword", default="Comment")
    ic.add_argument("--text", required=True)
    ic.add_argument("--compressed", action="store_true")
    ic.set_defaults(func=cmd_inject_chunk)

    # read-chunks
    rc = sub.add_parser("read-chunks", help="Read PNG chunks")
    rc.add_argument("image")
    rc.set_defaults(func=cmd_read_chunks)

    # inject-exif
    ie = sub.add_parser("inject-exif", help="Inject EXIF metadata")
    ie.add_argument("-i", "--input", required=True)
    ie.add_argument("-o", "--output", required=True)
    ie.add_argument("--comment", default="")
    ie.add_argument("--author", default="")
    ie.add_argument("--description", default="")
    ie.add_argument("--title", default="")
    ie.add_argument("--custom-fields", default="")
    ie.set_defaults(func=cmd_inject_exif)

    # inject-name
    inj = sub.add_parser("inject-name", help="Generate injection filenames")
    inj.add_argument("--template", default="universal_decoder")
    inj.add_argument("--channels", default="RGB")
    inj.add_argument("--count", type=int, default=1)
    inj.set_defaults(func=cmd_inject_name)

    # templates
    tmpl = sub.add_parser("templates", help="List jailbreak templates")
    tmpl.set_defaults(func=cmd_templates)

    # analysis-tool
    at = sub.add_parser("analysis-tool", help="Run a specific analysis function")
    at.add_argument("image")
    at.add_argument("action")
    at.set_defaults(func=cmd_analysis_tool)

    # list-tools
    lt = sub.add_parser("list-tools", help="List all analysis actions")
    lt.set_defaults(func=cmd_list_tools)

    # crypto-status
    cs = sub.add_parser("crypto-status", help="Check encryption availability")
    cs.set_defaults(func=cmd_crypto_status)

    return p


def main():
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.func(args)
    except SystemExit:
        raise
    except Exception as e:
        _err(str(e))


if __name__ == "__main__":
    main()
