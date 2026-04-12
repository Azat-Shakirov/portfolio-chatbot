# app/rag.py
from pathlib import Path
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from anthropic import AsyncAnthropic
from app.config import settings
from app.prompts import (
    SYSTEM_PROMPT_CORE,
    PERSONALITY_MODIFIERS,
    CONTEXT_TEMPLATE,
)

CHROMA_PATH = Path(__file__).parent.parent / "chroma_db"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
CLAUDE_MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS = 1024

# Module-level singletons — loaded once on first use
_embeddings: HuggingFaceEmbeddings | None = None
_vectorstore: Chroma | None = None


def _get_vectorstore() -> Chroma:
    global _embeddings, _vectorstore
    if _vectorstore is None:
        _embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
        _vectorstore = Chroma(
            persist_directory=str(CHROMA_PATH),
            embedding_function=_embeddings,
        )
    return _vectorstore


def warmup() -> None:
    """Pre-load the embedding model and vectorstore at startup."""
    _get_vectorstore()


def retrieve_chunks(question: str, k: int = 3) -> list[str]:
    """Return the top-k most semantically similar chunks to the question."""
    vs = _get_vectorstore()
    docs = vs.similarity_search(question, k=k)
    return [doc.page_content for doc in docs]


def build_prompt(question: str, chunks: list[str], personality: str) -> tuple[str, str]:
    """
    Assemble the system prompt and user message for a Claude request.
    Returns (system_prompt, user_message).
    """
    context_block = CONTEXT_TEMPLATE.format(chunks="\n\n---\n\n".join(chunks))
    modifier = PERSONALITY_MODIFIERS.get(personality, PERSONALITY_MODIFIERS["casual"])
    system = f"{SYSTEM_PROMPT_CORE}\n\n{modifier}\n\n{context_block}"
    return system, question


async def stream_response(question: str, personality: str):
    """
    Async generator. Yields (text_chunk, None) for each streamed token,
    then yields ("", total_token_count) as the final item.
    On error, yields an error message chunk then ("", 0).
    """
    chunks = retrieve_chunks(question)
    system, user_message = build_prompt(question, chunks, personality)

    client = AsyncAnthropic(api_key=settings.claude_api_key)

    try:
        async with client.messages.stream(
            model=CLAUDE_MODEL,
            max_tokens=MAX_TOKENS,
            system=system,
            messages=[{"role": "user", "content": user_message}],
        ) as stream:
            async for text in stream.text_stream:
                yield text, None
            final = await stream.get_final_message()
            total_tokens = final.usage.input_tokens + final.usage.output_tokens

        yield "", total_tokens
    except Exception:
        yield "Something went wrong on my end. Please try again.", None
        yield "", 0
