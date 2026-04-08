#!/usr/bin/env python3
"""
STEGOSAURUS WRECKS - Command Line Interface
🦕 The most epic steg tool of all time 🦕

Usage:
    steg encode -i image.png -t "secret message" -o output.png
    steg decode -i encoded.png
    steg analyze image.png
    steg inject --help
"""

import os
import sys
import time
import typer
from pathlib import Path
from typing import Optional, List
from enum import Enum

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.syntax import Syntax
from rich.text import Text
from rich.columns import Columns
from rich.live import Live
from rich.align import Align
from rich import box

from PIL import Image

# Import our modules
from steg_core import (
    encode, decode, create_config, calculate_capacity, analyze_image,
    detect_encoding, CHANNEL_PRESETS, EncodingStrategy
)
try:
    from crypto import encrypt, decrypt, get_available_methods, crypto_status
except Exception:
    # Gracefully handle broken cryptography library (e.g., broken system install)
    encrypt = decrypt = None
    def get_available_methods(): return ["none", "xor"]
    def crypto_status(): return "⚠ crypto module unavailable (install cryptography package)"
from injector import (
    generate_injection_filename, get_template_names,
    get_jailbreak_template, get_jailbreak_names,
    zalgo_text, leetspeak
)
from ascii_art import (
    BANNER, BANNER_SMALL, STEGOSAURUS_ASCII_SIMPLE, STEGOSAURUS_SMALL,
    STATUS, FOOTER, TAGLINES, section_header, channel_bar, COLORS
)

# Initialize
console = Console()
app = typer.Typer(
    name="steg",
    help="🦕 STEGOSAURUS WRECKS - Ultimate Steganography Suite",
    add_completion=False,
    rich_markup_mode="rich",
)


class ChannelPreset(str, Enum):
    """Channel preset options"""
    R = "R"
    G = "G"
    B = "B"
    A = "A"
    RG = "RG"
    RB = "RB"
    RA = "RA"
    GB = "GB"
    GA = "GA"
    BA = "BA"
    RGB = "RGB"
    RGA = "RGA"
    RBA = "RBA"
    GBA = "GBA"
    RGBA = "RGBA"


class Strategy(str, Enum):
    """Encoding strategy options"""
    interleaved = "interleaved"
    sequential = "sequential"
    spread = "spread"
    randomized = "randomized"


def print_banner(small: bool = False):
    """Print the epic banner"""
    if small:
        console.print(BANNER_SMALL)
    else:
        console.print(BANNER)
    console.print()


def print_stego():
    """Print the stegosaurus"""
    console.print(STEGOSAURUS_ASCII_SIMPLE)


def success(msg: str):
    console.print(f"{STATUS['success']} [green]{msg}[/green]")


def error(msg: str):
    console.print(f"{STATUS['error']} [red]{msg}[/red]")


def warning(msg: str):
    console.print(f"{STATUS['warning']} [yellow]{msg}[/yellow]")


def info(msg: str):
    console.print(f"{STATUS['info']} [cyan]{msg}[/cyan]")


# ============== MAIN COMMAND ==============

@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """
    🦕 STEGOSAURUS WRECKS - Ultimate Steganography Suite

    Hide data in images using LSB steganography with style.
    """
    if ctx.invoked_subcommand is None:
        print_banner()
        print_stego()
        console.print(f"\n[dim]Run [green]steg --help[/green] for usage information[/dim]")
        console.print(FOOTER)


# ============== ENCODE COMMAND ==============

@app.command()
def encode_cmd(
    input_image: Path = typer.Option(..., "--input", "-i", help="Input carrier image"),
    output: Path = typer.Option(None, "--output", "-o", help="Output image path"),
    text: Optional[str] = typer.Option(None, "--text", "-t", help="Text to encode"),
    file: Optional[Path] = typer.Option(None, "--file", "-f", help="File to encode"),
    channels: ChannelPreset = typer.Option(ChannelPreset.RGB, "--channels", "-c", help="Channel preset"),
    bits: int = typer.Option(1, "--bits", "-b", help="Bits per channel (1-8)", min=1, max=8),
    strategy: Strategy = typer.Option(Strategy.interleaved, "--strategy", "-s", help="Encoding strategy"),
    seed: Optional[int] = typer.Option(None, "--seed", help="Random seed (for randomized strategy)"),
    password: Optional[str] = typer.Option(None, "--password", "-p", help="Encryption password"),
    no_compress: bool = typer.Option(False, "--no-compress", help="Disable compression"),
    inject_filename: bool = typer.Option(False, "--inject-name", "-j", help="Use injection filename"),
    template: Optional[str] = typer.Option(None, "--template", help="Jailbreak template to encode"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Minimal output"),
):
    """
    🔐 Encode data into an image (v3.0 - with CRC32 checksum & auto-detection)

    Examples:
        steg encode -i photo.png -t "secret message" -o hidden.png
        steg encode -i photo.png -f secret.txt -c RGBA -b 2 -p mypassword
        steg encode -i photo.png --template pliny_classic -j
        steg encode -i photo.png -t "spread out" -s spread
        steg encode -i photo.png -t "random order" -s randomized --seed 12345
    """
    if not quiet:
        print_banner(small=True)

    # Validate input
    if not input_image.exists():
        error(f"Input image not found: {input_image}")
        raise typer.Exit(1)

    if not text and not file and not template:
        error("Must provide --text, --file, or --template")
        raise typer.Exit(1)

    # Load payload
    if template:
        payload = get_jailbreak_template(template).encode('utf-8')
        info(f"Using template: [cyan]{template}[/cyan]")
    elif file:
        if not file.exists():
            error(f"File not found: {file}")
            raise typer.Exit(1)
        payload = file.read_bytes()
        info(f"Loaded file: [cyan]{file}[/cyan] ({len(payload):,} bytes)")
    else:
        payload = text.encode('utf-8')

    # Generate output filename
    if output is None:
        if inject_filename:
            output = Path(generate_injection_filename("chatgpt_decoder", channels.value))
        else:
            output = Path(f"steg_{input_image.stem}.png")

    # Load image
    try:
        image = Image.open(input_image)
        info(f"Loaded image: [cyan]{input_image}[/cyan] ({image.width}x{image.height})")
    except Exception as e:
        error(f"Failed to load image: {e}")
        raise typer.Exit(1)

    # Create config
    config = create_config(
        channels=channels.value,
        bits=bits,
        compress=not no_compress,
        strategy=strategy.value,
        seed=seed,
    )

    # Show capacity
    capacity = calculate_capacity(image, config)
    if not quiet:
        console.print(Panel(
            f"[cyan]Capacity:[/cyan] {capacity['human']}\n"
            f"[cyan]Channels:[/cyan] {channel_bar(channels.value)}\n"
            f"[cyan]Bits/Channel:[/cyan] {bits}\n"
            f"[cyan]Strategy:[/cyan] {strategy.value}\n"
            f"[cyan]Payload:[/cyan] {len(payload):,} bytes",
            title="[green]Configuration[/green]",
            border_style="green",
        ))

    # Check capacity
    if len(payload) > capacity['usable_bytes']:
        error(f"Payload too large! {len(payload):,} bytes > {capacity['usable_bytes']:,} available")
        raise typer.Exit(1)

    # Encrypt if password provided
    if password:
        with console.status("[cyan]Encrypting payload...[/cyan]", spinner="dots"):
            payload = encrypt(payload, password)
        success("Payload encrypted")

    # Encode
    with Progress(
        SpinnerColumn(style="green"),
        TextColumn("[green]Encoding...[/green]"),
        BarColumn(complete_style="green", finished_style="bright_green"),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Encoding", total=100)

        try:
            for i in range(0, 100, 10):
                progress.update(task, completed=i)
                time.sleep(0.05)

            result = encode(image, payload, config, str(output))
            progress.update(task, completed=100)

        except Exception as e:
            error(f"Encoding failed: {e}")
            raise typer.Exit(1)

    # Success output
    console.print()
    success(f"Data encoded successfully!")

    result_panel = Panel(
        f"[green]Output:[/green] {output}\n"
        f"[green]Size:[/green] {output.stat().st_size:,} bytes\n"
        f"[green]Payload:[/green] {len(payload):,} bytes\n"
        f"[green]Encrypted:[/green] {'Yes' if password else 'No'}",
        title=f"{STATUS['dino']} [green]Encoding Complete[/green]",
        border_style="green",
        box=box.DOUBLE,
    )
    console.print(result_panel)

    if not quiet:
        console.print(f"\n{FOOTER}")


# ============== DECODE COMMAND ==============

@app.command()
def decode_cmd(
    input_image: Path = typer.Option(..., "--input", "-i", help="Encoded image to decode"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file for binary data"),
    auto_detect: bool = typer.Option(True, "--auto/--no-auto", "-a", help="Auto-detect encoding config from header"),
    channels: ChannelPreset = typer.Option(ChannelPreset.RGB, "--channels", "-c", help="Channel preset (if not auto)"),
    bits: int = typer.Option(1, "--bits", "-b", help="Bits per channel (if not auto)", min=1, max=8),
    strategy: Strategy = typer.Option(Strategy.interleaved, "--strategy", "-s", help="Strategy (if not auto)"),
    seed: Optional[int] = typer.Option(None, "--seed", help="Random seed (if not auto)"),
    password: Optional[str] = typer.Option(None, "--password", "-p", help="Decryption password"),
    no_verify: bool = typer.Option(False, "--no-verify", help="Skip CRC32 checksum verification"),
    raw: bool = typer.Option(False, "--raw", help="Output raw bytes (hex)"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Minimal output"),
):
    """
    🔓 Decode data from an image (v3.0 - with auto-detection & checksum verification)

    Examples:
        steg decode -i hidden.png                     # Auto-detect config
        steg decode -i hidden.png --no-auto -c RGBA   # Manual config
        steg decode -i hidden.png -p mypassword       # With decryption
        steg decode -i hidden.png -o extracted.bin    # Save to file
    """
    if not quiet:
        print_banner(small=True)

    if not input_image.exists():
        error(f"Image not found: {input_image}")
        raise typer.Exit(1)

    # Load image
    try:
        image = Image.open(input_image)
        info(f"Loaded image: [cyan]{input_image}[/cyan] ({image.width}x{image.height})")
    except Exception as e:
        error(f"Failed to load image: {e}")
        raise typer.Exit(1)

    # Auto-detect or use manual config
    config = None
    if auto_detect:
        info("Auto-detecting encoding configuration...")
        detection = detect_encoding(image)
        if detection:
            success(f"Detected STEG v3 encoding!")
            if not quiet:
                console.print(Panel(
                    f"[cyan]Channels:[/cyan] {', '.join(detection['config']['channels'])}\n"
                    f"[cyan]Bits/Channel:[/cyan] {detection['config']['bits_per_channel']}\n"
                    f"[cyan]Strategy:[/cyan] {detection['config']['strategy']}\n"
                    f"[cyan]Compressed:[/cyan] {detection['config']['compression']}\n"
                    f"[cyan]Payload Size:[/cyan] {detection['payload_length']:,} bytes\n"
                    f"[cyan]Original Size:[/cyan] {detection['original_length']:,} bytes",
                    title="[green]Detected Configuration[/green]",
                    border_style="green",
                ))
            # Use None to let decode() use header config
            config = None
        else:
            warning("No STEG header detected, using manual config")
            config = create_config(
                channels=channels.value,
                bits=bits,
                strategy=strategy.value,
                seed=seed,
            )
    else:
        config = create_config(
            channels=channels.value,
            bits=bits,
            strategy=strategy.value,
            seed=seed,
        )
        if not quiet:
            console.print(Panel(
                f"[cyan]Channels:[/cyan] {channel_bar(channels.value)}\n"
                f"[cyan]Bits/Channel:[/cyan] {bits}\n"
                f"[cyan]Strategy:[/cyan] {strategy.value}",
                title="[cyan]Manual Configuration[/cyan]",
                border_style="cyan",
            ))

    # Decode
    with console.status("[cyan]Decoding...[/cyan]", spinner="dots"):
        try:
            data = decode(image, config, verify_checksum=not no_verify)
        except Exception as e:
            error(f"Decoding failed: {e}")
            raise typer.Exit(1)

    # Decrypt if password
    if password:
        with console.status("[cyan]Decrypting...[/cyan]", spinner="dots"):
            try:
                data = decrypt(data, password)
                success("Data decrypted")
            except Exception as e:
                error(f"Decryption failed: {e}")
                raise typer.Exit(1)

    success(f"Extracted {len(data):,} bytes")

    # Output
    if output:
        output.write_bytes(data)
        success(f"Saved to: {output}")
    elif raw:
        console.print(Panel(
            data.hex(),
            title="[cyan]Raw Data (hex)[/cyan]",
            border_style="cyan",
        ))
    else:
        # Try to decode as text
        try:
            text_data = data.decode('utf-8')
            console.print(Panel(
                text_data,
                title=f"{STATUS['decode']} [cyan]Decoded Message[/cyan]",
                border_style="cyan",
                box=box.DOUBLE,
            ))
        except UnicodeDecodeError:
            warning("Data is not valid UTF-8, showing hex preview:")
            console.print(Panel(
                data[:500].hex() + ("..." if len(data) > 500 else ""),
                title="[yellow]Binary Data (hex preview)[/yellow]",
                border_style="yellow",
            ))

    if not quiet:
        console.print(f"\n{FOOTER}")


# ============== ANALYZE COMMAND ==============

@app.command()
def analyze(
    input_image: Path = typer.Argument(..., help="Image to analyze"),
    full: bool = typer.Option(False, "--full", "-f", help="Full analysis with all channels"),
):
    """
    🔍 Analyze an image for steganographic content

    Examples:
        steg analyze photo.png
        steg analyze suspicious.png --full
    """
    print_banner(small=True)

    if not input_image.exists():
        error(f"Image not found: {input_image}")
        raise typer.Exit(1)

    try:
        image = Image.open(input_image)
    except Exception as e:
        error(f"Failed to load image: {e}")
        raise typer.Exit(1)

    with console.status("[cyan]Analyzing image...[/cyan]", spinner="dots"):
        analysis = analyze_image(image)

    # Image info
    info_table = Table(show_header=False, box=box.SIMPLE)
    info_table.add_column("Property", style="cyan")
    info_table.add_column("Value", style="white")
    info_table.add_row("File", str(input_image))
    info_table.add_row("Dimensions", f"{analysis['dimensions']['width']} x {analysis['dimensions']['height']}")
    info_table.add_row("Total Pixels", f"{analysis['total_pixels']:,}")
    info_table.add_row("Mode", analysis['mode'])
    info_table.add_row("Format", str(analysis['format']))

    console.print(Panel(info_table, title="[green]Image Information[/green]", border_style="green"))

    # Channel analysis
    channel_table = Table(box=box.ROUNDED)
    channel_table.add_column("Channel", style="bold")
    channel_table.add_column("Mean", justify="right")
    channel_table.add_column("Std Dev", justify="right")
    channel_table.add_column("LSB 0s", justify="right")
    channel_table.add_column("LSB 1s", justify="right")
    channel_table.add_column("Anomaly", justify="center")

    for ch_name, ch_data in analysis['channels'].items():
        lsb = ch_data['lsb_ratio']
        indicator = lsb['chi_square_indicator']

        if indicator < 0.1:
            anomaly = "[green]✓ Normal[/green]"
        elif indicator < 0.3:
            anomaly = "[yellow]⚠ Slight[/yellow]"
        else:
            anomaly = "[red]⚠ HIGH[/red]"

        color = {"R": "red", "G": "green", "B": "blue", "A": "white"}[ch_name]
        channel_table.add_row(
            f"[{color}]█ {ch_name}[/{color}]",
            f"{ch_data['mean']:.1f}",
            f"{ch_data['std']:.1f}",
            f"{lsb['zeros']*100:.1f}%",
            f"{lsb['ones']*100:.1f}%",
            anomaly,
        )

    console.print(Panel(channel_table, title="[cyan]Channel Analysis[/cyan]", border_style="cyan"))

    # Capacity table
    cap_table = Table(box=box.SIMPLE)
    cap_table.add_column("Config", style="cyan")
    cap_table.add_column("Capacity", style="green", justify="right")

    for config_name, capacity in analysis['capacity_by_config'].items():
        cap_table.add_row(config_name, capacity)

    console.print(Panel(cap_table, title="[magenta]Capacity Estimates[/magenta]", border_style="magenta"))

    # Verdict
    max_indicator = max(
        ch['lsb_ratio']['chi_square_indicator']
        for ch in analysis['channels'].values()
    )

    if max_indicator > 0.3:
        verdict = Panel(
            "[red bold]⚠ HIGH PROBABILITY OF HIDDEN DATA ⚠[/red bold]\n\n"
            "LSB distribution shows significant anomaly.\n"
            "This image likely contains steganographic content.",
            title="[red]Verdict[/red]",
            border_style="red",
            box=box.DOUBLE,
        )
    elif max_indicator > 0.1:
        verdict = Panel(
            "[yellow]⚠ Possible hidden data[/yellow]\n\n"
            "LSB distribution shows slight anomaly.\n"
            "Could be natural variation or light steganography.",
            title="[yellow]Verdict[/yellow]",
            border_style="yellow",
        )
    else:
        verdict = Panel(
            "[green]✓ No obvious steganographic indicators[/green]\n\n"
            "LSB distribution appears natural.\n"
            "Does not mean data isn't hidden - could use encryption or advanced techniques.",
            title="[green]Verdict[/green]",
            border_style="green",
        )

    console.print(verdict)
    console.print(f"\n{FOOTER}")


# ============== INJECT COMMAND ==============

inject_app = typer.Typer(help="💉 Prompt injection tools")
app.add_typer(inject_app, name="inject")


@inject_app.command("filename")
def inject_filename(
    template: str = typer.Option("chatgpt_decoder", "--template", "-t", help="Filename template"),
    channels: str = typer.Option("RGB", "--channels", "-c", help="Channel string"),
    count: int = typer.Option(1, "--count", "-n", help="Number of filenames to generate"),
):
    """
    Generate prompt injection filenames

    Templates: chatgpt_decoder, claude_decoder, gemini_decoder, universal_decoder,
               system_override, roleplay_trigger, dev_mode, subtle, custom
    """
    print_banner(small=True)
    console.print(section_header("Injection Filename Generator"))
    console.print()

    for i in range(count):
        filename = generate_injection_filename(template, channels)
        console.print(f"  [green]{filename}[/green]")

    console.print(f"\n{FOOTER}")


@inject_app.command("templates")
def inject_templates():
    """List available jailbreak templates"""
    print_banner(small=True)
    console.print(section_header("Jailbreak Templates"))
    console.print()

    for name in get_jailbreak_names():
        template = get_jailbreak_template(name)
        preview = template[:80].replace('\n', ' ') + "..." if len(template) > 80 else template.replace('\n', ' ')
        console.print(f"  [cyan]{name}[/cyan]")
        console.print(f"    [dim]{preview}[/dim]")
        console.print()

    console.print(f"\n{FOOTER}")


@inject_app.command("show")
def inject_show(template: str = typer.Argument(..., help="Template name")):
    """Show full content of a jailbreak template"""
    print_banner(small=True)

    content = get_jailbreak_template(template)
    if content:
        console.print(Panel(
            content,
            title=f"[cyan]{template}[/cyan]",
            border_style="cyan",
        ))
    else:
        error(f"Template not found: {template}")

    console.print(f"\n{FOOTER}")


@inject_app.command("zalgo")
def inject_zalgo(
    text: str = typer.Argument(..., help="Text to convert"),
    intensity: int = typer.Option(3, "--intensity", "-i", help="Zalgo intensity (1-5)"),
):
    """Convert text to Zalgo (glitchy) text"""
    result = zalgo_text(text, intensity)
    console.print(Panel(result, title="[magenta]Zalgo Text[/magenta]", border_style="magenta"))


@inject_app.command("leet")
def inject_leet(
    text: str = typer.Argument(..., help="Text to convert"),
    intensity: int = typer.Option(2, "--intensity", "-i", help="Leet intensity (1-3)"),
):
    """Convert text to leetspeak"""
    result = leetspeak(text, intensity)
    console.print(Panel(result, title="[green]Leetspeak[/green]", border_style="green"))


# ============== INFO COMMAND ==============

@app.command()
def info_cmd():
    """
    ℹ️ Show system information and capabilities
    """
    print_banner(small=True)
    print_stego()

    # Crypto status
    crypto = crypto_status()
    crypto_table = Table(show_header=False, box=box.SIMPLE)
    crypto_table.add_column("Property", style="cyan")
    crypto_table.add_column("Value")

    if crypto['cryptography_available']:
        crypto_table.add_row("AES Encryption", "[green]✓ Available[/green]")
    else:
        crypto_table.add_row("AES Encryption", "[yellow]✗ Not installed[/yellow]")

    crypto_table.add_row("Available Methods", ", ".join(crypto['available_methods']))
    crypto_table.add_row("Recommended", crypto['recommended'])

    console.print(Panel(crypto_table, title="[green]Cryptography[/green]", border_style="green"))

    # Channels
    channel_list = " • ".join(CHANNEL_PRESETS.keys())
    console.print(Panel(
        f"[cyan]{channel_list}[/cyan]",
        title="[cyan]Channel Presets[/cyan]",
        border_style="cyan",
    ))

    # Version info
    console.print(Panel(
        "[green]STEGOSAURUS WRECKS[/green] v2.0\n"
        "[dim]Ultimate Steganography Suite[/dim]\n\n"
        f"{TAGLINES[0]}",
        title="[magenta]About[/magenta]",
        border_style="magenta",
    ))

    console.print(f"\n{FOOTER}")


# Entry point
def main_cli():
    """Main entry point"""
    app()


if __name__ == "__main__":
    main_cli()
