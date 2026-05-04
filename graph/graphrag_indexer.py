"""
Converts DOCX files from graph/graphrag/data_untouched/ to TXT in graph/graphrag/input/.
Run with: python -m graph.graphrag_indexer
"""
import subprocess
import sys
from pathlib import Path

from docx import Document

GRAPHRAG_ROOT = Path(__file__).parent / "graphrag"
DATA_DIR = GRAPHRAG_ROOT / "data_untouched"
INPUT_DIR = GRAPHRAG_ROOT / "input"


def _docx_to_text(path: Path) -> str:
    doc = Document(path)
    parts: list[str] = []

    # Paragraphs and tables are interleaved in doc.element.body — iterate in order
    from docx.oxml.ns import qn
    for child in doc.element.body:
        tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
        if tag == "p":
            text = "".join(node.text or "" for node in child.iter(qn("w:t"))).strip()
            if text:
                parts.append(text)
        elif tag == "tbl":
            for row in child.iter(qn("w:tr")):
                cells = [
                    "".join(node.text or "" for node in cell.iter(qn("w:t"))).strip()
                    for cell in row.iter(qn("w:tc"))
                ]
                row_text = " | ".join(c for c in cells if c)
                if row_text:
                    parts.append(row_text)

    return "\n".join(parts)


def convert_all() -> int:
    INPUT_DIR.mkdir(exist_ok=True)
    converted = 0
    for docx_file in DATA_DIR.rglob("*.docx"):
        txt_path = INPUT_DIR / (docx_file.stem + ".txt")
        try:
            text = _docx_to_text(docx_file)
            txt_path.write_text(text, encoding="utf-8")
            print(f"  ✓ {docx_file.name} → {txt_path.name}")
            converted += 1
        except Exception as e:
            print(f"  ✗ {docx_file.name}: {e}", file=sys.stderr)
    return converted


def run_index():
    print("Running graphrag index pipeline...")
    result = subprocess.run(
        [sys.executable, "-m", "graphrag", "index", "--root", str(GRAPHRAG_ROOT)],
        check=True,
    )
    return result.returncode


if __name__ == "__main__":
    print(f"Converting DOCX files from {DATA_DIR}...\n")
    n = convert_all()
    print(f"\nConverted {n} file(s).\n")
    if n > 0:
        run_index()
