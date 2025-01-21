import seaborn as sns
from shiny import render
from shiny.express import input, ui
import pandas as pd

from dakarAPI import DakarAPIClient

dakar = DakarAPIClient(
    use_cache=True,
    backend='memory',
    # cache_name='dakar_cache',
    expire_after=3600  # Cache for 1 hour
)

stages_df, sectors_df, stage_surfaces_df, section_surfaces_df, surfaces_df = dakar.get_stages()

# Get distances from percentages
stage_surfaces_df = pd.merge(
    sectors_df[["code", "length"]], stage_surfaces_df, on="code")
stage_surfaces_df["distance"] = stage_surfaces_df["length"] * \
    stage_surfaces_df["percentage"]/100


# Mapping types to colors
type_color_map = dict(
    zip(stage_surfaces_df['type'], stage_surfaces_df['color']))

import seaborn as sns

def plot_stage_surface_chart(selected_code, typ):
    #plt.clf()

    # Filter the DataFrame for the selected code
    filtered_df = stage_surfaces_df[stage_surfaces_df['code'] == selected_code]

    # Create the plot (remove plt.figure() call)
    ax = sns.barplot(
        data=filtered_df,
        x="type",
        y=typ,
        palette=type_color_map,
        hue="type",
        legend=False
    )

    # Adjust labels and title
    #plt.title(f"Dodged Bar Chart for Code {selected_code}")
    #plt.xlabel("Surface type")
    #plt.ylabel(f"{typ.capitalize()}")
    #plt.xticks(rotation=45)
    return ax
#----

#stage_surfaces_df = pd.DataFrame({"code": ["this", "that"]})

# Create dropdown widget
ui.input_select("code", "Code:",
    stage_surfaces_df['code'].unique().tolist(),
)

ui.input_select("percentage", "Percentage (%)",
    ['percentage', 'distance'])


@render.plot(alt="A Seaborn histogram on penguin body mass in grams.")
def plot():
    ax = plot_stage_surface_chart(input.code(), input.percentage())
    #ax = sns.histplot(data=penguins, x="body_mass_g", bins=input.n())
    #ax.set_title("Palmer Penguins")
    #ax.set_xlabel("Mass (g)")
    #ax.set_ylabel("Count")
    return ax
