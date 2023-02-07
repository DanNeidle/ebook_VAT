# ebook VAT effect evaluation

# (c) Dan Neidle of Tax Policy Associates Ltd, 2022
# licensed under the GNU General Public License, version 2

# all ONS data from https://www.ons.gov.uk/economy/inflationandpriceindices/datasets/consumerpriceindicescpiandretailpricesindexrpiitemindicesandpricequotes
# except 2019 data which is here: https://www.ons.gov.uk/economy/inflationandpriceindices/datasets/consumerpriceindicescpiandretailpricesindexrpiitemindicesandpricequotes/itemindices2019
# note data can't be scraped from website, as filename changes unpredictably, so instead files should be downloaded
# and names conformed
# also note at least one file was in binary format and had to be converted to csv

import os
import statistics
import scipy
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import datetime
from PIL import Image
import calendar

dates = []
prices_on_date = {}

chart_title = "20% ebook VAT cut"

# this is the target to analyse
target_item = "EBOOKS"

# this is the month before the relevant VAT cut
normalising_target_date = datetime.datetime(year=2020, month=4, day=1)

# these are comparables, taken from column C of the spreadsheet
items_to_find = ["BOOK FICTION P/BACK TOP 10", "BOOK-NON-FICTION-PAPER-BACK", "MUSIC STREAMING SUBSCRIPTIONS",
                 "GAMES CONSOLES ONLINE SUB SERV", "MOBILE PHONE APPLICATIONS",
                 "COMPUTER GAME DOWNLOADS", "MUSIC DOWNLOADS", "COMPUTER SOFTWARE"]

items_to_find.sort()  # nice to put them in alphabetical order

items_to_find.insert(0, target_item)  # and then put target item first

# create lists for each item
for x in items_to_find:
    prices_on_date[x] = []

# get list of all available dates - scraping all "upload-itemindices" csv files in ONS_data directory
for filename in os.listdir('ONS_data'):
    if "upload-itemindices" not in filename:
        continue
    date = filename.replace("upload-itemindices","").replace(".csv","")
    month = int(date[4:])
    year = int(date[:-2])
    dates.append(datetime.datetime(year=year, month=month, day=1))

# now sort the dates
dates.sort()

# extract CPI data
print("Reading CPI data")
cpi_data = pd.read_csv(f"ONS_data/CPI.csv")

cpi = []
for x in dates:
    for cpi_index, cpi_row in cpi_data.iterrows():
        if cpi_row["Month"] == (str(x.year) + " " + x.strftime("%b").upper()):
            cpi.append(cpi_row["Index"])
            break

# check that we found CPI data for each date
if len (dates) != len (cpi):
    print("Error - missing CPI")
    exit()

print(f"CPI data: {cpi}")


# now reading all the ONS data in
for x in dates:
    print(f"Reading ONS data for {x.month}/{x.year}...")

    df = pd.read_csv(f"ONS_data/upload-itemindices{x.year}{x.month:02d}.csv")

    prices_found = {}
    for index, row in df.iterrows():
        # search for each of the specific items
        for target in prices_on_date:
            if row["ITEM_DESC"] == target:
                prices_found[target] = row["ALL_GM_INDEX"]
                prices_on_date[target].append(row["ALL_GM_INDEX"])    # this is CPI
                break

    print(f"{x.month}/{x.year}:  {prices_found}")

# normalise data
index_for_target_date = dates.index(normalising_target_date)

cpi = [float(i)/cpi[index_for_target_date] for i in cpi]
for x in prices_on_date:
    prices_on_date[x] = [float(i) / prices_on_date[x][index_for_target_date] for i in prices_on_date[x]]

# Print out all data for e.g. import into excel
human_dates = []
for x in dates:
    human_dates.append(x.strftime("%d/%m/%Y"))

print("")
print("Final data for export to Excel:")
print('Date, ' + str(human_dates).replace("\'", "").replace("[", "").replace("]", ""))

for x in prices_on_date:
    print(x.replace(",", "").replace(" ", "_") + ", " + str(prices_on_date[x]).replace("[", "").replace("]", ""))

# for each item, calculate change in average price before/after index date
# and calculate t-test
change_in_average_price = []

# this prints t-test for all products
months_for_t = 6
months_for_bar_chart = 23

for item in prices_on_date:
    prior_months = prices_on_date[item][:index_for_target_date + 1]
    subsequent_months = prices_on_date[item][index_for_target_date + 1:]
    prior_average = statistics.mean(prior_months[-months_for_bar_chart:])
    subsequent_average = statistics.mean(subsequent_months[:months_for_bar_chart])
    change_in_average_price.append(subsequent_average - prior_average)
    ttest = scipy.stats.ttest_ind(prior_months[-months_for_t:], subsequent_months[:months_for_t],
                                  equal_var=False, alternative='greater')
    # this is t-test using Welch’s t-test (doesn't assume equal population variance)
    # the alternative hypothesis is that the price in the pre-Jan 2021 period is greater
    print(f"month t-test for {item}: {ttest}")

# prepare for bar chart by sorting in order of price change (going forward/back the same period as the t-test)
sorted_items = [x for _,x in sorted(zip(change_in_average_price, items_to_find))]
change_in_average_price.sort()

# grab logo
logo_jpg = Image.open("logo_full_white_on_blue.jpg")
logo_layout = [dict(
        source=logo_jpg,
        xref="paper", yref="paper",
        x=1, y=1.03,
        sizex=0.1, sizey=0.1,
        xanchor="right", yanchor="bottom"
    )]


# now plot it

fig_change = make_subplots(specs=[[{"secondary_y": False}]])

fig_change.update_layout(
    images=logo_layout,
    title=f'The {chart_title} - overall change in price of products from {dates[index_for_target_date - months_for_bar_chart].strftime("%B %Y")} to {dates[index_for_target_date + months_for_bar_chart].strftime("%B %Y")}',
    yaxis=dict(
        title="% change",
        tickformat='.0%',  # so we get nice percentages
    ),

    )

fig_change.add_trace(go.Bar(
        x=[x.capitalize() for x in sorted_items],
        y=change_in_average_price
    ))

fig_change.show()

# now plot price movements
fig_prices = make_subplots(specs=[[{"secondary_y": False}]])
fig_prices.update_layout(
    images=logo_layout,
    title=f"{chart_title} - ONS index changes for related consumer goods, normalised to {calendar.month_name[normalising_target_date.month]} {normalising_target_date.year}",
    yaxis=dict(
        title="Relative prices",
        tickformat='.0%',  # so we get nice percentages
    ),
    xaxis=dict(
            range=(min(dates), max(dates)),
            tick0=min(dates),
            dtick="M1",  # monthly x axis ticks
            tickformat='%b %Y'
        ),

    )

# plot a scatter for cpi and then each specified item
plots = [[cpi, "CPI"]]
for x in prices_on_date:
    plots.append([prices_on_date[x], x])

for plot in plots:

    # make the target plot visible immediately. the others only visible if clicked on
    if plot[1] == target_item:
        visibility = True
    else:
        visibility = 'legendonly'

    # dashed lines for key and cpi plots
    if plot[1] == target_item or plot[1] == "CPI":
        dash = "dash"
    else:
        dash = None

    fig_prices.add_trace(go.Scatter(
        x=dates,
        y=plot[0],
        mode="lines+text+markers",  # no markers
        line=dict(dash=dash),
        name=plot[1].capitalize(),
        showlegend=True,
        visible=visibility
    ),
        secondary_y=False)

    # now add line and annotation showing moment VAT was removed
    fig_prices.add_vline(x=normalising_target_date.timestamp() * 1000, line_dash="dot",
                  annotation_text=chart_title,
                  annotation_position="top right")

fig_prices.show()
