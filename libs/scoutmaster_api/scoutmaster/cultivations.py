import pandas as pd


class Cultivations:
    def cultivations(self, project_id):
        endpoint = f"projects/{project_id}/cultivations"
        params = {}
        if self.output_format in ["geojson", "gdf"]:
            params["output"] = "geojson"

        # Pass params to _get
        data = self._get(endpoint, params=params)
        return self._format_output(data)
    
    def cultivations_by_field(self, field_id):
        endpoint = f"fields/{field_id}/calendar"
        params = {}
        if self.output_format in ["geojson", "gdf"]:
            params["output"] = "geojson"

        # Pass params to _get
        data = self._get(endpoint, params=params)
        return self._format_output(data)

    def cultivations_create(self, field_id, cultivation_data):
        endpoint = f"fields/{field_id}/calendar"
        data = self._post(endpoint, cultivation_data)
        return self._format_output(data)
    
    def cultivations_tsum(self, cultivation_id):
        endpoint = f"calendars/{cultivation_id}/tsum"

        data = self._get(endpoint)
        if self.output_format == "json":
            return data
        elif self.output_format == "df":
            # Convert the 'tsum' list of dicts into a DataFrame
            df = pd.DataFrame(data['tsum'])

            # Optional: convert 'date' to datetime
            df['date'] = pd.to_datetime(df['date'])

            # Optional: add crop info as columns for context
            df['crop_name'] = data['crop']['name']
            df['variety_name'] = data['crop']['variety_name']
            df['field_id'] = data['field_id']
            
            return df
    