import chromadb
from typing import List, Dict, Any
import uuid
from .database import TradeDatabase
from .logger import get_logger

logger = get_logger(__name__)

class RAGSystem:
    def __init__(self, persist_directory="./db_chroma"):
        self.client = chromadb.PersistentClient(path=persist_directory)
        self.db = TradeDatabase()
        
        # Collection 1: Setups (History - Vector Part)
        self.setup_collection = self.client.get_or_create_collection(
            name="sentinel_x_proven_setups",
            metadata={"hnsw:space": "cosine"}
        )
        
        # Collection 2: Concepts (Knowledge Base)
        self.concept_collection = self.client.get_or_create_collection(
            name="trading_concepts",
            metadata={"hnsw:space": "cosine"}
        )

    # --- History / Setups (Hybrid: Vector + SQLite) ---
    def query_similar_history(self, data: Any, n_results=3) -> List[Dict]:
        """Find similar past trades and return full details from SQLite."""
        # Vector: MA Diff, RSI, Volatility (ATR-like or Volume)
        ma_diff = (data.ma_fast - data.ma_slow) if (data.ma_fast and data.ma_slow) else 0.0
        query_vector = [ma_diff, data.rsi or 50.0, float(data.tick_volume)]
        
        try:
            results = self.setup_collection.query(
                query_embeddings=[query_vector],
                n_results=n_results
            )
            
            if not results['ids'] or not results['ids'][0]:
                return []
                
            # Get IDs found by Vector Search
            found_ids = results['ids'][0]
            
            # Fetch full details from SQLite
            full_details = self.db.get_trades_by_ids(found_ids)
            return full_details
            
        except Exception as e:
            logger.error(f"RAG query failed: {e}", extra={"context": {"error": str(e)}})
            return []

        ma_diff = (mc.get('ma_fast', 0) - mc.get('ma_slow', 0))
        vector = [ma_diff, mc.get('rsi', 50), float(mc.get('tick_volume', 0))]
        
        self.setup_collection.add(
            embeddings=[vector],
            metadatas=[{"outcome": trade_data['outcome']}],
            ids=[trade_data['id']]
        )

    # --- Knowledge / Concepts ---
    def add_concept(self, text: str, source: str = "manual"):
        """Ingest a strategy rule or concept text."""
        self.concept_collection.add(
            documents=[text],
            metadatas=[{"source": source, "type": "concept"}],
            ids=[str(uuid.uuid4())]
        )

    def ingest_knowledge_base(self, directory: str) -> str:
        """Scan folder and ingest text files (TXT, MD, PDF) into Knowledge Base."""
        import os
        import hashlib
        try:
            from pypdf import PdfReader
        except ImportError:
            return "Error: pypdf not installed. Please pip install pypdf"
        
        if not os.path.exists(directory):
            return f"Directory not found: {directory}"
            
        ingested_count = 0
        total_files = 0
        errors = []
        
        for filename in os.listdir(directory):
            ext = filename.lower()
            if ext.endswith(('.txt', '.md', '.pdf')):
                total_files += 1
                path = os.path.join(directory, filename)
                try:
                    text = ""
                    
                    # --- Text Handler ---
                    if ext.endswith(('.txt', '.md')):
                        with open(path, 'r', encoding='utf-8') as f:
                            text = f.read()
                            
                    # --- PDF Handler ---
                    elif ext.endswith('.pdf'):
                        reader = PdfReader(path)
                        for page in reader.pages:
                            page_text = page.extract_text()
                            if page_text:
                                text += page_text + "\n"
                        
                    if not text.strip(): continue
                    
                    # Deduplication: Use Hash of text as ID
                    text_hash = hashlib.md5(text.encode('utf-8')).hexdigest()
                    
                    # check if exists (optional, but add overwrites so it's fine)
                    self.concept_collection.add(
                        documents=[text],
                        metadatas=[{"source": filename, "type": "concept"}],
                        ids=[text_hash]
                    )
                    ingested_count += 1
                except Exception as e:
                    errors.append(f"{filename}: {str(e)}")
        
        result = f"Ingested {ingested_count}/{total_files} files."
        if errors:
            result += f" Errors: {'; '.join(errors)}"
        return result
