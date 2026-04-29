import pandas as pd
import requests


class Observations:
    def observations(self, project_id):
        endpoint = f"projects/{project_id}/observations"
        params = {}
        if self.output_format in ["geojson", "gdf"]:
            params["output"] = "geojson"

        # Pass params to _get
        data = self._get(endpoint, params=params)
        return self._format_output(data)
    
    def observations_create(self, project_id, obs_data):
        """
        Create a new observation in the specified project.

        Args:
            project_id (str): The ID of the project.
            obs_data (dict): Observation data with required fields:
                {
                    "user_id": "uuid",
                    "acquired_at": "ISO timestamp",
                    "geometry": { "type": "Point", "coordinates": [x, y] },
                    "reference_code": "string"
                }

        Returns:
            pd.DataFrame or dict: Created observation.
        """
        self._check_auth()
        
        endpoint = f"{self.host}projects/{project_id}/observations"
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }

        try:
            # IMPORTANT: use json=obs_data
            response = requests.post(endpoint, json=obs_data, headers=headers)
            print(response)
            data = response.json()
          

            if response.status_code in (200, 201):
                self.output_format = "json"
                return self._format_output(data["data"][0])
                # return (
                #     pd.DataFrame([response_json])
                #     if self.output_format == "df"
                #     else response_json
                # )
            else:
                raise Exception(
                    f"Failed to create observation: "
                    f"{response.status_code} {response.text}"
                )

        except requests.exceptions.RequestException as e:
            raise Exception(f"Request failed: {e}")
        
    def observations_values_create(self, obs_id, obs_data):
        """
        Create a new observation value.

        Args:
            obs_id (str): Observation ID.
            obs_data (dict): Value data, e.g.:
                {
                    "parameter_id": 1,
                    "value": 23.5,
                    "operator": ">",   # optional, default "="
                    "target_min": 20.0, # optional
                    "target_max": 30.0  # optional
                }

            Allowed operator symbols:
                =   equal to (default)
                !=  not equal to
                <   less than
                <=  less than or equal to
                >   greater than
                >=  greater than or equal to

        Returns:
            dict or DataFrame: Created value.
        """
        endpoint = f"observations/{obs_id}/values"

        # Optional: light client-side validation
        allowed_operators = {"=", "!=", "<", "<=", ">", ">="}
        operator = obs_data.get("operator", "=")
        if operator not in allowed_operators:
            raise ValueError(
                f"Invalid operator '{operator}'. Allowed: {sorted(allowed_operators)}"
            )
        obs_data["operator"] = operator
        # Optional: ensure target_min and target_max are floats or None
        self._validate_numeric_fields(obs_data, ["target_min", "target_max", "value"])
        try:
            data = self._post(endpoint, obs_data)
            return pd.DataFrame(data) if self.output_format == "df" else data
        except Exception as e:
            # Check if this is a 409 Conflict from the API
            msg = str(e)
            if "409" in msg:
                # Optional: parse JSON error
                try:
                    import json
                    error_info = json.loads(msg.split(" ", 1)[1])
                    return {
                        "status": "exists",
                        "message": error_info.get("error", "Value already exists"),
                        "fields": error_info.get("fields", [])
                    }
                except Exception:
                    return {"status": "exists", "message": "Observation value already exists."}
            # re-raise other exceptions
            raise
        