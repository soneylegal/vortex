"""
Knowledge Base Ingestion Script.

Loads Markdown files from data/knowledge_base/, splits them into chunks,
and indexes them into the local ChromaDB vector store.

Usage:
    python scripts/ingest_data.py           # Append to existing collection
    python scripts/ingest_data.py --clear   # Wipe collection and re-ingest
"""

import argparse
import glob
import sys

from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.app.services.vector_store import get_vector_store


def main():
    parser = argparse.ArgumentParser(description="Ingest knowledge base into ChromaDB")
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear existing ChromaDB collection before ingesting.",
    )
    args = parser.parse_args()

    kb_path = "data/knowledge_base"

    # Discover markdown files
    md_files = sorted(glob.glob(f"{kb_path}/**/*.md", recursive=True))
    if not md_files:
        print(f"✗ No markdown files found in {kb_path}/")
        print("  Add .md files to the knowledge base directory and re-run.")
        sys.exit(1)

    print(f"Found {len(md_files)} file(s):")
    for f in md_files:
        print(f"  • {f}")

    # Load documents
    docs = []
    for file_path in md_files:
        loader = TextLoader(file_path, encoding="utf-8")
        docs.extend(loader.load())

    # Split into chunks
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        separators=["\n## ", "\n### ", "\n---", "\n\n", "\n", " "],
    )
    splits = text_splitter.split_documents(docs)
    print(f"\nSplit into {len(splits)} chunks (chunk_size=1000, overlap=200)")

    # Initialize vector store
    vs = get_vector_store()

    if args.clear:
        print("Clearing existing collection...")
        vs.clear()

    # Ingest
    print("Ingesting into ChromaDB...")
    vs.add_documents(splits)

    # Validate
    total = vs.document_count()
    print(f"\n✓ Ingestion complete. Total documents in collection: {total}")


if __name__ == "__main__":
    main()
