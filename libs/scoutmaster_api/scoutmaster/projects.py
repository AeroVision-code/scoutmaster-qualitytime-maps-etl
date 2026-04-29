import requests
import mimetypes

class Projects:
    def projects(self):
        try: 
            endpoint = "projects/"
            data = self._get(endpoint)
            return self._format_output(data)
        except requests.exceptions.RequestException as e:
            raise Exception(f"Request failed: {e}")
    
    def project_create(self, user_id, name, abbreviation=None):

        """
        Create new project

        Args:
            project_collection_id (str): The ID of the project collection.
            fields_data (list): List of field dicts to create.

        Returns:
            pd.DataFrame or dict: Created fields as DataFrame or JSON.
        """
        try:
            endpoint = f"projects"
            if abbreviation is None:
                abbreviation = name[:2].upper()
                
            project_data = {
                "user_id": user_id,
                "name": name,
                "abbreviation": abbreviation
            }
            data = self._post(endpoint, project_data)
            return data

        except requests.exceptions.RequestException as e:
            raise Exception(f"Request failed: {e}")
        
    def project_by_id(self, project_id):
        try:
            endpoint = f"projects/{project_id}"
            data = self._get(endpoint)
            return data
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Request failed: {e}")
        
        
        
    def project_uploadurl(self, project_id):
        """
        POST a layer upload URL request (all fields mandatory).

        Args:
            field_id (str): The ID of the field.
            layer_type_id (str): The layer type ID.
            acquired_at (str): Acquisition timestamp (ISO8601, e.g., 2025-11-21T10:15:30Z).

        Returns:
            Formatted response (DataFrame or dict) depending on self.output_format.
        """
        self._check_auth()
        endpoint = f"projects/{project_id}/logo/upload-url"



        # Send POST request
        data = self._post(endpoint)
        return data
    
    def project_upload_logo(self, project_id: str, file_path: str):
        """
        Upload a logo for a project using the presigned URL from the backend.

        Args:
            project_id: The project ID to upload the logo for.
            file_path: Local path to the logo file.

        Returns:
            Dict containing the file_key and public_url.
        """
        # 1️⃣ Get presigned URL from backend
        upload_data = self.project_uploadurl(project_id)
        upload_url = upload_data["upload_url"]
        file_key = upload_data["file_key"]
        public_url = upload_data["public_url"]

        # 2️⃣ Determine MIME type
        mime_type, _ = mimetypes.guess_type(file_path)
        if not mime_type:
            mime_type = "application/octet-stream"

        # 3️⃣ Upload the file to S3
        with open(file_path, "rb") as f:
            response = requests.put(upload_url, data=f, headers={"Content-Type": mime_type})

        if response.status_code not in (200, 201):
            raise Exception(f"S3 upload failed: {response.status_code} {response.text}")

        print("✅ Logo uploaded successfully!")

        # 4️⃣ Return metadata
        return {"file_key": file_key, "public_url": public_url}
        
    def project_upload_logo(self, project_id, file_path):
        """
        Upload a logo file for a specific project.
        
        Steps:
        1. Request presigned URL from API
        2. Upload file to S3 using PUT
        3. Return final metadata result from API if needed
        """
        self._check_auth()

        # 1️⃣ Request presigned URL
        endpoint = f"projects/{project_id}/logo/upload-url"

        try:
            presign_data = self._post(endpoint)
            print(presign_data)
            upload_url = presign_data["upload_url"]
            public_url = presign_data["public_url"]
            file_key = presign_data["file_key"]

            # 2️⃣ Upload file directly to S3 using PUT
        
            mime_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"

            with open(file_path, "rb") as file:
                upload_res = requests.put(upload_url, data=file, headers={"Content-Type": mime_type})

            if upload_res.status_code not in (200, 201):
                raise Exception(f"S3 upload failed: {upload_res.status_code} {upload_res.text}")

            print("Logo uploaded successfully!")

            # 3️⃣ Return metadata including final public URL
            return {
                "project_id": project_id,
                "file_key": file_key,
                "public_url": public_url
            }
        except requests.exceptions.RequestException as e:
            raise Exception(f"Request failed: {e}")

        
