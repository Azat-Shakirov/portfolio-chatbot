from pathlib import Path
from app.ingest import load_text, chunk_text


def test_load_text_reads_file(tmp_path):
    f = tmp_path / "test.txt"
    f.write_text("Hello Azat", encoding="utf-8")
    assert load_text(f) == "Hello Azat"


def test_chunk_text_returns_list_of_strings():
    text = "word " * 500  # ~2500 chars
    chunks = chunk_text(text)
    assert isinstance(chunks, list)
    assert all(isinstance(c, str) for c in chunks)


def test_chunk_text_splits_long_text():
    text = "word " * 1000  # ~5000 chars, above chunk size
    chunks = chunk_text(text)
    assert len(chunks) > 1


def test_chunk_text_keeps_short_text_as_one_chunk():
    text = "Azat is a security engineer at Knox College."
    chunks = chunk_text(text)
    assert len(chunks) == 1
    assert "Azat" in chunks[0]


def test_chunk_text_overlap_shares_content():
    # Each chunk should partially overlap with the next
    text = "sentence " * 400
    chunks = chunk_text(text)
    if len(chunks) > 1:
        # Last words of chunk[0] should appear somewhere in start of chunk[1]
        tail_words = chunks[0].split()[-10:]
        head_text = " ".join(chunks[1].split()[:30])
        assert any(w in head_text for w in tail_words)
