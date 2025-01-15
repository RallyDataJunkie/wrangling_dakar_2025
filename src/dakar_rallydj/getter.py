import pandas as pd
from typing import Optional, Union, List, Tuple
from jupyterlite_simple_cors_proxy.proxy import CorsProxy, create_cached_proxy


class DakarAPIClient:
    """Client for accessing Dakar Rally API data."""

    DAKAR_API_TEMPLATE = "https://www.dakar.live.worldrallyraidchampionship.com/api/{path}"

    # Template strings
    CATEGORY_TEMPLATE = "category-{year}"
    GROUPS_TEMPLATE = "allGroups-{year}"
    CLAZZ_TEMPLATE = "allClazz-{year}-{category}"
    WITHDRAWAL_TEMPLATE = "withdrawal-{year}-{category}"
    STAGE_TEMPLATE = "stage-{year}-{category}"
    WAYPOINT_TEMPLATE = "waypoint-{year}-{category}-{stage}"
    SCORE_TEMPLATE = "lastScore-{year}-{category}-{stage}"

    def __init__(self, year: int = 2025, category: str = "A", stage: int = 1,
                 use_cache: bool = False, **cache_kwargs):
        """
        Initialize the Dakar API client.
        
        Args:
            year: Default year for API requests
            category: Default category for API requests
            stage: Default stage for API requests
            use_cache: Whether to enable request caching
            **cache_kwargs: Cache configuration options passed to requests_cache
        """
        self.year = year
        self.category = category
        self.stage = stage

        # Initialize the proxy with caching if requested
        if use_cache:
            self.proxy = create_cached_proxy(**cache_kwargs)
        else:
            self.proxy = CorsProxy()

    @staticmethod
    def _coldropper(df: pd.DataFrame, cols: Optional[list] = None) -> None:
        """Drop specified columns from DataFrame if they exist."""
        if cols is None:
            return
        dropcols = [c for c in cols if c in df.columns]
        df.drop(columns=dropcols, inplace=True)

    @staticmethod
    def mergeInLangLabels(df: pd.DataFrame, col: str, key: str = "shortLabel") -> pd.DataFrame:
        """Merge language labels into the main DataFrame."""
        # Unpack the lists of labels into their own rows
        longLabels = pd.json_normalize(df[col].explode())

        # Drop empty rows
        longLabels.dropna(axis="index", how="all", inplace=True)

        # Reshape to wide format
        wideLabels = longLabels.pivot(
            index='variable',
            columns='locale',
            values='text',
        ).reset_index()

        # Merge data back
        _df = pd.merge(df, wideLabels, left_on=key, right_on='variable')

        # Clean up
        _df.drop("variable", axis=1, inplace=True)
        _df.drop(col, axis=1, inplace=True, errors="ignore")

        return _df

    @staticmethod
    def normalize_team_competitors(df: pd.DataFrame, year: int = 2025) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        Transform a DataFrame containing nested competitor lists into three slighly more normalized DataFrames.
        
        Args:
            df (pd.DataFrame): Input DataFrame with columns including 'team.bib', 'team.model', and 'team.competitors' (list of dicts)
        
        Returns:
            Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]: (teams_df, competitors_df, results_df)
                - teams_df: DataFrame with team information
                - competitors_df: DataFrame with competitor information
                - results_df: DataFrame of results;
        """
        # Create competitors DataFrame using explode and json_normalize
        competitors_df = (
            df[['team.bib', 'team.competitors']]
            .explode('team.competitors')
            .rename(columns={'team.bib': 'team_bib'})
            .reset_index(drop=True)
        )

        # Normalize the dictionary contents and combine with team_bib
        competitors_df = pd.concat([
            competitors_df['team_bib'],
            pd.json_normalize(competitors_df['team.competitors'])
        ], axis=1)

        # Align column names with an ealier Dakar analysis codebase
        competitors_df["Year"] = year
        competitors_df.rename(
            columns={'team.bib': 'Bib', 'name': 'Name'}, inplace=True)
        
        # Create teams DataFrame by dropping the competitors column
        teams_df = df.drop('team.competitors', axis=1)
        team_cols = [c for c in teams_df.columns if c.startswith(
            "team")]
        teams_df = teams_df[team_cols]
        teams_df.rename(columns={'team.bib': 'Bib'}, inplace=True)

        team_cols.remove("team.bib")
        team_cols.append("team.competitors")
        return teams_df, competitors_df, df.rename(columns={'team.bib': 'Bib'}).drop(team_cols, axis=1)

    def _get_url(self, template: str, **kwargs) -> str:
        """Construct API URL from template."""
        path = template.format(**kwargs)
        return self.DAKAR_API_TEMPLATE.format(path=path)

    def get_category(self, year: Optional[int] = None,
                     use_cache: Optional[bool] = None, **cache_kwargs) -> pd.DataFrame:
        """
        Get category data.
        
        Args:
            year: Override default year
            use_cache: Override default caching behavior for this request
            **cache_kwargs: Override cache settings for this request
        """
        year = year or self.year

        # Create request-specific proxy if cache settings are different
        proxy = self._get_request_proxy(use_cache, **cache_kwargs)

        url = self._get_url(self.CATEGORY_TEMPLATE, year=year)
        category_df = pd.read_json(proxy.furl(url))
        category_df = self.mergeInLangLabels(category_df, "categoryLangs")
        category_df.sort_values(by=["reference"], inplace=True)
        return category_df

    def get_groups(self, year: Optional[int] = None,
                   use_cache: Optional[bool] = None, **cache_kwargs) -> pd.DataFrame:
        """
        Get groups data.
        
        Args:
            year: Override default year
            use_cache: Override default caching behavior for this request
            **cache_kwargs: Override cache settings for this request
        """
        year = year or self.year

        # Create request-specific proxy if cache settings are different
        proxy = self._get_request_proxy(use_cache, **cache_kwargs)

        url = self._get_url(self.GROUPS_TEMPLATE, year=year)
        groups_df = pd.read_json(proxy.furl(url))
        groups_df = self.mergeInLangLabels(groups_df, "categoryGroupLangs")
        self._coldropper(groups_df, ["liveDisplay", "updatedAt",
                                     "refueling", "_key", "_updatedAt"])
        groups_df.sort_values(by=["_origin", "position"], inplace=True)
        return groups_df

    def _get_clazz_single(self, year: Optional[int] = None,
                          category: Optional[str] = None,
                          proxy: Optional[CorsProxy] = None) -> pd.DataFrame:
        """
        Get clazz data for a single category.
        
        Internal method used by get_clazz.
        """
        year = year or self.year
        category = category or self.category
        proxy = proxy or self.proxy

        url = self._get_url(self.CLAZZ_TEMPLATE, year=year, category=category)
        clazz_df = pd.read_json(proxy.furl(url))
        clazz_df = self.mergeInLangLabels(clazz_df, "categoryClazzLangs")

        # Add category info
        clazz_df['category'] = category
        clazz_df['categoryClazz'] = clazz_df["_origin"].str.replace(
            "categoryClazz-", "")

        # Clean up columns
        self._coldropper(clazz_df, [
            "liveDisplay", "updatedAt", "_origin", "_gets",
            "categoryGroupLangs", "_key", "_updatedAt"
        ])

        clazz_df.sort_values(by=["shortLabel"], inplace=True)
        return clazz_df

    def get_clazz(self, year: Optional[int] = None,
                  category: Optional[Union[str, List[str]]] = None,
                  use_cache: Optional[bool] = None, **cache_kwargs) -> pd.DataFrame:
        """
        Get clazz data for one or more categories.
        
        Args:
            year: Override default year
            category: Category or list of categories to fetch
            use_cache: Override default caching behavior for this request
            **cache_kwargs: Override cache settings for this request
            
        Returns:
            DataFrame containing clazz data for all requested categories
        """
        year = year or self.year
        category = category or self.category

        # Create request-specific proxy if cache settings are different
        proxy = self._get_request_proxy(use_cache, **cache_kwargs)

        # Convert single category to list
        if isinstance(category, str):
            category = [category]

        # Fetch data for each category
        dfs = [self._get_clazz_single(year, c, proxy) for c in category]

        # Combine results
        return pd.concat(dfs, ignore_index=True).reset_index(drop=True)

    def get_waypoints(self, year: Optional[int] = None,
                      category: Optional[str] = None,
                      stage: Optional[int] = None,
                      use_cache: Optional[bool] = None, **cache_kwargs) -> pd.DataFrame:
        """Get waypoints data for a specific stage and category."""
        year = year or self.year
        category = category or self.category
        stage = stage or self.stage

        proxy = self._get_request_proxy(use_cache, **cache_kwargs)

        url = self._get_url(self.WAYPOINT_TEMPLATE, year=year,
                            category=category, stage=stage)
        waypoint_df = pd.read_json(proxy.furl(url))
        stage_code = waypoint_df.iloc[0]["_origin"]

        waypoint_df = pd.json_normalize(waypoint_df["waypoints"].explode())
        waypoint_df["Year"] = year
        waypoint_df["stage"] = stage
        waypoint_df["Category"] = category
        waypoint_df["stage_code"] = stage_code

        self._coldropper(waypoint_df, ["isFirstDss"])
        waypoint_df.sort_values(by=["stage", "checkpoint"], inplace=True)
        return waypoint_df

    def _get_withdrawals_single(self, year: Optional[int] = None,
                                category: Optional[str] = None,
                                proxy: Optional[CorsProxy] = None) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Get withdrawals data for a single category."""
        year = year or self.year
        category = category or self.category
        proxy = proxy or self.proxy

        url = self._get_url(self.WITHDRAWAL_TEMPLATE,
                            year=year, category=category)
        withdrawal_df = pd.read_json(proxy.furl(url))
        withdrawal_df.set_index("stage", drop=False, inplace=True)
        withdrawals_by_stage = withdrawal_df["list"].explode()

        withdrawals_by_stage_index = withdrawals_by_stage.index
        withdrawals_by_stage_df = pd.json_normalize(withdrawals_by_stage)
        withdrawals_by_stage_df["stage"] = withdrawals_by_stage_index

        # Process competitor withdrawals
        withdrawn_competitors_df = (
            withdrawals_by_stage_df[[
                'stage', 'reason', 'bib', 'team.competitors']]
            .explode('team.competitors')
            .reset_index(drop=True)
        )

        withdrawn_competitors_df = pd.concat([
            withdrawn_competitors_df[['stage', 'bib', 'reason']],
            pd.json_normalize(withdrawn_competitors_df['team.competitors'])
        ], axis=1)

        # Process team withdrawals
        team_cols = [
            c for c in withdrawals_by_stage_df.columns if c.startswith("team")]
        withdrawn_teams_df = withdrawals_by_stage_df[team_cols].copy()
        withdrawn_teams_df.drop("team.competitors", axis=1, inplace=True)
        withdrawn_teams_df.sort_values(by=["team.bib"], inplace=True)
        withdrawn_teams_df.reset_index(drop=True, inplace=True)

        # Process withdrawals summary
        withdrawals_df = withdrawn_competitors_df[[
            "stage", "bib", "reason"]].drop_duplicates()
        withdrawals_df['_category'] = category
        withdrawals_df.sort_values(by=["stage", "reason"], inplace=True)
        withdrawals_df.reset_index(drop=True, inplace=True)

        # Clean up competitor data
        withdrawn_competitors_df.drop(
            ["stage", "reason"], axis=1, inplace=True)
        withdrawn_competitors_df.sort_values(by=["bib"], inplace=True)
        withdrawn_competitors_df.reset_index(drop=True, inplace=True)

        return withdrawals_df, withdrawn_competitors_df, withdrawn_teams_df

    def get_withdrawals(self, year: Optional[int] = None,
                        category: Optional[Union[str, List[str]]] = None,
                        use_cache: Optional[bool] = None, **cache_kwargs) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Get withdrawals data for one or more categories."""
        year = year or self.year
        category = category or self.category
        proxy = self._get_request_proxy(use_cache, **cache_kwargs)

        if isinstance(category, str):
            category = [category]

        df_list1, df_list2, df_list3 = [], [], []

        for cat in category:
            df1, df2, df3 = self._get_withdrawals_single(year, cat, proxy)
            df_list1.append(df1)
            df_list2.append(df2)
            df_list3.append(df3)

        combined_df1 = pd.concat(df_list1, ignore_index=True).sort_values(
            ["stage", "bib", "reason"]).reset_index(drop=True)
        combined_df2 = pd.concat(df_list2, ignore_index=True).sort_values(
            ["bib"]).reset_index(drop=True)
        combined_df3 = pd.concat(df_list3, ignore_index=True).sort_values(
            ["team.bib"]).reset_index(drop=True)

        return combined_df1, combined_df2, combined_df3

    @staticmethod
    def _flatten_grounds_data(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Flatten nested grounds data into a wide DataFrame format."""
        flattened_data = []
        percentage_data = []
        surface_types = []
        _surface_types = []

        df.sort_values("code", inplace=True)

        for _, row in df.iterrows():
            ground_data = row['grounds']
            translations = {f"text_{lang['locale']}": lang['text']
                            for lang in ground_data['groundLangs']}
            _stype = translations["text_en"].lower()

            percentage_data.append({
                'code': row['code'],
                'percentage': ground_data['percentage'],
                'color': ground_data['color'],
                "type": _stype
            })

            if _stype not in _surface_types:
                _surface_types.append(_stype)
                surface_types.append({"type": _stype, **translations})

            for section in ground_data['sections']:
                section_record = {
                    'code': row['code'],
                    'ground_name': ground_data['name'],
                    'section': section['section'],
                    'start': section['start'],
                    'finish': section['finish'],
                    'color': ground_data['color'],
                    "type": _stype
                }
                flattened_data.append(section_record)

        section_df = pd.DataFrame(flattened_data)
        percentage_df = pd.DataFrame(percentage_data)
        surfaces_df = pd.DataFrame(surface_types)

        fixed_columns = ['code', 'section', 'start', 'finish', 'color', "type"]
        lang_columns = [
            col for col in section_df.columns if col.startswith('text_')]
        section_df = section_df[fixed_columns + sorted(lang_columns)]

        section_df = section_df.drop_duplicates()
        section_df = section_df.sort_values(['code', 'section'])
        section_df.reset_index(drop=True, inplace=True)

        return section_df, percentage_df, surfaces_df

    def get_stages(self, year: Optional[int] = None,
                   category: Optional[str] = None,
                   use_cache: Optional[bool] = None, **cache_kwargs) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Get stages information (start time, surfaces, sections)."""
        year = year or self.year
        category = category or self.category
        proxy = self._get_request_proxy(use_cache, **cache_kwargs)

        url = self._get_url(self.STAGE_TEMPLATE, year=year, category=category)
        stage_df = pd.read_json(proxy.furl(url))

        stage_df["variable"] = "stage.name." + stage_df["code"]
        stage_df = self.mergeInLangLabels(
            stage_df, "stageLangs", key="variable")
        stage_df['stage_code'] = stage_df['code']
        stage_df.sort_values("startDate", inplace=True)
        stage_df.reset_index(drop=True, inplace=True)

        sectors_df = pd.json_normalize(stage_df["sectors"].explode())
        sectors_df['stage_code'] = sectors_df['code'].str[:2] + '000'
        sectors_df['sector_number'] = sectors_df.groupby(
            'stage_code').cumcount() + 1

        stage_cols = ['stage_code', 'stage', 'date', 'startDate', 'endDate', 'isCancelled',
                      'generalDisplay', 'isDelayed', 'marathon', 'length', 'type', 'timezone',
                      'stageWithBonus', 'mapCategoryDisplay', 'podiumDisplay', '_bind',
                      'ar', 'en', 'es', 'fr']
        stage_df = stage_df[stage_cols]

        competitive_sectors = sectors_df[['grounds', 'code']].dropna(
            axis="index").explode('grounds').reset_index(drop=True)

        sectors_df = sectors_df[["stage_code", "code", "id", "sector_number", "powerStage",
                                 "length", "startTime", "type", "arrivalTime"]]

        sectors_df.sort_values("code", inplace=True)
        sectors_df.reset_index(drop=True, inplace=True)

        section_surfaces, stage_surfaces, surfaces = self._flatten_grounds_data(
            competitive_sectors)

        return stage_df, sectors_df, stage_surfaces, section_surfaces, surfaces

    @staticmethod
    def long_results(_results: pd.DataFrame) -> pd.DataFrame:
        id_column = "_id"
        point_cols = [col for col in _results.columns if col.startswith(('cg', 'cs'))]
        # Melt only the point-specific columns
        melted = _results[[id_column, "Bib", *point_cols]
                        ].melt(id_vars=[id_column, "Bib"]).dropna()
        melted = melted[melted['variable'].str.contains('position|absolute|relative')]
        melted["type"] = melted["variable"].str.split('.').str[0]
        melted["waypoint"] = melted["variable"].str.extract(r'\.([^\.]+)\.')
        melted["metric"] = melted["variable"].str.split('.').str[-1]

        melted[['value_0', 'value_1']] = pd.DataFrame(
            melted['value'].tolist(),
            index=melted.index
        )
        melted.drop(columns=["value"], inplace=True)
        return melted

    def get_scores(self, year: Optional[int] = None,
                   category: Optional[str] = None,
                   stage: Optional[int] = None,
                   use_cache: Optional[bool] = None, **cache_kwargs) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Get lastScore information (results, times)."""
        year = year or self.year
        category = category or self.category
        stage = stage or self.stage
        proxy = self._get_request_proxy(use_cache, **cache_kwargs)

        url = self._get_url(self.SCORE_TEMPLATE, year=year, category=category, stage=stage)
        _results_df = pd.json_normalize(proxy.cors_proxy_get(url).json())

        teams_df, competitors_df, _results_df = self.normalize_team_competitors(_results_df)

        long_results_df = self.long_results(_results_df)

        return long_results_df, teams_df, competitors_df

    def _get_request_proxy(self, use_cache: Optional[bool], **cache_kwargs) -> CorsProxy:
        """Get appropriate proxy for the request based on cache settings."""
        if use_cache is None or not cache_kwargs:
            return self.proxy

        # Create new proxy with specific cache settings for this request
        if use_cache:
            return create_cached_proxy(**cache_kwargs)
        return CorsProxy()
