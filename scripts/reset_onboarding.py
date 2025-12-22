import os
import sys
import argparse
from pathlib import Path
from rich.console import Console
from rich.prompt import Confirm

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from settings.manager import SettingsManager

console = Console()

def reset_onboarding(dry_run: bool = False, nuke_data: bool = False):
    """
    Resets the onboarding state by deleting config.json.
    Optionally deletes journal data if nuke_data is True.
    """
    manager = SettingsManager()
    
    files_to_delete = []
    
    # 1. Config File (Primary Onboarding Flag)
    if manager.exists():
        files_to_delete.append(manager.config_path)
    
    # 2. Data Files (Optional)
    if nuke_data:
        data_dir = Path("data")
        if data_dir.exists():
            for f in data_dir.glob("*.jsonl"):
                files_to_delete.append(f)
            # Also Qdrant would need specific API call, but we can just warn
    
    if not files_to_delete:
        console.print("[yellow]No configuration or data files found to reset.[/yellow]")
        return

    console.print(f"[bold]Found {len(files_to_delete)} files to delete:[/bold]")
    for f in files_to_delete:
        console.print(f" - {f}")

    if nuke_data:
         console.print("[bold red]⚠ NUKE MODE: Journal data will be deleted![/bold red]")

    if dry_run:
        console.print("[blue]Dry run completed. No changes made.[/blue]")
        return

    if Confirm.ask("Are you sure you want to proceed?"):
        for f in files_to_delete:
            try:
                f.unlink()
                console.print(f"[green]Deleted {f}[/green]")
            except Exception as e:
                console.print(f"[red]Failed to delete {f}: {e}[/red]")
        
        console.print("[bold green]✔ Onboarding reset successfully.[/bold green]")
        console.print("Reload your browser. The frontend will detect the missing config and restart onboarding.")
    else:
        console.print("Operation cancelled.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reset Humanity Onboarding State")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be deleted without doing it")
    parser.add_argument("--nuke-data", action="store_true", help="Also delete journal/memory data (DESTRUCTIVE)")
    
    args = parser.parse_args()
    
    try:
        import rich
    except ImportError:
        print("Please install requirements: pip install rich")
        sys.exit(1)
        
    reset_onboarding(dry_run=args.dry_run, nuke_data=args.nuke_data)
