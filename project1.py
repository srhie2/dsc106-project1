from pathlib import Path
import textwrap
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

folder = Path(__file__).resolve().parent
raw = pd.read_csv(folder / "grocerydb.csv")
data = raw.drop_duplicates()

bars = data[data["store"] == "WholeFoods"].copy()
bars = bars[bars["category"] == "snacks-bars"]
bars["name_lower"] = bars["name"].fillna("").str.lower()
bars = bars[bars["name_lower"].str.contains(r"\bprotein\b")]
bars = bars[bars["name_lower"].str.contains(r"\bbars?\b")]
candidate_count = len(bars)

bars = bars.dropna(
    subset=["price", "package_weight", "Protein", "Sugars, total"]
)
bars = bars[bars["price"] > 0]
bars = bars[bars["package_weight"] > 0]
bars = bars[bars["Protein"] > 0]
bars = bars[bars["Protein"] <= 100]
bars = bars[bars["Sugars, total"] >= 0]
bars = bars[bars["Sugars, total"] <= 100]

bars = bars[bars["Protein"] + bars["Sugars, total"] <= 100]
valid_count = len(bars)

bars = bars[bars["package_weight"] >= 20]
bars = bars[bars["package_weight"] <= 100]
small_package_count = len(bars)

names = bars["name_lower"].str.replace("ounces", "oz", regex=False)
names = names.str.replace("ounce", "oz", regex=False)
ounces = names.str.extract(r"([0-9.]+)\s*oz\b")[0].astype(float)
named_grams = ounces * 28.3495

difference = abs(bars["package_weight"] - named_grams)
bars = bars[difference <= named_grams * 0.02]

pack_pattern = r"\b\d+\s*(?:pk|pack|ct|count)\b|\b(?:packs?|box|case)\b"
is_multipack = bars["name_lower"].str.contains(pack_pattern)
bars = bars[is_multipack == False].copy()
bars = bars.reset_index(drop=True)

bars["protein_per_bar"] = (
    bars["Protein"] * bars["package_weight"] / 100
)
bars["cost_per_10g"] = bars["price"] / bars["protein_per_bar"] * 10
bars["sugar_per_10g"] = bars["Sugars, total"] / bars["Protein"] * 10

better_count = 0

for i in range(len(bars)):
    for j in range(len(bars)):
        cheaper = (
            bars.loc[j, "cost_per_10g"]
            < bars.loc[i, "cost_per_10g"]
        )
        less_sugar = (
            bars.loc[j, "sugar_per_10g"]
            < bars.loc[i, "sugar_per_10g"]
        )

        if cheaper and less_sugar:
            better_count = better_count + 1
            break

bars["plot_cost"] = bars["cost_per_10g"].round(5)
bars["plot_sugar"] = bars["sugar_per_10g"].round(5)

profiles = bars.groupby(["plot_cost", "plot_sugar"]).size()
profiles = profiles.reset_index(name="records")

nugo = bars[
    bars["name_lower"].str.contains("slim crunchy peanut butter")
].iloc[0]

think = bars[
    bars["name_lower"].str.contains("high protein bar brownie crunch")
].iloc[0]

bulletproof = bars[
    bars["name_lower"].str.contains("coconut cream chocolate fudge")
].iloc[0]

print("Exact duplicate records removed:", len(raw) - len(data))
print("Protein-bar candidates:", candidate_count)
print("After required-value checks:", valid_count)
print("After the 20-100 g package filter:", small_package_count)
print("Final records:", len(bars))
print("Distinct plotted locations:", len(profiles))
print("Records with a cheaper, lower-sugar alternative:", better_count)

plt.rcParams["font.family"] = "DejaVu Sans"
plt.rcParams["font.size"] = 11
plt.rcParams["text.parse_math"] = False

teal = "#087F8C"
orange = "#AD542E"
gray = "#8998A3"

fig = plt.figure(figsize=(8.5, 11), facecolor="white")

fig.text(
    0.075, 0.95,
    "Cheaper protein does not always\ncome with more sugar",
    va="top", fontsize=23, fontweight="bold", color="#18242B"
)

fig.text(
    0.075, 0.853,
    f"{len(bars)} screened Whole Foods protein-bar records from GroceryDB\n"
    "Both axes compare the amount needed to obtain 10 g of protein.",
    va="top", fontsize=11, color="#52616B", linespacing=1.5
)

fig.text(
    0.075, 0.782,
    f"{better_count} of {len(bars)} records have another option "
    "that is cheaper AND lower in total sugar.",
    fontsize=11.2, fontweight="bold", color="#18242B"
)

ax = fig.add_axes([0.13, 0.29, 0.80, 0.42])

ax.scatter(
    profiles["plot_cost"],
    profiles["plot_sugar"],
    s=profiles["records"] * 20,
    color=gray,
    alpha=0.8,
    edgecolor="white",
    linewidth=0.5,
    zorder=3
)

for product, color in [
    (nugo, teal),
    (think, teal),
    (bulletproof, orange)
]:
    same_location = profiles[
        (profiles["plot_cost"] == product["plot_cost"])
        & (profiles["plot_sugar"] == product["plot_sugar"])
    ]
    count = same_location["records"].iloc[0]

    ax.scatter(
        product["cost_per_10g"],
        product["sugar_per_10g"],
        s=count * 20,
        color=color,
        edgecolor="white",
        linewidth=0.5,
        zorder=5
    )

ax.annotate(
    "NuGo Slim Crunchy Peanut Butter\n"
    f"${nugo['plot_cost']:.2f} | {nugo['plot_sugar']:.2f} g sugar",
    xy=(nugo["cost_per_10g"], nugo["sugar_per_10g"]),
    xytext=(0.18, 5.5),
    fontsize=10,
    color=teal,
    linespacing=1.4,
    arrowprops={"arrowstyle": "-", "color": teal, "lw": 1}
)

ax.annotate(
    "Think! Brownie Crunch\n"
    f"${think['cost_per_10g']:.2f} | {think['sugar_per_10g']:.2f} g sugar",
    xy=(think["cost_per_10g"], think["sugar_per_10g"]),
    xytext=(1.48, 3.0),
    fontsize=10,
    color=teal,
    linespacing=1.4,
    arrowprops={"arrowstyle": "-", "color": teal, "lw": 1}
)

ax.annotate(
    "Bulletproof Coconut Cream\n"
    f"${bulletproof['cost_per_10g']:.2f} | "
    f"{bulletproof['sugar_per_10g']:.2f} g sugar",
    xy=(bulletproof["cost_per_10g"], bulletproof["sugar_per_10g"]),
    xytext=(2.75, 4.8),
    fontsize=10,
    color=orange,
    linespacing=1.4,
    arrowprops={"arrowstyle": "-", "color": orange, "lw": 1}
)

ax.set_xlim(0, 4.4)
ax.set_ylim(-1.1, 16)

ax.set_xticks(
    [0, 1, 2, 3, 4],
    ["$0", "$1", "$2", "$3", "$4"]
)
ax.set_yticks([0, 4, 8, 12, 16])

ax.set_xlabel(
    "Cost per 10 g of protein (USD) - cheaper to the left",
    labelpad=12
)
ax.set_ylabel(
    "Total sugar per 10 g of protein (g) - less sugar below",
    labelpad=10
)

ax.tick_params(axis="both", length=0, pad=8)
ax.grid(color="#E6ECEF", linewidth=0.8)
ax.set_axisbelow(True)

for spine in ax.spines.values():
    spine.set_visible(False)

size_handles = []

for count in [1, 3, 6]:
    handle = ax.scatter(
        [], [], s=count * 20, color=gray, label=str(count)
    )
    size_handles.append(handle)

fig.legend(
    handles=size_handles,
    title="Records at the same chart position",
    loc="center",
    bbox_to_anchor=(0.72, 0.746),
    ncol=3,
    frameon=False,
    fontsize=9.5,
    title_fontsize=9.5
)

fig.text(
    0.075, 0.207,
    "Two different choices, rather than one unavoidable trade-off",
    fontsize=12, fontweight="bold", color="#18242B"
)

fig.text(
    0.075, 0.180,
    "NuGo Slim is cheapest; Think! costs more but reports zero sugar.\n"
    "Think! also costs less AND has less total sugar "
    "than the highlighted Bulletproof bar.",
    fontsize=10.5, color="#35434C", linespacing=1.5, va="top"
)

notes = (
    "Scope: named protein bars; 20-100 g packages; "
    "named ounce size agrees within 2%; no named multipacks.\n"
    "Cost = price x 10 / protein grams per bar. "
    "Sugar = total sugar per 100 g x 10 / protein per 100 g.\n"
    "Circle area = record count; equal locations grouped at 5 decimals. "
    "Missing required values excluded.\n"
    "Recorded prices; normalized costs, not fractional-bar purchases. "
    "Total sugar is not added sugar.\n"
    "These two measures do not rank overall health, protein quality, or taste.\n"
    "Source: GroceryDB course CSV - dsc106.com/resources/data/grocerydb.csv"
)

fig.text(
    0.075, 0.043, notes,
    fontsize=8.5, color="#52616B", linespacing=1.45
)

# 6. Save the image and the one-page chart PDF.
fig.savefig(
    folder / "protein_value_chart.pdf",
    facecolor="white"
)