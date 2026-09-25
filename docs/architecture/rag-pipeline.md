# Rag pipeline

Documents -> Parsing -> Chunking -> Embedding -> ChromaDB -> Retrieval -> Context -> Gemini LLM -> Answer + Citation.
Insufficient-information behavior is required; answers must be grounded in retrieved context. NOT implemented in SETUP-001.
