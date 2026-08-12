from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.services import AnalysisService


def main() -> None:
    parser = argparse.ArgumentParser(description="Import CSV/JSON jobs into SQLite")
    parser.add_argument("--input", required=True)
    parser.add_argument("--db", default="data/app.db")
    args = parser.parse_args()
    source = Path(args.input)
    service = AnalysisService(db_path=args.db)
    count, errors = service.import_jobs(source.name, source.read_bytes())
    print(f"imported_or_updated={count} errors={len(errors)}")
    for error in errors:
        print(error)
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
