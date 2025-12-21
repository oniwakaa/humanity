import sys
import os
from pathlib import Path
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel

# Add current dir to sys.path to import modules
sys.path.append(os.getcwd())

from settings.manager import SettingsManager
from settings.config_model import AppConfig, OllamaConfig, QdrantConfig, STTConfig
from connectors.ollama import OllamaClient
from utils.errors import OllamaError

console = Console()

def main():
    console.print(Panel.fit("Humanity: Offline-First Journal Setup", style="bold blue"))

    manager = SettingsManager()
    
    # Defaults
    default_ollama_url = "http://127.0.0.1:11434"
    default_chat_model = "llama3:latest"
    default_embed_model = "mxbai-embed-large:latest"
    default_qdrant_url = "http://127.0.0.1:6333"
    default_stt_model = str(Path("./models/ggml-base.en.bin").resolve())

    # --- Step 1: Ollama Configuration ---
    console.rule("[bold]Ollama Configuration[/bold]")
    ollama_url = Prompt.ask("Ollama Base URL", default=default_ollama_url)
    
    console.print(f"Checking connection to {ollama_url}...", style="italic")
    client = OllamaClient(base_url=ollama_url, timeout=5.0)
    
    available_models = []
    try:
        available_models = client.list_models()
        console.print(f"[green]✔ Ollama reachable.[/green] Found {len(available_models)} models.")
    except OllamaError as e:
        console.print(f"[red]✘ Could not connect to Ollama:[/red] {e}")
        if not Confirm.ask("Continue anyway? (Features will be broken)", default=False):
            sys.exit(1)

    chat_model = Prompt.ask("Chat Model Name", default=default_chat_model)
    if available_models and chat_model not in available_models:
        console.print(f"[yellow]⚠ Warning:[/yellow] Model '{chat_model}' not found in Ollama list.")

    embed_model = Prompt.ask("Embedding Model Name", default=default_embed_model)
    if available_models and embed_model not in available_models:
        console.print(f"[yellow]⚠ Warning:[/yellow] Model '{embed_model}' not found in Ollama list.")

    # --- Step 2: Qdrant Configuration ---
    console.rule("[bold]Qdrant Configuration[/bold]")
    qdrant_url = Prompt.ask("Qdrant Base URL", default=default_qdrant_url)
    # Simple check could be added here similar to Ollama, but we'll trust user/default for now 
    # or implement a simple request check if we added a specific Qdrant connector already.
    # For now, we proceed.

    # --- Step 3: STT Configuration ---
    console.rule("[bold]STT Configuration (whisper.cpp)[/bold]")
    stt_path = Prompt.ask("Path to whisper.cpp model (gguf/bin)", default=default_stt_model)
    if not Path(stt_path).exists():
        console.print(f"[yellow]⚠ Warning:[/yellow] File at {stt_path} does not exist yet.")

    # --- Step 4: Save ---
    config = AppConfig(
        ollama=OllamaConfig(
            base_url=ollama_url,
            chat_model=chat_model,
            embed_model=embed_model
        ),
        qdrant=QdrantConfig(
            url=qdrant_url
        ),
        stt=STTConfig(
            model_path=stt_path
        )
    )

    try:
        manager.save_settings(config)
        console.print(Panel(f"[green]✔ Settings saved to {manager.config_path}[/green]"))
    except Exception as e:
        console.print(f"[red]✘ Failed to save settings:[/red] {e}")

if __name__ == "__main__":
    try:
        import rich
    except ImportError:
        print("Please install requirements first: pip install rich")
        sys.exit(1)
    main()
