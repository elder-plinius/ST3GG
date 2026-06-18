#!/usr/bin/env python3
"""
STEGOSAURUS WRECKS - Terminal User Interface
🦕 The most epic steg tool of all time 🦕

Full-screen hacker-aesthetic TUI built with Textual
"""

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import (
    Header, Footer, Static, Button, Input, Label,
    Select, Switch, TextArea, ProgressBar, TabbedContent, TabPane,
    DirectoryTree, Markdown, DataTable, RichLog
)
from textual.binding import Binding
from textual.screen import Screen
from textual import events
from textual.reactive import reactive
from textual.message import Message

from pathlib import Path
from PIL import Image
import asyncio

# Import our modules
from steg_core import (
    encode, decode, create_config, calculate_capacity, analyze_image,
    CHANNEL_PRESETS
)
from crypto import encrypt, decrypt, crypto_status
from injector import (
    generate_injection_filename, get_template_names,
    get_jailbreak_template, get_jailbreak_names,
    zalgo_text
)
from ascii_art import STEGOSAURUS_SMALL, TAGLINES, BANNER_SMALL


# ============== CUSTOM CSS ==============

CSS = """
Screen {
    background: #0a0a0a;
}

Header {
    background: #001100;
    color: #00ff00;
}

Footer {
    background: #001100;
}

#main-container {
    layout: grid;
    grid-size: 2 1;
    grid-columns: 1fr 2fr;
    padding: 1;
}

#sidebar {
    width: 100%;
    height: 100%;
    border: solid #00ff00;
    background: #0a0a0a;
    padding: 1;
}

#content {
    width: 100%;
    height: 100%;
    border: solid #00ffff;
    background: #0a0a0a;
    padding: 1;
}

.title {
    text-style: bold;
    color: #00ff00;
    text-align: center;
    padding: 1;
}

.subtitle {
    color: #00ffff;
    text-align: center;
}

.menu-button {
    width: 100%;
    margin: 1 0;
    background: #001a00;
    border: solid #00ff00;
}

.menu-button:hover {
    background: #003300;
}

.menu-button:focus {
    background: #004400;
    border: solid #00ffff;
}

.status-bar {
    dock: bottom;
    height: 3;
    background: #001100;
    border-top: solid #00ff00;
    padding: 0 1;
}

.panel {
    border: solid #00ff00;
    background: #0a0a0a;
    padding: 1;
    margin: 1;
}

.panel-title {
    background: #00ff00;
    color: #0a0a0a;
    text-style: bold;
    padding: 0 1;
}

Input {
    background: #001a00;
    border: solid #00ff00;
    color: #00ff00;
}

Input:focus {
    border: solid #00ffff;
}

Select {
    background: #001a00;
    border: solid #00ff00;
}

TextArea {
    background: #001a00;
    border: solid #00ff00;
}

Button {
    background: #001a00;
    border: solid #00ff00;
    color: #00ff00;
}

Button:hover {
    background: #003300;
    border: solid #00ffff;
}

Button.primary {
    background: #004400;
    border: solid #00ff00;
}

Button.primary:hover {
    background: #006600;
}

Button.danger {
    background: #440000;
    border: solid #ff0000;
    color: #ff0000;
}

Switch {
    background: #001a00;
}

ProgressBar {
    padding: 1;
}

ProgressBar > .bar--bar {
    color: #00ff00;
}

ProgressBar > .bar--complete {
    color: #00ffff;
}

DataTable {
    background: #0a0a0a;
}

DataTable > .datatable--header {
    background: #001a00;
    color: #00ffff;
    text-style: bold;
}

DataTable > .datatable--cursor {
    background: #003300;
}

Log {
    background: #0a0a0a;
    border: solid #00ff00;
}

.dino {
    color: #00ff00;
    text-align: center;
}

.glitch {
    color: #ff00ff;
}

.success {
    color: #00ff00;
}

.error {
    color: #ff0000;
}

.warning {
    color: #ffff00;
}

.info {
    color: #00ffff;
}

TabbedContent {
    background: #0a0a0a;
}

TabPane {
    padding: 1;
}

#dino-display {
    height: 12;
    content-align: center middle;
    color: #00ff00;
}

#capacity-display {
    height: auto;
    padding: 1;
    border: solid #00ffff;
    margin: 1 0;
}

#output-log {
    height: 100%;
    min-height: 10;
}
"""


# ============== ASCII DISPLAY ==============

DINO_ASCII = """
[green]       __
      /  '-.
     / .-. |  [cyan]STEGOSAURUS[/cyan]
    /.'   \\|    [magenta]WRECKS[/magenta]
   //   |\\  \\
  ||   | \\  |  [dim]v2.0[/dim]
 /||   |  \\ |
/ ||__/   \\/
\\  --'   |\\_\\
 '._____.' \\/[/green]
"""

HEADER_ASCII = """[green]╔═╗╔╦╗╔═╗╔═╗╔═╗╔═╗╔═╗╦ ╦╦═╗╦ ╦╔═╗[/green]  [cyan]╦ ╦╦═╗╔═╗╔═╗╦╔═╔═╗[/cyan]
[green]╚═╗ ║ ║╣ ║ ╦║ ║╚═╗╠═╣║ ║╠╦╝║ ║╚═╗[/green]  [cyan]║║║╠╦╝║╣ ║  ╠╩╗╚═╗[/cyan]
[green]╚═╝ ╩ ╚═╝╚═╝╚═╝╚═╝╩ ╩╚═╝╩╚═╚═╝╚═╝[/green]  [cyan]╚╩╝╩╚═╚═╝╚═╝╩ ╩╚═╝[/cyan]"""


# ============== MAIN APP ==============

class StegosaurusApp(App):
    """Main TUI Application"""

    TITLE = "🦕 STEGOSAURUS WRECKS"
    SUB_TITLE = "Ultimate Steganography Suite"
    CSS = CSS

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("e", "encode", "Encode"),
        Binding("d", "decode", "Decode"),
        Binding("a", "analyze", "Analyze"),
        Binding("i", "inject", "Inject"),
        Binding("?", "help", "Help"),
        Binding("ctrl+c", "quit", "Quit", show=False),
    ]

    current_image: reactive[str | None] = reactive(None)
    current_mode: reactive[str] = reactive("home")

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="main-container"):
            yield Vertical(
                Static(DINO_ASCII, id="dino-display"),
                Button("🔐 Encode", id="btn-encode", classes="menu-button"),
                Button("🔓 Decode", id="btn-decode", classes="menu-button"),
                Button("🔍 Analyze", id="btn-analyze", classes="menu-button"),
                Button("💉 Inject", id="btn-inject", classes="menu-button"),
                Button("⚙️  Settings", id="btn-settings", classes="menu-button"),
                Static("[dim]───────────────────[/dim]", classes="subtitle"),
                Static(f"[dim]{TAGLINES[0]}[/dim]", classes="subtitle"),
                id="sidebar",
            )
            with Vertical(id="content"):
                with TabbedContent(id="main-tabs"):
                    with TabPane("Home", id="tab-home"):
                        yield from self._home_content()
                    with TabPane("Encode", id="tab-encode"):
                        yield from self._encode_content()
                    with TabPane("Decode", id="tab-decode"):
                        yield from self._decode_content()
                    with TabPane("Analyze", id="tab-analyze"):
                        yield from self._analyze_content()
                    with TabPane("Inject", id="tab-inject"):
                        yield from self._inject_content()
        yield Footer()

    def _home_content(self) -> ComposeResult:
        yield Static(HEADER_ASCII, classes="title")
        yield Static("\n[cyan]» Ultimate LSB Steganography Suite «[/cyan]\n", classes="subtitle")
        yield Static("""
[green]Features:[/green]
  • Multi-channel encoding (R/G/B/A + combinations)
  • Variable bit depth (1-8 bits per channel)
  • AES-256 encryption support
  • Prompt injection filename generator
  • Jailbreak template library
  • Statistical analysis & detection

[cyan]Quick Start:[/cyan]
  [dim]E[/dim] - Encode data into image
  [dim]D[/dim] - Decode data from image
  [dim]A[/dim] - Analyze image for hidden data
  [dim]I[/dim] - Injection tools
  [dim]Q[/dim] - Quit

[magenta].-.-.-.-<={LOVE PLINY}=>-.-.-.-.[/magenta]
        """)

    def _encode_content(self) -> ComposeResult:
        yield Static("[green]═══ ENCODE DATA ═══[/green]", classes="panel-title")
        yield Horizontal(
            Vertical(
                Label("Input Image:"),
                Input(placeholder="/path/to/image.png", id="encode-input"),
                Label("Output Path:"),
                Input(placeholder="output.png (or leave empty for auto)", id="encode-output"),
                Label("Channels:"),
                Select(
                    [(k, k) for k in CHANNEL_PRESETS.keys()],
                    value="RGB",
                    id="encode-channels",
                ),
                Label("Bits per Channel:"),
                Select(
                    [(str(i), i) for i in range(1, 9)],
                    value=1,
                    id="encode-bits",
                ),
                Horizontal(
                    Switch(id="encode-compress"),
                    Label("Compress"),
                ),
                Horizontal(
                    Switch(id="encode-encrypt"),
                    Label("Encrypt"),
                ),
                Input(placeholder="Password (if encrypting)", password=True, id="encode-password"),
                id="encode-options",
            ),
            Vertical(
                Label("Data to Encode:"),
                TextArea(id="encode-text", language=None),
                Static("", id="capacity-display"),
                Button("🚀 ENCODE", id="btn-do-encode", classes="primary"),
                id="encode-data",
            ),
        )
        yield RichLog(id="encode-log", highlight=True, markup=True)

    def _decode_content(self) -> ComposeResult:
        yield Static("[cyan]═══ DECODE DATA ═══[/cyan]", classes="panel-title")
        yield Vertical(
            Horizontal(
                Vertical(
                    Label("Input Image:"),
                    Input(placeholder="/path/to/encoded.png", id="decode-input"),
                    Label("Channels:"),
                    Select(
                        [(k, k) for k in CHANNEL_PRESETS.keys()],
                        value="RGB",
                        id="decode-channels",
                    ),
                    Label("Bits per Channel:"),
                    Select(
                        [(str(i), i) for i in range(1, 9)],
                        value=1,
                        id="decode-bits",
                    ),
                    Horizontal(
                        Switch(id="decode-compress", value=True),
                        Label("Data is Compressed"),
                    ),
                    Horizontal(
                        Switch(id="decode-encrypt"),
                        Label("Data is Encrypted"),
                    ),
                    Input(placeholder="Password (if encrypted)", password=True, id="decode-password"),
                    Button("🔍 DECODE", id="btn-do-decode", classes="primary"),
                ),
                Vertical(
                    Label("Decoded Output:"),
                    TextArea(id="decode-output", language=None, read_only=True),
                ),
            ),
        )
        yield RichLog(id="decode-log", highlight=True, markup=True)

    def _analyze_content(self) -> ComposeResult:
        yield Static("[magenta]═══ ANALYZE IMAGE ═══[/magenta]", classes="panel-title")
        yield Vertical(
            Horizontal(
                Input(placeholder="/path/to/image.png", id="analyze-input"),
                Button("🔍 Analyze", id="btn-do-analyze"),
            ),
            DataTable(id="analyze-results"),
            RichLog(id="analyze-log", highlight=True, markup=True),
        )

    def _inject_content(self) -> ComposeResult:
        yield Static("[yellow]═══ INJECTION TOOLS ═══[/yellow]", classes="panel-title")
        yield Vertical(
            Label("Filename Template:"),
            Select(
                [(t, t) for t in get_template_names()],
                value="chatgpt_decoder",
                id="inject-template",
            ),
            Label("Channels:"),
            Select(
                [(k, k) for k in CHANNEL_PRESETS.keys()],
                value="RGB",
                id="inject-channels",
            ),
            Button("Generate Filename", id="btn-gen-filename"),
            Static("", id="inject-filename-output"),
            Static("[dim]───────────────────[/dim]"),
            Label("Jailbreak Templates:"),
            Select(
                [(t, t) for t in get_jailbreak_names()],
                value="pliny_classic",
                id="inject-jailbreak",
            ),
            Button("Load Template", id="btn-load-jailbreak"),
            TextArea(id="inject-jailbreak-text", language=None),
        )

    # ============== EVENT HANDLERS ==============

    def on_mount(self) -> None:
        """Initialize app"""
        self.query_one("#analyze-results", DataTable).add_columns(
            "Channel", "Mean", "Std", "LSB 0%", "LSB 1%", "Status"
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button clicks"""
        btn_id = event.button.id

        if btn_id == "btn-encode":
            self.query_one("#main-tabs", TabbedContent).active = "tab-encode"
        elif btn_id == "btn-decode":
            self.query_one("#main-tabs", TabbedContent).active = "tab-decode"
        elif btn_id == "btn-analyze":
            self.query_one("#main-tabs", TabbedContent).active = "tab-analyze"
        elif btn_id == "btn-inject":
            self.query_one("#main-tabs", TabbedContent).active = "tab-inject"
        elif btn_id == "btn-settings":
            self.notify("Settings coming soon!", title="Info")
        elif btn_id == "btn-do-encode":
            self.do_encode()
        elif btn_id == "btn-do-decode":
            self.do_decode()
        elif btn_id == "btn-do-analyze":
            self.do_analyze()
        elif btn_id == "btn-gen-filename":
            self.gen_filename()
        elif btn_id == "btn-load-jailbreak":
            self.load_jailbreak()

    def do_encode(self) -> None:
        """Perform encoding"""
        log = self.query_one("#encode-log", RichLog)
        log.clear()
        log.write("[cyan]Starting encode...[/cyan]")

        try:
            input_path = self.query_one("#encode-input", Input).value
            output_path = self.query_one("#encode-output", Input).value
            channels = self.query_one("#encode-channels", Select).value
            bits = self.query_one("#encode-bits", Select).value
            text = self.query_one("#encode-text", TextArea).text
            use_compress = self.query_one("#encode-compress", Switch).value
            use_encrypt = self.query_one("#encode-encrypt", Switch).value
            password = self.query_one("#encode-password", Input).value

            if not input_path:
                log.write("[red]Error: No input image specified[/red]")
                return
            if not text:
                log.write("[red]Error: No data to encode[/red]")
                return

            log.write(f"[dim]Loading image: {input_path}[/dim]")
            image = Image.open(input_path)
            log.write(f"[green]✓[/green] Image loaded: {image.width}x{image.height}")

            config = create_config(channels=channels, bits=bits, compress=use_compress)
            capacity = calculate_capacity(image, config)
            log.write(f"[dim]Capacity: {capacity['human']}[/dim]")

            payload = text.encode('utf-8')

            if use_encrypt and password:
                log.write("[dim]Encrypting payload...[/dim]")
                payload = encrypt(payload, password)
                log.write("[green]✓[/green] Payload encrypted")

            if not output_path:
                output_path = generate_injection_filename("chatgpt_decoder", channels)

            log.write("[dim]Encoding...[/dim]")
            result = encode(image, payload, config, output_path)

            log.write(f"[green]✓ SUCCESS![/green]")
            log.write(f"[green]Output: {output_path}[/green]")
            self.notify(f"Encoded to {output_path}", title="Success!")

        except Exception as e:
            log.write(f"[red]Error: {e}[/red]")
            self.notify(str(e), title="Error", severity="error")

    def do_decode(self) -> None:
        """Perform decoding"""
        log = self.query_one("#decode-log", RichLog)
        log.clear()
        log.write("[cyan]Starting decode...[/cyan]")

        try:
            input_path = self.query_one("#decode-input", Input).value
            channels = self.query_one("#decode-channels", Select).value
            bits = self.query_one("#decode-bits", Select).value
            use_compress = self.query_one("#decode-compress", Switch).value
            use_encrypt = self.query_one("#decode-encrypt", Switch).value
            password = self.query_one("#decode-password", Input).value

            if not input_path:
                log.write("[red]Error: No input image specified[/red]")
                return

            log.write(f"[dim]Loading image: {input_path}[/dim]")
            image = Image.open(input_path)
            log.write(f"[green]✓[/green] Image loaded")

            config = create_config(channels=channels, bits=bits, compress=use_compress)

            log.write("[dim]Decoding...[/dim]")
            data = decode(image, config)

            if use_encrypt and password:
                log.write("[dim]Decrypting...[/dim]")
                data = decrypt(data, password)
                log.write("[green]✓[/green] Decrypted")

            try:
                text = data.decode('utf-8')
                self.query_one("#decode-output", TextArea).text = text
                log.write(f"[green]✓ SUCCESS! Extracted {len(data)} bytes[/green]")
            except UnicodeDecodeError:
                self.query_one("#decode-output", TextArea).text = data.hex()
                log.write("[yellow]Binary data - showing hex[/yellow]")

            self.notify("Decode complete!", title="Success!")

        except Exception as e:
            log.write(f"[red]Error: {e}[/red]")
            self.notify(str(e), title="Error", severity="error")

    def do_analyze(self) -> None:
        """Perform analysis"""
        log = self.query_one("#analyze-log", RichLog)
        table = self.query_one("#analyze-results", DataTable)
        log.clear()
        table.clear()

        try:
            input_path = self.query_one("#analyze-input", Input).value
            if not input_path:
                log.write("[red]Error: No input image specified[/red]")
                return

            log.write(f"[dim]Analyzing: {input_path}[/dim]")
            image = Image.open(input_path)
            analysis = analyze_image(image)

            log.write(f"[green]✓[/green] {image.width}x{image.height} - {analysis['total_pixels']:,} pixels")

            for ch_name, ch_data in analysis['channels'].items():
                lsb = ch_data['lsb_ratio']
                indicator = lsb['chi_square_indicator']

                if indicator < 0.1:
                    status = "✓ Normal"
                elif indicator < 0.3:
                    status = "⚠ Slight"
                else:
                    status = "⚠ HIGH"

                table.add_row(
                    ch_name,
                    f"{ch_data['mean']:.1f}",
                    f"{ch_data['std']:.1f}",
                    f"{lsb['zeros']*100:.1f}%",
                    f"{lsb['ones']*100:.1f}%",
                    status,
                )

            max_ind = max(ch['lsb_ratio']['chi_square_indicator'] for ch in analysis['channels'].values())
            if max_ind > 0.3:
                log.write("[red]⚠ HIGH PROBABILITY OF HIDDEN DATA[/red]")
            elif max_ind > 0.1:
                log.write("[yellow]⚠ Possible hidden data[/yellow]")
            else:
                log.write("[green]✓ No obvious steganographic indicators[/green]")

        except Exception as e:
            log.write(f"[red]Error: {e}[/red]")

    def gen_filename(self) -> None:
        """Generate injection filename"""
        template = self.query_one("#inject-template", Select).value
        channels = self.query_one("#inject-channels", Select).value
        filename = generate_injection_filename(template, channels)
        self.query_one("#inject-filename-output", Static).update(f"[green]{filename}[/green]")

    def load_jailbreak(self) -> None:
        """Load jailbreak template"""
        template = self.query_one("#inject-jailbreak", Select).value
        text = get_jailbreak_template(template)
        self.query_one("#inject-jailbreak-text", TextArea).text = text

    # ============== ACTIONS ==============

    def action_encode(self) -> None:
        self.query_one("#main-tabs", TabbedContent).active = "tab-encode"

    def action_decode(self) -> None:
        self.query_one("#main-tabs", TabbedContent).active = "tab-decode"

    def action_analyze(self) -> None:
        self.query_one("#main-tabs", TabbedContent).active = "tab-analyze"

    def action_inject(self) -> None:
        self.query_one("#main-tabs", TabbedContent).active = "tab-inject"

    def action_help(self) -> None:
        self.query_one("#main-tabs", TabbedContent).active = "tab-home"


def main():
    """Entry point"""
    app = StegosaurusApp()
    app.run()


if __name__ == "__main__":
    main()
