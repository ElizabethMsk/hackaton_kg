import chromadb
from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Dict

class SemanticSearch:
    def __init__(self, db_path: str = "./vector_db", collection_name: str = "articles"):
        self.model = SentenceTransformer(
            "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        )
        self.client = chromadb.PersistentClient(path=db_path)
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )
    
    def add_documents(self, texts: List[str], metadatas: List[Dict] = None):
        """Добавить документы в базу"""
        if metadatas is None:
            metadatas = [{} for _ in texts]
        
        embeddings = self.model.encode(texts, show_progress_bar=True)
        
        self.collection.add(
            ids=[f"doc_{i}" for i in range(len(texts))],
            embeddings=embeddings.tolist(),
            documents=texts,
            metadatas=metadatas
        )
        print(f"✅ Добавлено {len(texts)} документов")
    
    def search(self, query: str, n_results: int = 5) -> List[Dict]:
        """Семантический поиск"""
        query_embedding = self.model.encode([query])[0]
        
        results = self.collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=n_results,
            include=["documents", "metadatas", "distances"]
        )
        
        output = []
        for doc, dist, meta in zip(
            results['documents'][0],
            results['distances'][0],
            results['metadatas'][0]
        ):
            output.append({
                "document": doc,
                "distance": dist,
                "similarity": 1 - dist,
                "metadata": meta
            })
        
        return output


if __name__ == "__main__":
    search = SemanticSearch()
    
    query = "термообработка сплавов"
    print(f"Поиск: '{query}'\n")
    
    results = search.search(query, n_results=3)
    
    for i, r in enumerate(results, 1):
        print(f"{i}. Похожесть: {r['similarity']:.2%}")
        print(f"   {r['document'][:150]}...")
        print()