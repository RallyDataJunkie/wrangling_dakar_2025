
import pandas as pd

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
