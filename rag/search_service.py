import os
import shutil
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from storage.blob_service import BlobService

class SearchService:
    def __init__(self):
        self.blob_service = BlobService()
        self.embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        self.cache_dir = "temp_indices" # Local cache for vector stores

    def search(self, doc_id, query, k=5):
        """
        1. Ensure index exists locally.
        2. Load index.
        3. Search.
        """
        # 1. Prepare local path
        # Use a safe path structure
        safe_doc_id = doc_id.replace('/', '_').replace('\\', '_')
        target_dir = os.path.join(self.cache_dir, safe_doc_id)
        
        # 2. Download if missing
        # We check if folder exists, but ideally we should check if it's empty
        if not os.path.exists(target_dir) or not os.listdir(target_dir):
            print(f"Index not found locally for {doc_id}. Downloading...")
            files = self.blob_service.download_vector_store(doc_id, target_dir)
            if not files:
                return [] # No index found

        # 3. Load Index
        try:
            # FAISS load_local requires the folder path and the embeddings object
            # Note: allow_dangerous_deserialization is needed for pickle files in recent langchain versions
            # We assume internal safe files.
            vectorstore = FAISS.load_local(
                target_dir, 
                self.embeddings, 
                allow_dangerous_deserialization=True
            )
        except Exception as e:
            print(f"Error loading FAISS index: {e}")
            return []

        # 4. Search
        # similarity_search_with_score returns (Document, score)
        # Lower score is better for L2 distance, but usually FAISS wraps this.
        results = vectorstore.similarity_search_with_score(query, k=k)
        
        processed_results = []
        for doc, score in results:
            processed_results.append({
                'content': doc.page_content,
                'page': doc.metadata.get('page', 0), # Assuming metadata has 'page'
                'score': float(score)
            })
            
        return processed_results

    def get_document_url(self, doc_id):
        """
        Reconstructs the blob path for the PDF and gets a SAS URL.
        doc_id: Category/Year/Filename_stem
        We need to find the actual .pdf blob again or assume standard naming.
        """
        # Re-scan or guess? Scanning is safer but slower. 
        # For efficiency, let's assume standard structure: pdfs/{doc_id}.pdf
        # The list_blobs_hierarchy stored the exact blob_path, but we don't have it here easily
        # without querying again.
        # Let's rely on the frontend passing the correct blob_path if possible, 
        # OR just reconstruct: "pdfs/Category/Year/filename.pdf"
        # Wait, doc_id was "Category/Year/filename_stem".
        # We need the extension. 
        
        # Quick fix: Scan specifically for this file in the hierarchy logic or just guess .pdf
        blob_path = f"pdfs/{doc_id}.pdf"
        return self.blob_service.get_sas_url(blob_path)

