import pandas as pd

def derive_clazz_metadata(x_df, clazz_df, groups_df, x_cols=None):
    x_cols = ["team.bib", "team.clazz"] if x_cols is None or not (isinstance(x_cols, list) and len(x_cols)==2) else x_cols
    clazz_map_df = pd.merge(x_df[x_cols], clazz_df[[
        "_id", "reference", "categoryClazz", "en"]], left_on="team.clazz", right_on="_id").drop(columns=["team.clazz", "_id"]).rename(columns={"en": "clazz_label"})

    clazz_map_df = pd.merge(clazz_map_df, groups_df[["reference", "tinyLabel", "label", "color", "en"]].rename(
        columns={"reference": "categoryClazz"}), on="categoryClazz").rename(columns={"en": "group_label"})
    
    # Reorder and reindex. Or should we leave it?
    clazz_map_df.sort_values("team.bib", inplace=True)
    clazz_map_df.reset_index(drop=True, inplace=True)

    return clazz_map_df
