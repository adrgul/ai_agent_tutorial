#!/usr/bin/env python
"""Script to initialize or rebuild the knowledge base."""

import argparse
import shutil
from pathlib import Path

from app.core.dependencies import initialize_knowledge_base, get_settings


def main():
    """Initialize knowledge base."""
    parser = argparse.ArgumentParser(
        description="Initialize FAISS knowledge base from KB articles"
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Delete existing index and rebuild from scratch",
    )

    args = parser.parse_args()

    settings = get_settings()
    index_path = Path(settings.faiss_index_path)

    if args.rebuild and index_path.exists():
        print(f"Deleting existing index at {index_path}")
        shutil.rmtree(index_path)

    print("Initializing knowledge base...")
    initialize_knowledge_base()
    print("✓ Knowledge base initialized successfully")


if __name__ == "__main__":
    main()
