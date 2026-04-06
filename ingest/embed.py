from sentence_transformers import SentenceTransformer
from config import EMBEDDING_MODEL

model = SentenceTransformer(EMBEDDING_MODEL, trust_remote_code=True)

def embed_chunks(chunks: list[str]):
    return model.encode(chunks, show_progress_bar=True)
