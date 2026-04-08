"""
STEGOSAURUS WRECKS - ASCII Art & Visual Assets
🦕 The most epic steg tool of all time 🦕
"""

# Color codes for Rich
COLORS = {
    "primary": "#00ff00",      # Matrix green
    "secondary": "#00ffff",    # Cyan
    "accent": "#ff00ff",       # Magenta
    "warning": "#ffff00",      # Yellow
    "error": "#ff0000",        # Red
    "muted": "#666666",        # Gray
    "white": "#ffffff",
    "dark": "#0a0a0a",
}

# Main stegosaurus - large
STEGOSAURUS_LARGE = r"""
[green]
                         .       .
                        / `.   .' \
                .---.  <    > <    >  .---.
                |    \  \ - ~ ~ - /  /    |
                 ~-..-~             ~-..-~
             \~~~\.'                    `./~~~/
              \__/                        \__/
               /                  .-    .  \
        _._ _.-    .-~ ~-.       /       }   \/~~~/
    _.-'q  }~     /       }     {        ;    \__/
   {'__,  /      (       /      {       /      `. ,googl
    `\ \        |     |              }     /    \  ---__-..-'
      `\ \      |      `.___/-"  -._ {     /     \  / /
        `\ `.___| /\          |  \ \ {    ._..---' / /
          `-.___/  | `-._     |   \  `-.___      _/ /
                   |     `----|    `.      ``---''  /
                   |          |      `----.  __..--'
                    \         |     .-'   \'\'\'
                     \        |    /
                      `.      |   '
                        `'---'`'-'
[/green]
"""

STEGOSAURUS_MEDIUM = r"""[green]
              __
            .'  '.
           :      :    [cyan]S T E G O S A U R U S[/cyan]
           | _  _ |        [magenta]W R E C K S[/magenta]
        .--| o  o |--.
       /   '.    .'   \    [dim]>> LSB Steganography Suite <<[/dim]
      /    / `~~` \    \
     /    /        \    \
    /   .'    /\    `.   \
   / _.'    .'  `.    `._ \
  :.'      /      \      `.:
 .'       ;        ;       `.
/     _  |    __    |  _     \
|    (o) |   /  \   | (o)    |
|        |  |    |  |        |
 \      /|  |    |  |\      /
  '._  _' |  \__/  | '._  _'
     ``   |        |    ``
          |___  ___|
          |   ``   |
         /    ||    \
        '    |  |    '
            /    \
           '      '
[/green]"""

STEGOSAURUS_SMALL = r"""[green]
       __
      /  '-.
     / .-. |  [cyan]STEGOSAURUS[/cyan]
    /.'   \|    [magenta]WRECKS[/magenta]
   //   |\  \
  ||   | \  |  [dim]v2.0[/dim]
 /||   |  \ |
/ ||__/   \/
\  --'   |\_\
 '._____.' \/
[/green]"""

STEGOSAURUS_MINI = r"[green]🦕[/green]"

STEGOSAURUS_ASCII_SIMPLE = r"""
[green]        .-.     [cyan]╔═══════════════════════════════╗[/cyan]
       /   \    [cyan]║[/cyan]   [bold white]S T E G O S A U R U S[/bold white]       [cyan]║[/cyan]
   __./_   _\   [cyan]║[/cyan]       [magenta]W R E C K S[/magenta]             [cyan]║[/cyan]
  / ,    '  \   [cyan]╠═══════════════════════════════╣[/cyan]
 | |  o   o |   [cyan]║[/cyan] [dim]>> Ultimate Steg Suite <<[/dim]     [cyan]║[/cyan]
  \ \   ▽   /   [cyan]║[/cyan] [dim]>> Encode • Decode • Inject[/dim]   [cyan]║[/cyan]
   '.`'---'`.'  [cyan]╚═══════════════════════════════╝[/cyan]
     `-----`[/green]
"""

# Banner for CLI
BANNER = r"""
[green]███████╗████████╗███████╗ ██████╗  ██████╗ ███████╗ █████╗ ██╗   ██╗██████╗ ██╗   ██╗███████╗
██╔════╝╚══██╔══╝██╔════╝██╔════╝ ██╔═══██╗██╔════╝██╔══██╗██║   ██║██╔══██╗██║   ██║██╔════╝
███████╗   ██║   █████╗  ██║  ███╗██║   ██║███████╗███████║██║   ██║██████╔╝██║   ██║███████╗
╚════██║   ██║   ██╔══╝  ██║   ██║██║   ██║╚════██║██╔══██║██║   ██║██╔══██╗██║   ██║╚════██║
███████║   ██║   ███████╗╚██████╔╝╚██████╔╝███████║██║  ██║╚██████╔╝██║  ██║╚██████╔╝███████║
╚══════╝   ╚═╝   ╚══════╝ ╚═════╝  ╚═════╝ ╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚══════╝[/green]
[cyan]                      ██╗    ██╗██████╗ ███████╗ ██████╗██╗  ██╗███████╗
                      ██║    ██║██╔══██╗██╔════╝██╔════╝██║ ██╔╝██╔════╝
                      ██║ █╗ ██║██████╔╝█████╗  ██║     █████╔╝ ███████╗
                      ██║███╗██║██╔══██╗██╔══╝  ██║     ██╔═██╗ ╚════██║
                      ╚███╔███╔╝██║  ██║███████╗╚██████╗██║  ██╗███████║
                       ╚══╝╚══╝ ╚═╝  ╚═╝╚══════╝ ╚═════╝╚═╝  ╚═╝╚══════╝[/cyan]
"""

BANNER_SMALL = r"""
[green]╔═╗╔╦╗╔═╗╔═╗╔═╗╔═╗╔═╗╦ ╦╦═╗╦ ╦╔═╗[/green]  [cyan]╦ ╦╦═╗╔═╗╔═╗╦╔═╔═╗[/cyan]
[green]╚═╗ ║ ║╣ ║ ╦║ ║╚═╗╠═╣║ ║╠╦╝║ ║╚═╗[/green]  [cyan]║║║╠╦╝║╣ ║  ╠╩╗╚═╗[/cyan]
[green]╚═╝ ╩ ╚═╝╚═╝╚═╝╚═╝╩ ╩╚═╝╩╚═╚═╝╚═╝[/green]  [cyan]╚╩╝╩╚═╚═╝╚═╝╩ ╩╚═╝[/cyan]
"""

BANNER_MINI = "[green]◤[bold]STEGOSAURUS[/bold][/green] [cyan][bold]WRECKS[/bold][/cyan]"

# Loading animation frames
LOADING_FRAMES = [
    "[green]🦕       [/green]",
    "[green] 🦕      [/green]",
    "[green]  🦕     [/green]",
    "[green]   🦕    [/green]",
    "[green]    🦕   [/green]",
    "[green]     🦕  [/green]",
    "[green]      🦕 [/green]",
    "[green]       🦕[/green]",
    "[green]      🦕 [/green]",
    "[green]     🦕  [/green]",
    "[green]    🦕   [/green]",
    "[green]   🦕    [/green]",
    "[green]  🦕     [/green]",
    "[green] 🦕      [/green]",
]

# Encode animation
ENCODE_FRAMES = [
    "[green]▓[/green]░░░░░░░░░",
    "[green]▓▓[/green]░░░░░░░░",
    "[green]▓▓▓[/green]░░░░░░░",
    "[green]▓▓▓▓[/green]░░░░░░",
    "[green]▓▓▓▓▓[/green]░░░░░",
    "[green]▓▓▓▓▓▓[/green]░░░░",
    "[green]▓▓▓▓▓▓▓[/green]░░░",
    "[green]▓▓▓▓▓▓▓▓[/green]░░",
    "[green]▓▓▓▓▓▓▓▓▓[/green]░",
    "[green]▓▓▓▓▓▓▓▓▓▓[/green]",
]

# Matrix rain characters
MATRIX_CHARS = "ﾊﾐﾋｰｳｼﾅﾓﾆｻﾜﾂｵﾘｱﾎﾃﾏｹﾒｴｶｷﾑﾕﾗｾﾈｽﾀﾇﾍ01234567890"

# Box drawing characters for panels
BOX = {
    "tl": "╔", "tr": "╗", "bl": "╚", "br": "╝",
    "h": "═", "v": "║",
    "tl_r": "╭", "tr_r": "╮", "bl_r": "╰", "br_r": "╯",
    "h_s": "─", "v_s": "│",
}

# Status indicators
STATUS = {
    "success": "[green]✓[/green]",
    "error": "[red]✗[/red]",
    "warning": "[yellow]⚠[/yellow]",
    "info": "[cyan]ℹ[/cyan]",
    "loading": "[magenta]◐[/magenta]",
    "encode": "[green]⬆[/green]",
    "decode": "[cyan]⬇[/cyan]",
    "lock": "[yellow]🔒[/yellow]",
    "unlock": "[green]🔓[/green]",
    "key": "[yellow]🔑[/yellow]",
    "file": "[blue]📄[/blue]",
    "image": "[magenta]🖼[/magenta]",
    "dino": "[green]🦕[/green]",
}

# Progress bar styles
PROGRESS_STYLE = {
    "complete": "[green]█[/green]",
    "incomplete": "[dim]░[/dim]",
    "head": "[cyan]▓[/cyan]",
}

# Glitch text for effects
def glitch_text(text: str, intensity: int = 1) -> str:
    """Add glitch effects to text"""
    glitch_chars = "!@#$%^&*()_+-=[]{}|;':\",./<>?`~"
    import random
    result = []
    for char in text:
        if random.random() < 0.1 * intensity:
            result.append(f"[red]{random.choice(glitch_chars)}[/red]")
        else:
            result.append(char)
    return ''.join(result)


# Cyber-styled section headers
def section_header(title: str, width: int = 60) -> str:
    """Create a cyber-styled section header"""
    padding = (width - len(title) - 4) // 2
    return f"[cyan]{'─' * padding}[/cyan][green]《 {title} 》[/green][cyan]{'─' * padding}[/cyan]"


def box_text(text: str, style: str = "green", width: int = 60) -> str:
    """Wrap text in a styled box"""
    lines = text.split('\n')
    max_len = max(len(line) for line in lines)
    padded_width = max(max_len + 4, width)

    result = [f"[{style}]╔{'═' * (padded_width - 2)}╗[/{style}]"]
    for line in lines:
        padding = padded_width - len(line) - 4
        result.append(f"[{style}]║[/{style}] {line}{' ' * padding} [{style}]║[/{style}]")
    result.append(f"[{style}]╚{'═' * (padded_width - 2)}╝[/{style}]")

    return '\n'.join(result)


# Channel visualization
CHANNEL_DISPLAY = {
    "R": "[red]█R█[/red]",
    "G": "[green]█G█[/green]",
    "B": "[blue]█B█[/blue]",
    "A": "[white]█A█[/white]",
}

def channel_bar(channels: str) -> str:
    """Create a visual channel indicator"""
    return " ".join(CHANNEL_DISPLAY.get(c, f"[dim]█{c}█[/dim]") for c in channels)


# Taglines / quotes
TAGLINES = [
    "S̷̛̤̼̥̹͚͈̓̽̂E̴̳̘͕͍̯̮͖̖͚͋̋͠Ȩ̶͕̪͈̋ͅḌ̴̮͙̯̅̿̈́͐̏ ̷̳̗̟͕͐͂͒̉̑̕T̶̡͖͕̬̺̪̼̂̋̎̾̓͠ͅḪ̷̼͈̝̯̉͆̓̔̒̿̀̈́E̷̝̰͔̺͛̋͌̂̚ ̴̡̡̳̭̹͐̉̈̑F̵̫̜͆́̄͆͑̍́͆͠U̶̪̖̖̻̫͙̓̆̓͜T̵̛͔̭͈̙̙̠̜̤̠̓́́̈̕̕Ȕ̵̜͎̘̞̯͍̦̫͖̆Ŗ̶͍͓̤̪͍̦͔͙̿Ȩ̵͈̹̬͓̝̮̟̎̓͒̀̈́ 🔮",
    ".-.-.-.-<={LOVE PLINY}=>-.-.-.-.",
    ">> Hide in plain sight <<",
    ">> The pixels have secrets <<",
    ">> What you see is not what you get <<",
    ">> 65 million years of evolution <<",
    ">> Least Significant. Most Powerful. <<",
]

FOOTER = "[dim].-.-.-.-<={LOVE PLINY}=>-.-.-.-.[/dim]"
