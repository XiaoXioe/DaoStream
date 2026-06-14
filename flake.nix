{
  description = "DaoStream - A modular CLI scraper and stream resolver for Anime & Donghua";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };
      in
      {
        devShells.default = pkgs.mkShell {
          buildInputs = with pkgs; [
            python3
            python3Packages.pip
            python3Packages.virtualenv
            mpv
          ];

          shellHook = ''
            echo "🌌 Welcome to the DaoStream Nix devShell!"
            if [ ! -d ".venv" ]; then
              echo "Initializing virtual environment (.venv)..."
              python3 -m venv .venv
            fi
            source .venv/bin/activate
            echo "Verifying Python dependencies..."
            pip install --quiet -r requirements.txt
            echo "----------------------------------------------------"
            echo "DaoStream is ready! Run 'python3 main.py' to start."
            echo "----------------------------------------------------"
          '';
        };
      }
    );
}
