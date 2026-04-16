"""CLI entry-point shim. Keeps `python main.py` working."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))
from reasoner.main import main

if __name__ == "__main__":
    main()
