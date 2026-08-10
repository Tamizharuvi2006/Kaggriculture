"""Parse what-actually-wins-on-the-kaggriculture-ladder.ipynb markdown and code cells.
"""

import json
import os
import sys

# Set encoding for Windows console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

NOTEBOOK_PATH = r"D:\kagriulture\Kaggriculture\what-actually-wins-on-the-kaggriculture-ladder.ipynb"

def main():
    if not os.path.exists(NOTEBOOK_PATH):
        print(f"Notebook file not found: {NOTEBOOK_PATH}")
        return

    with open(NOTEBOOK_PATH, "r", encoding="utf-8") as f:
        nb = json.load(f)

    cells = nb.get("cells", [])
    print(f"Total cells in notebook: {len(cells)}")

    markdown_headers = []
    for idx, cell in enumerate(cells):
        cell_type = cell.get("cell_type", "")
        source = "".join(cell.get("source", []))
        
        if cell_type == "markdown":
            lines = [line.strip() for line in source.split("\n") if line.strip().startswith("#")]
            if lines:
                markdown_headers.append(f"Cell {idx} [Markdown]: " + " | ".join(lines))
        elif cell_type == "code":
            if "Kaggle" in source or "meta" in source.lower() or "win" in source.lower() or "strategy" in source.lower():
                # Extract first 3 lines of code
                first_lines = source.split("\n")[:3]
                markdown_headers.append(f"Cell {idx} [Code]: " + " ".join(first_lines))

    print("\n--- NOTEBOOK TABLE OF CONTENTS / HEADERS ---")
    for header in markdown_headers[:40]:
        print(header)

if __name__ == "__main__":
    main()
