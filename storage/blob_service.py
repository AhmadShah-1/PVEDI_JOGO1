import os
from datetime import datetime, timedelta
from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions
from azure.identity import DefaultAzureCredential

class BlobService:
    def __init__(self):
        # Prefer Connection String if available (Development), otherwise Managed Identity (Production)
        self.connect_str = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
        self.account_name = os.getenv('AZURE_STORAGE_ACCOUNT_NAME', 'jogostorage')
        self.container_name = 'nyccodesvectorstore'
        
        if self.connect_str:
            self.blob_service_client = BlobServiceClient.from_connection_string(self.connect_str)
        else:
            credential = DefaultAzureCredential()
            account_url = f"https://{self.account_name}.blob.core.windows.net"
            self.blob_service_client = BlobServiceClient(account_url, credential=credential)
            
        self.container_client = self.blob_service_client.get_container_client(self.container_name)

    def list_blobs_hierarchy(self):
        """
        Scans the 'pdfs/' folder to build a hierarchy: Category -> Year -> [Files]
        Returns: Dict structure for frontend dropdowns
        """
        hierarchy = {}
        # List all blobs in the pdfs folder
        blobs = self.container_client.list_blobs(name_starts_with="pdfs/")
        
        for blob in blobs:
            # Expected format: pdfs/Category/Year/filename.pdf
            parts = blob.name.split('/')
            if len(parts) >= 4 and blob.name.endswith('.pdf'):
                category = parts[1]
                year = parts[2]
                filename = parts[-1]
                
                # We need the relative path that matches the vector store structure
                # Vector store structure seems to be: Category/Year/filename (no 'pdfs/' prefix in manifest usually)
                # But let's store the full blob path for PDF retrieval, and a "doc_id" for vector retrieval.
                # Based on user description: "folder_path": "AAMA/2020", "pdf_name": "2605-20_errata"
                # So we can construct the key.
                
                if category not in hierarchy:
                    hierarchy[category] = {}
                if year not in hierarchy[category]:
                    hierarchy[category][year] = []
                
                hierarchy[category][year].append({
                    'name': filename,
                    'blob_path': blob.name,
                    # ID used to find the vector store: Category/Year/filename_stem
                    'doc_id': f"{category}/{year}/{os.path.splitext(filename)[0]}"
                })
        
        return hierarchy

    def get_sas_url(self, blob_path):
        """
        Generates a read-only SAS URL for a specific blob.
        """
        if not blob_path:
            return None
            
        try:
            # If using Connection String (Account Key available)
            if self.connect_str:
                sas_token = generate_blob_sas(
                    account_name=self.blob_service_client.account_name,
                    container_name=self.container_name,
                    blob_name=blob_path,
                    account_key=self.blob_service_client.credential.account_key,
                    permission=BlobSasPermissions(read=True),
                    expiry=datetime.utcnow() + timedelta(hours=1)
                )
                return f"https://{self.blob_service_client.account_name}.blob.core.windows.net/{self.container_name}/{blob_path}?{sas_token}"
            else:
                # For Managed Identity, we rely on User Delegation SAS (more complex) 
                # or just returning the URL if the container is public (unlikely for internal docs).
                # For this specific sample, let's assume Connection String is primary for simplicity,
                # or we'd need to implement User Delegation Key fetching.
                # Fallback: assume public or connection string was actually present.
                pass
        except Exception as e:
            print(f"Error generating SAS: {e}")
            return None

    def download_vector_store(self, doc_id, local_dir):
        """
        Downloads the FAISS index and PKL file for a given document.
        doc_id example: AAMA/2020/2605-20_errata
        Target blob folder: vectorstores_RecursiveSplitting/AAMA/2020/2605-20_errata/
        """
        # Construct blob prefix
        prefix = f"vectorstores_RecursiveSplitting/{doc_id}/"
        
        blobs = self.container_client.list_blobs(name_starts_with=prefix)
        downloaded_files = []
        
        if not os.path.exists(local_dir):
            os.makedirs(local_dir)
            
        for blob in blobs:
            if blob.name.endswith('.faiss') or blob.name.endswith('.pkl'):
                file_name = os.path.basename(blob.name)
                download_path = os.path.join(local_dir, file_name)
                
                # Only download if not already cached
                if not os.path.exists(download_path):
                    with open(download_path, "wb") as my_blob:
                        blob_client = self.container_client.get_blob_client(blob)
                        download_stream = blob_client.download_blob()
                        my_blob.write(download_stream.readall())
                
                downloaded_files.append(download_path)
                
        return downloaded_files

