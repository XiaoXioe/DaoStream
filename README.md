# 🌌 DaoStream

`DaoStream` is a modular, lightning-fast Command Line Interface (CLI) scraper and stream resolver for Anime and Donghua. It is designed to allow you to search, browse latest releases, list episodes, and stream video content directly in your terminal using `mpv`.

---

## 🚀 Key Features

* **⚡ Pure Terminal Streaming**: No heavy browser overhead. Find your favorite show and start playing immediately using `mpv`.
* **🧩 Modular Scraper Architecture**: Built with extensibility in mind. Easily add new anime/donghua sources by extending the base class.
* **🌐 Out-of-the-Box Sources**:
  * **Anichin** (`https://anichin.moe`)
  * **AnimeXin** (`https://animexin.dev`)
  * **Donghua Fun** (`https://donghuafun.com`)
* **🔓 Advanced Stream Resolving**: Auto-resolves complex media hosting sites, including:
  * **Abyss Player** (via a local background decryption proxy server)
  * **Rumble** (extracting raw HLS streams)
  * **D-Tube** (resolving HLS endpoints)
  * **Doodstream** & **RPMvid/RPMShare**
* **🎛️ Interactive CLI Experience**: Guided menus powered by `questionary` and progress/spinner feedback powered by `rich`.
* **📺 Resolution Selector**: Interactive quality selector for HLS master playlists.

---

## 🛠️ Prerequisites

To run `DaoStream`, you need:
1. **Python 3.10+**
2. **`mpv` media player** installed and available in your system's `PATH`.
   * **Linux (Ubuntu/Debian)**: `sudo apt install mpv`
   * **macOS (Homebrew)**: `brew install mpv`
   * **Windows**: Download from [mpv.io](https://mpv.io/) and add it to your System environment variables.

---

## ⚙️ Installation & Setup

### Option 1: Standard Installation (Linux, macOS, Windows)

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/your-username/DaoStream.git
   cd DaoStream
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

### Option 2: Nix / NixOS (Flake)

If you are using Nix or NixOS with Flakes enabled, you can enter the development shell instantly. This shell automatically provisions Python, virtualenv, and the `mpv` player on your path:

```bash
nix develop
```

This will automatically configure a local `.venv` directory, install all required dependencies, and launch you directly into a ready-to-run environment.

---

## 🎮 Usage

Launch the interactive CLI by running the main entrypoint:
```bash
python3 main.py
```

### Navigating the App:
1. **Select Scraper Source**: Choose between Anichin, AnimeXin, or Donghua Fun.
2. **Select Menu Option**:
   * **Latest Donghua**: Fetch the list of recently released episodes.
   * **Popular Today**: Show what's currently trending.
   * **Search Donghua**: Query specific titles.
3. **Select Episode**: Pick the episode you want to watch.
4. **Select Stream Server**: Choose your preferred video host mirror.
5. **Select Action**:
   * **Play with MPV**: Launch the media player directly.
   * **View URL**: Print the resolved direct stream link.

---

## 🏗️ Project Architecture

```
DaoStream/
├── main.py                    # Main CLI interactive loop & user menus
├── requirements.txt           # Python library dependencies
├── LICENSE                    # MIT License
├── flake.nix                  # Nix Flake environment definition
├── sources/                   # Scraper sources directory
│   ├── __init__.py            # Source registration
│   ├── base.py                # Abstract BaseSource class
│   ├── wordpress_theme.py     # Shared logic for WordPress-themed sites
│   ├── anichin.py             # Anichin scraper source
│   ├── animexin.py            # AnimeXin scraper source
│   └── donghuafun.py          # Donghua Fun scraper source
└── utils/                     # Resolver and player helpers
    ├── __init__.py
    └── resolver.py            # Resolves and decrypts host URLs & launches MPV
```

---

## 🧩 Adding a New Source

Adding a new website scraper is simple due to `DaoStream`'s modular design:

1. **Create the Scraper File**:
   Create a new file under `sources/` (e.g., `sources/mysource.py`) inheriting from `BaseSource`:
   ```python
   from .base import BaseSource
   
   class MyCustomSource(BaseSource):
       @property
       def name(self) -> str:
           return "My Custom Source"
           
       @property
       def base_url(self) -> str:
           return "https://mycustomsource.com"
           
       # Implement abstract methods: get_latest(), get_popular(), search(), get_episodes(), get_servers()
   ```

2. **Register the Source**:
   Import and add your class instance inside `sources/get_sources()` in [sources/__init__.py](sources/__init__.py):
   ```python
   from .mysource import MyCustomSource
   
   def get_sources():
       return [
           # ...
           MyCustomSource()
       ]
   ```

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
