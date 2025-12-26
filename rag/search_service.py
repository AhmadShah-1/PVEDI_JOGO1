import os
import shutil
from langchain_community.vectorstores import FAISS
from langchain_openai import AzureOpenAIEmbeddings
from storage.blob_service import BlobService

import re

class SearchService:
    def __init__(self):
        self.blob_service = BlobService()
        self.embeddings = AzureOpenAIEmbeddings(
            azure_deployment=os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT"),
            openai_api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            openai_api_version=os.getenv("AZURE_OPENAI_API_VERSION")
        )
        self.cache_dir = "temp_indices" # Local cache for vector stores

    def search(self, doc_id, query, k=5):
        """
        1. Ensure index exists locally.
        2. Load index.
        3. Search.
        """
        # ... (keep existing code up to loading) ...
        safe_doc_id = doc_id.replace('/', '_').replace('\\', '_')
        target_dir = os.path.join(self.cache_dir, safe_doc_id)
        
        if not os.path.exists(target_dir) or not os.listdir(target_dir):
            print(f"Index not found locally for {doc_id}. Downloading...")
            files = self.blob_service.download_vector_store(doc_id, target_dir)
            if not files:
                return []

        try:
            vectorstore = FAISS.load_local(
                target_dir, 
                self.embeddings, 
                allow_dangerous_deserialization=True
            )
        except Exception as e:
            print(f"Error loading FAISS index: {e}")
            return []

        # 4. Search
        results = vectorstore.similarity_search_with_score(query, k=k)
        
        processed_results = []
        print("--- DEBUG: Search Results Metadata ---")
        for doc, score in results:
            print(f"Metadata: {doc.metadata}")
            
            # 1. Try metadata 'page'
            page_num = doc.metadata.get('page')
            
            # If 0-indexed (common in LangChain/PyPDFLoader), usually min is 0. 
            # We assume it is 0-indexed if it comes from metadata.
            if page_num is not None:
                page_num = int(page_num) + 1
            else:
                # 2. If missing, try regex on content (e.g. "Page 15")
                match = re.search(r'Page\s+(\d+)', doc.page_content, re.IGNORECASE)
                if match:
                    try:
                        page_num = int(match.group(1))
                        # Regex extracted pages are usually already 1-based (human readable)
                        print(f"Extracted Page from Content: {page_num}")
                    except:
                        pass

            # 3. Default to 1 if still not found
            if not page_num:
                page_num = 1
            
            processed_results.append({
                'content': doc.page_content,
                'page': page_num,
                'score': float(score)
            })
            
        return processed_results

    def get_document_url(self, doc_id):
        """
        Reconstructs the blob path for the PDF and gets a SAS URL.
        doc_id: Category/Year/Filename_stem
        """
        # doc_id is like: AAMA/2021/2603-21_Coatings-Aluminum
        # We need to turn this back into: pdfs/AAMA/2021/2603-21_Coatings-Aluminum.pdf
        
        # Assumption: The original file has .pdf extension
        blob_path = f"pdfs/{doc_id}.pdf"
        
        print(f"--- DEBUG: Constructing PDF URL ---")
        print(f"Doc ID: {doc_id}")
        print(f"Target Blob Path: {blob_path}")
        
        url = self.blob_service.get_sas_url(blob_path)
        print(f"Generated URL: {url}")
        return url

