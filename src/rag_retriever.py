import os
import json
from pathlib import Path
from typing import List, Dict, Tuple, Any
import re
from anthropic import Anthropic

# Commented out: Real embeddings (reserved for production with sentence-transformers)
# from sentence_transformers import SentenceTransformer
# embedder = SentenceTransformer('all-MiniLM-L6-v2')

client = Anthropic()
embedder = None  # Using simple keyword matching instead of embeddings

PII_PATTERNS = {
    "SSN": r"\b\d{3}-\d{2}-\d{4}\b",
    "SALARY": r"\$[\d,]+(?:\.\d{2})?(?:\s*(?:per\s+year|annually|/year|k))?",
    "EMAIL": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
}


class RAGRetriever:
    def __init__(self, kb_path: str = "data/knowledge_base"):
        self.kb_path = kb_path
        self.documents = []
        self.embeddings = []
        self.load_documents()

    def load_documents(self):
        """Load all markdown files from knowledge base"""
        kb_dir = Path(self.kb_path)
        if not kb_dir.exists():
            print(f"Warning: Knowledge base directory {self.kb_path} not found")
            return

        for md_file in kb_dir.glob("*.md"):
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()
                self.documents.append({
                    "filename": md_file.stem,
                    "content": content,
                    "chunks": self._chunk_document(content)
                })

        # Create embeddings for all chunks
        if embedder:
            self._create_embeddings()

    def _chunk_document(self, content: str, chunk_size: int = 500) -> List[str]:
        """Split document into chunks"""
        chunks = []
        sentences = re.split(r'(?<=[.!?])\s+', content)
        current_chunk = ""

        for sentence in sentences:
            if len(current_chunk) + len(sentence) < chunk_size:
                current_chunk += sentence + " "
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence + " "

        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

    def _create_embeddings(self):
        """Create embeddings (commented out - using keyword matching instead)"""
        # Embeddings with sentence-transformers reserved for production
        # all_chunks = []
        # for doc in self.documents:
        #     all_chunks.extend(doc["chunks"])
        # if all_chunks and embedder:
        #     self.embeddings = embedder.encode(all_chunks, convert_to_tensor=True)
        pass

    def _keyword_similarity(self, query: str, chunk: str) -> float:
        """Simple keyword-based similarity (fallback for no embeddings)"""
        query_words = set(query.lower().split())
        chunk_words = set(chunk.lower().split())

        # Jaccard similarity
        if not query_words or not chunk_words:
            return 0.0

        intersection = len(query_words & chunk_words)
        union = len(query_words | chunk_words)

        return intersection / union if union > 0 else 0.0

    def retrieve(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Retrieve relevant chunks using keyword matching (embeddings commented out)"""
        if not self.documents:
            return []

        try:
            all_chunks = []
            chunk_to_doc = {}

            for doc in self.documents:
                for chunk in doc["chunks"]:
                    all_chunks.append(chunk)
                    chunk_to_doc[len(all_chunks) - 1] = doc["filename"]

            if not all_chunks:
                return []

            # Calculate similarity scores using keyword matching
            # (In production, replace with embedder.encode() and embedder.similarity())
            similarities = [self._keyword_similarity(query, chunk) for chunk in all_chunks]

            # Get top-k
            top_indices = sorted(range(len(similarities)), key=lambda i: similarities[i], reverse=True)[:top_k]

            results = []
            for idx in top_indices:
                if similarities[idx] > 0.1:  # Only include if some keyword overlap
                    results.append({
                        "content": all_chunks[idx],
                        "document": chunk_to_doc[idx],
                        "confidence": float(round(similarities[idx], 3))
                    })

            return results

        except Exception as e:
            print(f"Error in retrieval: {e}")
            return []

    def extract_pii(self, text: str) -> List[Dict[str, str]]:
        """Extract PII from text"""
        found_pii = []

        for pii_type, pattern in PII_PATTERNS.items():
            matches = re.finditer(pattern, text)
            for match in matches:
                found_pii.append({
                    "type": pii_type,
                    "value": match.group(),
                    "position": (match.start(), match.end())
                })

        return found_pii

    def redact_pii(self, text: str, pii_list: List[Dict[str, str]]) -> str:
        """Redact PII from text"""
        redacted = text
        # Sort by position (reverse) to maintain indices
        for pii in sorted(pii_list, key=lambda x: x["position"][0], reverse=True):
            start, end = pii["position"]
            pii_type = pii["type"]
            redacted = redacted[:start] + f"[REDACTED-{pii_type}]" + redacted[end:]

        return redacted

    def validate_response(self, response: str, source_chunks: List[str]) -> Dict[str, Any]:
        """Validate response against source chunks"""

        # Check for PII in response
        pii_in_response = self.extract_pii(response)

        # Check for PII in sources
        pii_in_sources = []
        for chunk in source_chunks:
            pii_in_sources.extend(self.extract_pii(chunk))

        # If PII in response but not in sources, flag it (hallucination)
        flagged_pii = []
        for pii in pii_in_response:
            is_sourced = any(pii["value"] == src["value"] for src in pii_in_sources)
            if not is_sourced:
                flagged_pii.append(pii)

        # Redact all PII from response
        redacted_response = self.redact_pii(response, pii_in_response)

        return {
            "original_response": response,
            "redacted_response": redacted_response,
            "pii_found": pii_in_response,
            "pii_redacted": len(pii_in_response),
            "unsourced_pii": flagged_pii,
            "validation_score": max(0, 1.0 - len(flagged_pii) * 0.2)
        }


def generate_rag_response(query: str, retriever: RAGRetriever, system_prompt: str = "") -> Dict[str, Any]:
    """Generate response using RAG with Claude"""

    # Retrieve relevant chunks
    chunks = retriever.retrieve(query, top_k=3)
    source_chunks = [chunk["content"] for chunk in chunks]

    if not chunks:
        sources_text = "No relevant sources found."
    else:
        sources_text = "\n\n".join([f"Source: {c['document']}\nConfidence: {c['confidence']}\n{c['content']}"
                                    for c in chunks])

    # Build prompt
    full_prompt = f"""Based on the following sources, answer the user's question.
Be accurate and only cite information from the sources provided.
Do not make up information.

Sources:
{sources_text}

User Question: {query}

Please provide a helpful and accurate response."""

    # Generate response
    try:
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=500,
            messages=[
                {"role": "user", "content": full_prompt}
            ]
        )

        generated_response = response.content[0].text

        # Validate response
        validation = retriever.validate_response(generated_response, source_chunks)

        return {
            "query": query,
            "response": generated_response,
            "sources": chunks,
            "validation": validation,
            "is_safe": len(validation["unsourced_pii"]) == 0
        }

    except Exception as e:
        return {
            "query": query,
            "response": f"Error generating response: {str(e)}",
            "sources": chunks,
            "validation": {},
            "is_safe": False
        }


# Test/demo functions
if __name__ == "__main__":
    retriever = RAGRetriever()

    # Test retrieval
    query = "What is the PTO policy?"
    results = retriever.retrieve(query)
    print(f"Retrieved {len(results)} chunks for query: {query}")
    for r in results:
        print(f"  - {r['document']} (confidence: {r['confidence']})")
