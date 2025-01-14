# Load in the required packages
import pandas as pd
from jupyterlite_simple_cors_proxy import furl, xurl


def _coldropper(df, cols=None):
    if cols is None:
        return
    dropcols = [c for c in cols if c in df.columns]
    df.drop(columns=dropcols, inplace=True)


def mergeInLangLabels(df, col, key="shortLabel"):
    # Unpack the lists of labels into their own rows
    # to give a long dataframe.
    longLabels = pd.json_normalize(df[col].explode())

    # This is the only new bit
    # If there are no labels, we may get empty rows
    # or rows filled with null / NA values in the long datafreme.
    # So we can pre-emptively drop such rows if they appear.
    longLabels.dropna(axis="index", how="all", inplace=True)
    # If we don't drop the empty rows, we may get issues
    # in the pivot stage.

    # Reshape the long dataframe to a wide dataframe by pivoting
    # the locale to column names using text values, and using
    # the category (variable) as the row index.
    wideLabels = longLabels.pivot(
        index='variable',
        columns='locale',
        values='text',
    ).reset_index()

    # Merge the data back in to the original dataframe
    _df = pd.merge(df, wideLabels,
                   left_on=key, right_on='variable')

    # Tidy up the dataframe by dropping the now redundant columns
    _df.drop("variable", axis=1, inplace=True)
    # If we pass in a column named "variable" trying to drop it
    # again will cause an error; so ignore any error...
    _df.drop(col, axis=1, inplace=True, errors="ignore")

    return _df


DAKAR_API_TEMPLATE = "https://www.dakar.live.worldrallyraidchampionship.com/api/{path}"

CATEGORY_TEMPLATE = "category-{year}"
GROUPS_TEMPLATE = "allGroups-{year}"
CLAZZ_TEMPLATE = "allClazz-{year}-{category}"
WITHDRAWAL_TEMPLATE = "withdrawal-{year}-{category}"
STAGE_TEMPLATE = "stage-{year}-{category}"
WAYPOINT_TEMPLATE = "waypoint-{year}-{category}-{stage}"


# Define some defaults
YEAR = 2025
CATEGORY = "A"
STAGE = 1


def get_category(year=YEAR):
    category_url = DAKAR_API_TEMPLATE.format(
        path=CATEGORY_TEMPLATE.format(year=year))
    category_df = pd.read_json(furl(category_url))
    category_df = mergeInLangLabels(category_df, "categoryLangs")
    category_df.sort_values(by=["reference"], inplace=True)
    return category_df


def get_groups(year=YEAR):
    groups_url = DAKAR_API_TEMPLATE.format(
        path=GROUPS_TEMPLATE.format(year=year))
    groups_df = pd.read_json(furl(groups_url))
    groups_df = mergeInLangLabels(groups_df, "categoryGroupLangs")
    _coldropper(groups_df, ["liveDisplay", "updatedAt",
                "refueling", "_key", "_updatedAt"])
    groups_df.sort_values(by=["_origin", "position"], inplace=True)
    return groups_df

def get_clazz(year=YEAR, category=CATEGORY):
    clazz_url = DAKAR_API_TEMPLATE.format(
        path=CLAZZ_TEMPLATE.format(year=year, category=category))
    clazz_df = pd.read_json(furl(clazz_url))
    clazz_df = mergeInLangLabels(clazz_df, "categoryClazzLangs")
    _coldropper(clazz_df, ["liveDisplay", "updatedAt",
                "_origin", "_gets", "categoryGroupLangs", "_key", "_updatedAt"])
    clazz_df.sort_values(by=["shortLabel"], inplace=True)
    return clazz_df

def get_waypoints(year=YEAR, category=CATEGORY, stage=STAGE):
    waypoint_url = DAKAR_API_TEMPLATE.format(
    path=WAYPOINT_TEMPLATE.format(year=year, category=category, stage=stage))
    waypoint_df = pd.read_json(furl(waypoint_url))
    stage_code = waypoint_df.iloc[0]["_origin"]

    waypoint_df = pd.json_normalize(waypoint_df["waypoints"].explode())
    waypoint_df["Year"] = YEAR
    waypoint_df["stage"] = STAGE
    waypoint_df["Category"] = CATEGORY
    waypoint_df["stage_code"] = stage_code
    
    _coldropper(waypoint_df, ["isFirstDss"])
    waypoint_df.sort_values(by=["stage", "checkpoint"], inplace=True)
    return waypoint_df

def get_withdrawals(year=YEAR, category=CATEGORY):
    withdrawals_url = DAKAR_API_TEMPLATE.format(
        path=WITHDRAWAL_TEMPLATE.format(year=year, category=category))
    withdrawal_df = pd.read_json(furl(withdrawals_url))
    withdrawal_df.set_index("stage", drop=False, inplace=True)
    withdrawals_by_stage = withdrawal_df["list"].explode()

    withdrawals_by_stage_index = withdrawals_by_stage.index

    withdrawals_by_stage_df = pd.json_normalize(withdrawals_by_stage)

    withdrawals_by_stage_df["stage"] = withdrawals_by_stage_index

    withdrawn_competitors_df = (
        withdrawals_by_stage_df[['stage', 'reason', 'bib', 'team.competitors']]
        .explode('team.competitors')
        .reset_index(drop=True)
    )

    # Normalize the dictionary contents and combine with team_bib
    withdrawn_competitors_df = pd.concat([
        withdrawn_competitors_df[['stage', 'bib', 'reason']],
        pd.json_normalize(withdrawn_competitors_df['team.competitors'])
    ], axis=1)

    team_cols = [
        c for c in withdrawals_by_stage_df.columns if c.startswith("team")]

    # Create a new dataframe, rather than a reference, by using .copy()
    withdrawn_teams_df = withdrawals_by_stage_df[team_cols].copy()
    withdrawn_teams_df.drop("team.competitors", axis=1, inplace=True)
    withdrawn_teams_df.sort_values(by=["team.bib"], inplace=True)

    withdrawals_df = withdrawn_competitors_df[[
        "stage", "bib", "reason", "name"]].copy()
    withdrawals_df.sort_values(by=["stage", "reason"], inplace=True)

    withdrawn_competitors_df.drop("stage", axis=1, inplace=True)
    withdrawn_competitors_df.drop("reason", axis=1, inplace=True)
    withdrawn_competitors_df.sort_values(by=["bib"], inplace=True)

    return withdrawals_df, withdrawn_competitors_df, withdrawn_teams_df


def get_stages(year=YEAR, category=CATEGORY):
    """
    Get stages information (start time, surfaces, sections).
    """
    def flatten_grounds_data(df):
        """
        Flatten nested grounds data into a wide DataFrame format.

        Parameters:
        df (pandas.DataFrame): DataFrame with 'grounds' and 'id' columns where grounds contains nested dictionary data

        Returns:
        pandas.DataFrame: Flattened DataFrame with one row per section
        """

        # Create empty lists to store flattened data
        flattened_data = []
        percentage_data = []
        surface_types = []
        _surface_types = []

        # Sort by stage sector
        df.sort_values("code", inplace=True)

        # Create a mapping for translations
        for _, row in df.iterrows():
            ground_data = row['grounds']

            # Create a translations dictionary
            translations = {f"text_{lang['locale']}": lang['text']
                            for lang in ground_data['groundLangs']}

            _stype = translations["text_en"].lower()

            percentage_data.append(
                {'code': row['code'],
                'percentage': ground_data['percentage'],
                # 'ground_name': ground_data['name'],
                'color': ground_data['color'], "type": _stype})

            if _stype not in _surface_types:
                _surface_types.append(_stype)
                surface_types.append({"type": _stype, **translations})

            # Create a record for each section
            for section in ground_data['sections']:
                section_record = {
                    'code': row['code'],
                    'ground_name': ground_data['name'],
                    'section': section['section'],
                    'start': section['start'],
                    'finish': section['finish'],
                    'color': ground_data['color'],
                    # 'percentage': ground_data['percentage'],
                    "type": _stype
                }
                flattened_data.append(section_record)

        # Create DataFrame from flattened data
        section_df = pd.DataFrame(flattened_data)
        percentage_df = pd.DataFrame(percentage_data)
        surfaces_df = pd.DataFrame(surface_types)

        # Sort columns for better organization
        # Ignore: 'percentage', 'ground_name',
        fixed_columns = ['code',  'section', 'start', 'finish',
                        'color', "type"]
        lang_columns = [
            col for col in section_df.columns if col.startswith('text_')]
        section_df = section_df[fixed_columns + sorted(lang_columns)]

        # Drop duplicates if any still exist
        section_df = section_df.drop_duplicates()
        section_df = section_df.sort_values(
            ['code', 'section'])
        section_df.reset_index(drop=True, inplace=True)

        return section_df, percentage_df, surfaces_df


    stage_url = DAKAR_API_TEMPLATE.format(
        path=STAGE_TEMPLATE.format(year=year, category=category))

    stage_df = pd.read_json(furl(stage_url))

    # Create a dummy colum to match on
    stage_df["variable"] = "stage.name." + stage_df["code"]

    # Update the dataframe by using our new function to
    # merge in the exploded and widenened language labels
    stage_df = mergeInLangLabels(stage_df, "stageLangs", key="variable")
    stage_df['stage_code'] = stage_df['code']
    stage_df.sort_values("startDate", inplace=True)
    stage_df.reset_index(drop=True, inplace=True)

    sectors_df = pd.json_normalize(stage_df[ "sectors"].explode())
    # Generate a stage code
    sectors_df['stage_code'] = sectors_df['code'].str[:2] + '000'
    # And a sector number
    sectors_df['sector_number'] = sectors_df.groupby('stage_code').cumcount() + 1

    # Simplify and tidy the "top-level" stages dataframe
    stage_cols = ['stage_code', 'stage', 'date', 'startDate', 'endDate', 'isCancelled', 'generalDisplay', 'isDelayed', 'marathon',
                'length', 'type',  'timezone', 'stageWithBonus', 'mapCategoryDisplay', 'podiumDisplay', '_bind', 'ar', 'en', 'es', 'fr']
    stage_df = stage_df[stage_cols]


    # Get the sectors with grounds data
    competitive_sectors = sectors_df[['grounds', 'code']].dropna(
        axis="index").explode('grounds').reset_index(drop=True)

    # Simplify the sectors dataframe
    sectors_df = sectors_df[["stage_code", "code", "id", "sector_number",  "powerStage",
                             "length", "startTime", "type", "arrivalTime"]]

    # Sort sectors by stage and sector
    sectors_df.sort_values("code", inplace=True)
    sectors_df.reset_index(drop=True, inplace=True)

    section_surfaces, stage_surfaces, surfaces = flatten_grounds_data(
    competitive_sectors)

    return stage_df, sectors_df, stage_surfaces, section_surfaces, surfaces
