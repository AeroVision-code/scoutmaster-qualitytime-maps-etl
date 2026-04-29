class Subscriptions:
    def subscriptions_by_field(self, field_id):
        endpoint = f"subscription/{field_id}/"
        params = {}
        if self.output_format in ["geojson", "gdf"]:
            params["output"] = "geojson"

        # Pass params to _get
        data = self._get(endpoint, params=params)
        return self._format_output(data)