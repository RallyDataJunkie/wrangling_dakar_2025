import seaborn as sns
from shiny import render
from shiny.express import input, ui
import pandas as pd
import matplotlib.pyplot as plt

from dakarAPI import DakarAPIClient

dakar = DakarAPIClient(
    use_cache=True,
    backend='memory',
    # cache_name='dakar_cache',
    expire_after=3600  # Cache for 1 hour
)

stages_df, sectors_df, stage_surfaces_df, section_surfaces_df, surfaces_df = dakar.get_stages()

# Rename the 0P000 stage to 00000 to make a simpler sort...
sectors_df.loc[sectors_df['code'].str.startswith('0P'), 'stage_code'] = '00000'


# Get distances from percentages
stage_surfaces_df = pd.merge(
    sectors_df[["code", "length"]], stage_surfaces_df, on="code")
stage_surfaces_df["distance"] = stage_surfaces_df["length"] * \
    stage_surfaces_df["percentage"]/100


# Mapping types to colors
type_color_map = dict(
    zip(stage_surfaces_df['type'], stage_surfaces_df['color']))


def plot_section_surface_chart(stage_code):
    # Filter data for the selected stage code
    stage_df = section_surfaces_df[section_surfaces_df['code']
                                   == stage_code].sort_values(by='start')

    # Create the figure and axis
    fig, ax = plt.subplots(figsize=(10, 2))

    # Plot each section as a horizontal bar
    for _, row in stage_df.iterrows():
        ax.barh(
            y=0,  # Single row
            width=row['finish'] - row['start'],  # Bar width is finish - start
            left=row['start'],  # Start position of the bar
            color=row['color'],  # Color based on surface type
            edgecolor='black',
            label=row['type']  # Label for legend
        )

    # Add legend (only unique types)
    handles, labels = ax.get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    ax.legend(by_label.values(), by_label.keys(), title="Surface Type",
              loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=3)

    # Set title and axis labels
    ax.set_title(f"Stage {stage_code}: Surface Visualization", pad=20)
    ax.set_xlabel("Distance", x=0.03)
    ax.set_yticks([])  # Hide y-axis ticks as it's a single row
    # Adjust x-axis limit to max finish value
    ax.set_xlim(
        0, section_surfaces_df[section_surfaces_df['code'] == stage_code]['finish'].max())

    return ax


#stage_surfaces_df = pd.DataFrame({"code": ["this", "that"]})

# Create dropdown widget
ui.input_select("code", "Code:",
    stage_surfaces_df['code'].unique().tolist(),
)

@render.plot(alt="A Seaborn histogram on penguin body mass in grams.")
def plot():
    ax = plot_section_surface_chart(input.code())
    #ax = sns.histplot(data=penguins, x="body_mass_g", bins=input.n())
    #ax.set_title("Palmer Penguins")
    #ax.set_xlabel("Mass (g)")
    #ax.set_ylabel("Count")
    return ax
