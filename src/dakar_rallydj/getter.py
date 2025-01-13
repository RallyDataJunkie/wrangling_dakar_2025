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
