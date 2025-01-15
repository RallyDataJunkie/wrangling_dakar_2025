import pandas as pd

def derive_clazz_metadata(withdrawn_teams_df, clazz_df, groups_df):
    clazz_map_df = pd.merge(withdrawn_teams_df[["team.bib", "team.clazz"]], clazz_df[[
        "_id", "reference", "categoryClazz", "en"]], left_on="team.clazz", right_on="_id").drop(columns=["team.clazz", "_id"]).rename(columns={"en": "clazz_label"})

    clazz_map_df = pd.merge(clazz_map_df, groups_df[["reference", "tinyLabel", "label", "color", "en"]].rename(
        columns={"reference": "categoryClazz"}), on="categoryClazz").rename(columns={"en": "group_label"})

    return clazz_map_df
