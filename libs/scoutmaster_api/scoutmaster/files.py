import requests

class Files:
    def upload_file(input_path: str, upload_path: str, content_type: str = None):
        """
        Uploads a file to S3 using a presigned URL.

        Args:
            input_path: Path to the local file.
            upload_path: The S3 presigned PUT URL from your backend.
            content_type: Optional MIME type (e.g., 'application/json', 'image/tiff').
        """

        with open(input_path, "rb") as f:
            file_data = f.read()

        headers = {}
        if content_type:
            headers["Content-Type"] = content_type

        response = requests.put(
            upload_path,
            data=file_data,
            headers=headers,
        )

        if response.status_code not in (200, 204):
            raise Exception(f"Upload failed with status {response.status_code}: {response.text}")

        print("✅ File uploaded successfully!")
