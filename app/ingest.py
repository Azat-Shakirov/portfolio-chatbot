"""
Run this script once after editing data/about_me.txt to rebuild the ChromaDB index.
Usage: python app/ingest.py
Railway: runs automatically on first deploy via start.sh if chroma_db is empty.
"""
import shutil
from pathlib import Path
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

DATA_PATH = Path(__file__).parent.parent / "data" / "about_me.txt"
CHROMA_PATH = Path(__file__).parent.parent / "chroma_db"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
CHUNK_SIZE = 1500   # ~400 words
CHUNK_OVERLAP = 200  # ~50 words


def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def chunk_text(text: str) -> list[str]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
    )
    return splitter.split_text(text)


def get_embeddings() -> HuggingFaceEmbeddings:
    return HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)


def build_index(chunks: list[str], embeddings: HuggingFaceEmbeddings) -> None:
    # Wipe existing index so re-runs don't accumulate stale chunks
    if CHROMA_PATH.exists():
        shutil.rmtree(CHROMA_PATH)
    Chroma.from_texts(
        texts=chunks,
        embedding=embeddings,
        persist_directory=str(CHROMA_PATH),
    )


def main() -> None:
    print(f"Loading {DATA_PATH}...")
    text = load_text(DATA_PATH)

    print("Chunking...")
    chunks = chunk_text(text)
    print(f"  → {len(chunks)} chunks created")

    print("Loading embedding model (first run downloads ~90 MB)...")
    embeddings = get_embeddings()

    print(f"Building ChromaDB index at {CHROMA_PATH}...")
    build_index(chunks, embeddings)
    print("Done. Re-run this script any time you update about_me.txt.")


if __name__ == "__main__":
    main()
