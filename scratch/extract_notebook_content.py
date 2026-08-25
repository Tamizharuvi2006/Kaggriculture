"""Extract all text and markdown findings from what-actually-wins-on-the-kaggriculture-ladder.ipynb
"""

import json
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

NOTEBOOK_PATH = r"D:\Kaggriculture\data\notebooks\what-actually-wins-on-the-kaggriculture-ladder.ipynb"

def main():
    with open(NOTEBOOK_PATH, "r", encoding="utf-8") as f:
        nb = json.load(f)

    cells = nb.get("cells", [])
    print(f"Reading {len(cells)} cells from notebook...\n")

    for idx, cell in enumerate(cells):
        cell_type = cell.get("cell_type", "")
        source = "".join(cell.get("source", []))
        
        if cell_type == "markdown":
            print(f"\n--- CELL {idx} [MARKDOWN] ---")
            print(source)
        elif cell_type == "code":
            # Print outputs if present
            outputs = cell.get("outputs", [])
            for out in outputs:
                if out.get("output_type") == "stream":
                    text = "".join(out.get("text", []))
                    print(f"--- CELL {idx} [OUTPUT STREAM] ---")
                    print(text[:1500])  # Print first 1500 chars of output
                elif out.get("output_type") == "execute_result":
                    data = out.get("data", {})
                    text_plain = "".join(data.get("text/plain", []))
                    if text_plain:
                        print(f"--- CELL {idx} [OUTPUT PLAIN] ---")
                        print(text_plain[:1500])

if __name__ == "__main__":
    main()
