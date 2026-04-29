class LayerTypes:
    def layer_types(self, project_id=None):

        """
        Retrieves available layer types, optionally filtered by layer source.
        Args:
            layer_source_id (str, optional): Filter by layer source ID.
        Returns:
            pd.DataFrame or list: Layer types as DataFrame or JSON list.
        """
        endpoint = "layer-types"
        params = {}
        if project_id is not None:
            params["project_id"] = project_id
        data = self._get(endpoint, params)
        return self._format_output(data)