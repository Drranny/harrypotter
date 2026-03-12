# Chunking
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

# Embedding
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# Vector DB
FAISS_INDEX_PATH = "./vector_db/faiss.index"

# Data paths (text-track first)
TEXT_RAW_DIR = "data/text/raw"
TEXT_PROCESSED_DIR = "data/text/processed"
TEXT_EVAL_DIR = "data/text/eval"

# Backward-compatible legacy paths
LEGACY_RAW_DIR = "data/raw"
LEGACY_PROCESSED_DIR = "data/processed"
LEGACY_EVAL_DIR = "data/eval"
