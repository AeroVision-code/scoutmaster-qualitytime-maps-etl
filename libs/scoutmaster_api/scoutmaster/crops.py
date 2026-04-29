class Crops:    
    def crops(self, sort_by=None, order=None, limit=None, page=None, lang=None, verbose=False):
        """
        Retrieve a list of crops from the API.
        Parameters
        ----------
        sort_by : str, optional
            The field to sort the results by. Default is None. Options are 'name', 'code', 'created_at', 'updated_at'.
        order : str, optional
            The sort order for results ('asc' or 'desc'). Default is None.
        limit : int, optional
            The maximum number of crops to return. Default is None.
        page : int, optional
            The page number for paginated results. Default is None.
        lang : str, optional
            The language code for the response (e.g., 'en', 'es'). Default is None.
        verbose : bool, optional
            If True, print verbose output for debugging. Default is False.
        Returns
        -------
        dict or list
            Formatted output containing the crops data from the API.
        Examples
        --------
        >>> crops_data = client.crops(limit=10, page=1, lang='en')
        >>> sorted_crops = client.crops(sort_by='name', order='asc', verbose=True)
        """
        
        endpoint = "crops"
        params = {}

        # Add optional parameters if provided
        if sort_by:
            params["sort_by"] = sort_by
        if order:
            params["order"] = order
        if limit:
            params["limit"] = limit
        if page:
            params["page"] = page    
        if lang:
            params["lang"] = lang

        data = self._get(endpoint, params=params, verbose=verbose)
        return self._format_output(data)
    
    def crop_varieties(self, crop_code, sort_by=None, order=None, limit=None, page=None):
        """
        Retrieve crop varieties for a given crop code.
        Args:
            crop_code (str): The code identifying the crop.
            sort_by (str, optional): The field to sort results by. Defaults to None.
            order (str, optional): The sort order ('asc' or 'desc'). Defaults to None.
            limit (int, optional): The maximum number of results to return. Defaults to None.
            page (int, optional): The page number for pagination. Defaults to None.
        Returns:
            Formatted output containing the list of crop varieties matching the query parameters.
        Example:
            >>> varieties = client.crop_varieties('wheat', sort_by='name', order='asc', limit=10, page=1)
        """
                
        endpoint = f"crops/{crop_code}/varieties"
        params = {}
        if sort_by:
            params["sort_by"] = sort_by
        if order:
            params["order"] = order
        if limit:
            params["limit"] = limit
        if page:
            params["page"] = page
            
        data = self._get(endpoint, params=params)    
        
        return self._format_output(data)