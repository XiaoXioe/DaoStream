#!/usr/bin/env python3
import sys
import questionary
from rich.console import Console
from sources import get_sources
from utils import play_or_view

console = Console()


def run_source_menu(source):
    while True:
        choice = questionary.select(
            f"{source.name} Scraper Menu:",
            choices=[
                "Latest Donghua",
                "Popular Today",
                "Search Donghua",
                "Switch Source",
                "Exit"
            ],
        ).ask()

        if choice == "Exit":
            sys.exit(0)
        elif choice == "Switch Source":
            return

        anime_list = []
        if choice == "Latest Donghua":
            with console.status("[bold green]Fetching latest releases...", spinner="dots"):
                anime_list = source.get_latest()
        elif choice == "Popular Today":
            with console.status("[bold green]Fetching popular today...", spinner="dots"):
                anime_list = source.get_popular()
        elif choice == "Search Donghua":
            query = questionary.text("Enter search keyword:").ask()
            if query:
                with console.status(f"[bold green]Searching for '{query}'...", spinner="dots"):
                    anime_list = source.search(query)

        if not anime_list:
            console.print("[red]No anime found.[/red]")
            continue

        anime_choice = questionary.select(
            "Select Anime:",
            choices=[{"name": a["title"], "value": a} for a in anime_list] + ["Back"],
        ).ask()

        if anime_choice == "Back":
            continue

        with console.status("[bold green]Fetching episode list...", spinner="dots"):
            episodes = source.get_episodes(anime_choice["link"])
        if not episodes:
            console.print("[red]No episodes found.[/red]")
            continue

        ep_choice = questionary.select(
            "Select Episode:",
            choices=[{"name": e["name"], "value": e} for e in episodes] + ["Back"],
        ).ask()

        if ep_choice == "Back":
            continue

        with console.status("[bold green]Fetching stream servers...", spinner="dots"):
            servers = source.get_servers(ep_choice["link"])
        if not servers:
            console.print("[red]No servers found.[/red]")
            continue

        server_choice = questionary.select(
            "Select Server/Link:",
            choices=[{"name": s["name"], "value": s} for s in servers] + ["Back"],
        ).ask()

        if server_choice == "Back":
            continue

        action = questionary.select(
            "Select Action:", choices=["Play with MPV", "View URL", "Back"]
        ).ask()

        if action != "Back":
            play_or_view(server_choice["value"], action)


def main():
    while True:
        sources = get_sources()
        if not sources:
            console.print("[red]No scraper sources configured.[/red]")
            break

        if len(sources) == 1:
            # If there's only one source, auto-select it but allow exit
            source = sources[0]
            run_source_menu(source)
            # When run_source_menu returns (e.g. Switch Source), we ask again
            # Since there's only 1, let's offer to exit or run it
            exit_choice = questionary.confirm("Exit application?").ask()
            if exit_choice:
                break
        else:
            choices = [{"name": s.name, "value": s} for s in sources] + [{"name": "Exit", "value": "exit"}]
            choice = questionary.select(
                "Select Scraper Source:",
                choices=choices
            ).ask()

            if choice == "exit" or choice is None:
                break

            run_source_menu(choice)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
