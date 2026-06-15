---
name: stegg-cli
description: "Subprocess CLI for ST3GG steganography — encode/decode, steganalysis, PNG chunk/EXIF injection, and AI red-team payloads. Runs as subprocess so output stays out of context. Use when hiding data in images, analyzing images for hidden content, injecting metadata, crafting steganographic PoCs, or detecting steganographic content. Triggers on stegg, steganography, steg, LSB, hide data in image, hidden data, steganalysis."
---

# ST3GG CLI

Subprocess steganography CLI. Output stays out of LLM context — call via `python3 stegg_cli.py <command>`. All output is JSON.

**This is the primary interface for steganography operations.** Prefer this over the MCP server for routine use (zero context cost). Fall back to MCP tools when you need results inline.

## Commands

```
encode        -i IMAGE [-t TEXT|-f FILE] [-o OUT] [--channels C] [--bits N] [--password P]
decode        -i IMAGE [-o OUT] [--no-auto] [--channels C] [--bits N] [--password P]
analyze       IMAGE [--full]
detect        IMAGE
capacity      IMAGE [--channels C] [--bits N]
inject-chunk  -i IMAGE -o OUT --text TEXT [--type tEXt] [--keyword Comment]
read-chunks   IMAGE
inject-exif   -i IMAGE -o OUT [--comment C] [--author A] [--custom-fields JSON]
inject-name   [--template T] [--channels C] [--count N]
templates
analysis-tool IMAGE ACTION
list-tools
crypto-status
```

## Quick Reference

### Encode + Verify + Decode

```bash
# Hide text
python3 stegg_cli.py encode -i carrier.png -t "secret message" -o stegged.png
# Always verify roundtrip after encoding
python3 stegg_cli.py decode -i stegged.png

# Hide file with encryption
python3 stegg_cli.py encode -i carrier.png -f payload.bin -o stegged.png --password s3cret
python3 stegg_cli.py decode -i stegged.png --password s3cret

# Decode with manual config (non-interleaved strategies)
python3 stegg_cli.py decode -i stegged.png --no-auto --strategy sequential
```

### Analyze + Detect

```bash
# Quick header check
python3 stegg_cli.py detect suspect.png

# Chi-square anomaly analysis
python3 stegg_cli.py analyze suspect.png

# Full 264-function sweep (PNG only)
python3 stegg_cli.py analyze suspect.png --full

# Specific analysis function
python3 stegg_cli.py analysis-tool suspect.png rs_analysis
python3 stegg_cli.py analysis-tool suspect.png sample_pairs_analysis
```

### Metadata Injection

```bash
# PNG chunk
python3 stegg_cli.py inject-chunk -i image.png -o out.png --text "hidden metadata"

# Private chunk type
python3 stegg_cli.py inject-chunk -i image.png -o out.png --type stEg --text "private"

# EXIF fields
python3 stegg_cli.py inject-exif -i image.png -o out.png --comment "payload" --author "red-team"

# Read chunks
python3 stegg_cli.py read-chunks image.png
```

### AI Red Team

```bash
# Generate injection filenames
python3 stegg_cli.py inject-name --template claude_decoder --channels R --count 3

# List jailbreak templates
python3 stegg_cli.py templates
```

## Key Constraints

- **Use `interleaved` strategy** (default) — only strategy with auto-detect on decode
- `spread` and `randomized` have upstream decode bugs
- `sequential` works but needs `--no-auto` on decode
- All output is JSON; errors: `{"error": "..."}` with exit code 1
- **Always check for `error` key** in JSON output before proceeding in multi-step operations
- **Always verify encode with decode** before distributing stegged images

## Installation

```bash
pip install stegg
# CLI is available as stegg-cli, or:
python3 /path/to/st3gg/stegg_cli.py <command>
```
