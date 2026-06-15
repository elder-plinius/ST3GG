# ST3GG MCP Server — Agent Guide

## Overview

ST3GG exposes 13 steganography tools via MCP (stdio transport) for AI agent integration. Covers LSB encoding/decoding, steganalysis, PNG chunk injection, EXIF manipulation, and AI red-team payload construction.

## Quick Start

```bash
# Run MCP server
uv run --extra mcp python3 mcp_server.py

# Run tests
uv run --extra mcp --with pytest python3 -m pytest tests/test_mcp_server.py -v
```

## Tools

| Tool | Purpose |
|---|---|
| `stegg_encode` | Hide data in image via LSB (15 channel presets, 1-8 bits, 4 strategies, AES-256-GCM) |
| `stegg_decode` | Extract hidden data (auto-detect or manual config) |
| `stegg_analyze` | Chi-square anomaly detection with verdict scoring |
| `stegg_detect` | Quick STEG v3 header check |
| `stegg_capacity` | Calculate carrier capacity for given settings |
| `stegg_inject_chunk` | Inject PNG tEXt/zTXt/iTXt/private chunks |
| `stegg_read_chunks` | Read all PNG chunks and extract text content |
| `stegg_inject_exif` | Inject EXIF/metadata fields via PIL |
| `stegg_injection_filename` | Generate prompt-injection filenames for AI red-teaming |
| `stegg_jailbreak_templates` | List jailbreak prompt template previews |
| `stegg_analysis_tool` | Run any of 264+ detection functions by name |
| `stegg_list_analysis_tools` | List all available analysis actions |
| `stegg_crypto_status` | Check available encryption methods |

## Known Limitations

- Auto-detect only works for `interleaved` strategy (default). Other strategies require manual config on decode.
- `spread` and `randomized` strategies have upstream decode bugs in `steg_core.py` — encode works but decode fails to find the header.
- Full analysis mode (`stegg_analyze` with `full=True`) is PNG-only.

## Error Handling

All tools return JSON. Errors are returned as `{"error": "description"}` — tools never raise exceptions to the MCP client.
