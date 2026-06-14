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
        pythonEnv = pkgs.python3.withPackages (ps: with ps; [
          pip
          virtualenv
          curl-cffi
          cryptography
          browserforge
        ]);
      in
      {
        devShells.default = pkgs.mkShell {
          buildInputs = [
            pythonEnv
            pkgs.mpv
          ];

          shellHook = ''
            echo "🌌 Welcome to the DaoStream Nix devShell!"
            if [ -f "requirements.txt" ]; then
              if [ ! -d ".venv" ]; then
                echo "Initializing virtual environment (.venv with system site packages)..."
                python3 -m venv --system-site-packages .venv
              else
                # Ensure system-site-packages is enabled if .venv already exists
                if [ -f ".venv/pyvenv.cfg" ]; then
                  sed -i 's/include-system-site-packages = false/include-system-site-packages = true/g' .venv/pyvenv.cfg
                fi
              fi
              source .venv/bin/activate
              echo "Verifying Python dependencies..."
              pip install --quiet -r requirements.txt
              echo "----------------------------------------------------"
              echo "DaoStream is ready! Run 'python3 main.py' to start."
              echo "----------------------------------------------------"
            else
              echo "----------------------------------------------------"
              echo "Warning: requirements.txt not found in the current directory."
              echo "Please clone the repo first and run 'nix develop' inside it:"
              echo "  git clone https://github.com/XiaoXioe/DaoStream.git"
              echo "  cd DaoStream"
              echo "  nix develop"
              echo "----------------------------------------------------"
            fi
          '';
        };
      }
    );
}
