# Generated with support from ChatGPT
# # pd.options docs:
# https://pandas.pydata.org/pandas-docs/version/1.4.0/user_guide/options.html
# pd.options.display.width
# pd.options.display.max_colwidth
# pd.options.display.max_rows
import pandas as pd
from IPython.display import display

def truncate_cell_content(value, max_colwidth):
    """
    Truncate cell content to respect max_colwidth.
    Args:
        value: The original cell content.
        max_colwidth: The maximum number of characters to display.
    Returns:
        Truncated cell content with ellipsis if necessary.
    """
    value = str(value)
    return value if len(value) <= max_colwidth else value[:max_colwidth - 3] + "..."


def truncate_and_add_ellipsis(df, max_rows, max_colwidth):
    """
    Truncate the DataFrame to max_rows and add an ellipsis row if necessary.
    Args:
        df: The DataFrame to process.
        max_rows: Maximum number of rows to display.
        max_colwidth: Maximum column width for truncation.
    Returns:
        A truncated DataFrame with an optional ellipsis row.
    """
    if len(df) > max_rows:
        half = max_rows // 2
        top = df.iloc[:half]
        bottom = df.iloc[-half:]
        ellipsis_row = pd.DataFrame(
            [["..."] * len(df.columns)], columns=df.columns)
        df = pd.concat([top, ellipsis_row, bottom], ignore_index=True)

    # Truncate cell content
    for col in df.columns:
        df[col] = df[col].apply(
            lambda x: truncate_cell_content(x, max_colwidth))
    return df

# Store original repr method
original_repr_html = pd.DataFrame._repr_html_


def custom_repr_html(self):
    """Custom HTML representation that splits wide tables"""
    split_wide_table(self)
    return ""


def enable_split_display(width=None, max_colwidth=None, max_rows=None):
    """Enable the custom split display"""
    if width is not None:
        pd.options.display.width = width
    if max_colwidth is not None:
        pd.options.display.max_colwidth = max_colwidth
    if pd.options.display.max_colwidth > pd.options.display.width:
        print(f"ERROR: max_colwidth ({pd.options.display.width}) greater than width ({pd.options.display.width}); resetting down.")
        pd.options.display.max_colwidth = pd.options.display.width - 1
    if max_rows is not None:
        pd.options.display.max_rows = max_rows
    pd.DataFrame._repr_html_ = custom_repr_html


def disable_split_display():
    """Disable the custom split display and restore original"""
    pd.DataFrame._repr_html_ = original_repr_html


def split_wide_table(df, split=True,
                     hide=None, padding=1, width=None):
    """Split a wide table over multiple smaller tables."""
    # Note: column widths may be much larger than heading widths
    if hide:
        hide = [hide] if isinstance(hide, str) else hide
    else:
        hide = []
    
    max_colwidth = pd.options.display.max_colwidth
    max_rows = pd.options.display.max_rows

    cols = [c for c in df.columns if c not in hide]

    # Truncate rows and cell content, and add ellipsis if necessary
    truncated_df = truncate_and_add_ellipsis(df[cols], max_rows, max_colwidth)

    for col in truncated_df.columns:
        truncated_df[col] = truncated_df[col].apply(
            lambda x: truncate_cell_content(x, max_colwidth))

    if not split:
        display(truncated_df[cols])
    else:
        width = width or pd.options.display.width

        _cols = []
        _w = 0
        for col in cols:
            col_width = max(
                len(col), truncated_df[col].astype(str).str.len().max())
            if (_w + col_width + padding) < width:
                _cols.append(col)
                _w += col_width + padding
            else:
                print("\n")
                display(truncated_df[_cols].style.hide(axis="index"))
                _cols = [col]
        if _cols:
            print("\n")
            display(truncated_df[_cols].style.hide(axis="index"))

"""
Usage:

from dakar_rallydj.stylers import enable_split_display

enable_split_display(width=30, max_rows=10)
# Params: width, max_colwidth, max_rows
"""