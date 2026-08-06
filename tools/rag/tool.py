import os
from typing import List, Dict, Any, Optional

class KnowledgeTool:
    """
    Tool to query ChromaDB for architectural documentation, incident runbooks, and API specs.
    """
    def __init__(self, persist_directory: str = "vector_db", collection_name: str = "eops_knowledge"):
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        self.client = None
        self.collection = None
        self._initialize_chroma()

    def _initialize_chroma(self):
        """
        Initializes ChromaDB client.
        """
        # We handle imports dynamically or gracefully catch failures in case ChromaDB is not yet installed.
        try:
            import chromadb
            # Initialize local persistent client
            self.client = chromadb.PersistentClient(path=self.persist_directory)
            self.collection = self.client.get_or_create_collection(self.collection_name)
        except ImportError:
            self.client = None
            self.collection = None

    def query_docs(self, query: str, limit: int = 3) -> List[Dict[str, Any]]:
        """
        Queries ChromaDB vector database. If ChromaDB isn't fully configured or lacks data,
        it yields contextual fallback information for testing.
        """
        if not self.collection or not self.client:
            # Fallback mock RAG context based on typical incidents
            return [
                {
                    "title": "Services/Checkout API Specification",
                    "content": "Checkout service uses Redis cache to store item details and pricing to reduceDB pressure. Redis host: redis.internal.net, port: 6379. Default connection timeout: 1000ms. If Redis is unavailable, the service is configured to fallback to the PostgreSQL main DB, which might lead to performance degradation or thread pooling saturation.",
                    "source": "knowledge/obsidian_vault/Services/checkout_api.md"
                },
                {
                    "title": "Runbooks/Redis Cache Latency Issues",
                    "content": "Symptom: High API latency or HTTP 500 errors on checkout. Action: Verify Redis CPU load and connection pools. If Redis connection errors occur, check if the latest deployment changed connection timeouts or network policies.",
                    "source": "knowledge/obsidian_vault/Runbooks/redis_troubleshooting.md"
                }
            ]

        try:
            # Real ChromaDB query logic
            # This assumes we are using standard langchain/chromadb flow with embeddings.
            # For pure chromadb, we'd supply query embeddings or use default embedding functions.
            results = self.collection.query(
                query_texts=[query],
                n_results=limit
            )
            
            documents = []
            if results and 'documents' in results and results['documents']:
                for i in range(len(results['documents'][0])):
                    doc_content = results['documents'][0][i]
                    metadata = results['metadatas'][0][i] if 'metadatas' in results and results['metadatas'] else {}
                    documents.append({
                        "title": metadata.get("title", "Unknown Doc"),
                        "content": doc_content,
                        "source": metadata.get("source", "ChromaDB")
                    })
            return documents
        except Exception as e:
            # Graceful fallback on query failure
            return [
                {
                    "title": "Error Querying ChromaDB",
                    "content": f"Failed to query database: {str(e)}",
                    "source": "System Error"
                }
            ]
        
    def add_documents(self, texts: List[str], metadatas: List[Dict[str, Any]], ids: List[str]):
        """
        Helper method to insert chunks into ChromaDB.
        """
        if self.collection:
            self.collection.add(
                documents=texts,
                metadatas=metadatas,
                ids=ids
            )
