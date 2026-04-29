class Users:    
    def users(self, project_id):
        endpoint = f"projects/{project_id}/users"
        params = {}
        if self.output_format in ["geojson", "gdf"]:
            params["output"] = "geojson"

        # Pass params to _get
        data = self._get(endpoint, params=params)
        return self._format_output(data)