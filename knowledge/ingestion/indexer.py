import os
import glob
from typing import List, Dict, Any

class ObsidianIndexer:
    """
    Offline indexing pipeline to chunk Markdown files from the Obsidian Vault,
    embed them, and upsert the documents into ChromaDB.
    """
    def __init__(self, vault_dir: str = "knowledge/obsidian_vault", persist_dir: str = "vector_db"):
        self.vault_dir = vault_dir
        self.persist_dir = persist_dir
        self.collection_name = "eops_knowledge"
        
    def scan_vault(self) -> List[Dict[str, Any]]:
        """
        Scans obsidian_vault recursively for Markdown (.md) documents.
        """
        search_pattern = os.path.join(self.vault_dir, "**", "*.md")
        files = glob.glob(search_pattern, recursive=True)
        
        documents = []
        for file_path in files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                
                # Extract relative path to use as title/source
                rel_path = os.path.relpath(file_path, self.vault_dir)
                title = os.path.splitext(rel_path)[0]
                
                documents.append({
                    "title": title,
                    "content": content,
                    "source": rel_path
                })
            except Exception as e:
                print(f"[Indexer] Error reading {file_path}: {e}")
                
        return documents

    def chunk_text(self, text: str, chunk_size: int = 500, chunk_overlap: int = 50) -> List[str]:
        """
        Simple text chunker based on character length and overlap.
        """
        chunks = []
        words = text.split()
        current_chunk = []
        current_length = 0
        
        for word in words:
            current_chunk.append(word)
            current_length += len(word) + 1  # Add 1 for the space
            
            if current_length >= chunk_size:
                chunks.append(" ".join(current_chunk))
                # basic overlap logic (keep last 5 words for simple overlap)
                current_chunk = current_chunk[-5:] if len(current_chunk) > 5 else []
                current_length = sum(len(w) + 1 for w in current_chunk)
                
        if current_chunk:
            chunks.append(" ".join(current_chunk))
            
        return chunks

    def run_ingestion(self):
        """
        Executes scan -> chunk -> embed -> write to ChromaDB.
        """
        print(f"[Indexer] Starting ingestion from vault: {self.vault_dir}")
        raw_docs = self.scan_vault()
        
        if not raw_docs:
            print("[Indexer] Obsidian vault is empty. No files indexed.")
            return

        chunks_to_index = []
        metadatas = []
        ids = []
        
        chunk_counter = 0
        for doc in raw_docs:
            chunks = self.chunk_text(doc["content"])
            print(f"[Indexer] Chunked '{doc['title']}' into {len(chunks)} pieces.")
            
            for i, chunk in enumerate(chunks):
                chunks_to_index.append(chunk)
                metadatas.append({
                    "title": doc["title"],
                    "source": doc["source"],
                    "chunk_id": i
                })
                ids.append(f"{doc['title']}_chunk_{i}")
                chunk_counter += 1

        # Connect to ChromaDB and insert
        try:
            import chromadb
            client = chromadb.PersistentClient(path=self.persist_dir)
            collection = client.get_or_create_collection(self.collection_name)
            
            # Upsert
            collection.upsert(
                documents=chunks_to_index,
                metadatas=metadatas,
                ids=ids
            )
            print(f"[Indexer] Successfully ingested {chunk_counter} chunks into ChromaDB.")
        except ImportError:
            print("[Indexer] chromadb package is not installed. Indexing skipped (sandbox simulation mode).")
            print(f"[Indexer] Simulated indexing of {chunk_counter} chunks completed.")

if __name__ == "__main__":
    # Create the test directories if running standalone
    os.makedirs("knowledge/obsidian_vault/Services", exist_ok=True)
    os.makedirs("knowledge/obsidian_vault/Runbooks", exist_ok=True)
    
    indexer = ObsidianIndexer()
    indexer.run_ingestion()
