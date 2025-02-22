# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.11.4
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %%
# %load_ext autoreload
# %autoreload 2

# %%
import json
import random
import string
import time

# %%
import arrow

# %%
import os
import sys
sys.path.append('../')

# %%
from TwitterAPI import TwitterAPI

# %%
from notion_client import Client

# %%
from globalStore import constants

# %%
from lib.port_utils import get_all_unpost_rows_from_notion_database, filter_rows_to_be_posted_based_on_date, post_row_to_twitter
from lib.port_utils import NotionRow

# %% [markdown]
# ## Configs

# %%
with open(constants.TWITTER_SECRET_FILE, "r") as f:
    secrets = json.load(f)

# %%
with open(constants.NOTION_SECRET_FILE, "r") as f:
    secrets_notion = json.load(f)

# %% [markdown]
# ## Clients

# %%
notion = Client(auth = secrets_notion['notionToken'])

# %%
notionDB_id = secrets_notion['databaseID']

# %%
api = TwitterAPI(consumer_key = secrets['APIConsumerKey'], 
                    consumer_secret = secrets['APIConsumerSecret'],
                    access_token_key = secrets['AccessToken'],
                    access_token_secret = secrets['AccessTokenSecret']
                )

# %% [markdown]
# ## Loop

# %%
# get all untweeted notion rows
allNotionRows = get_all_unpost_rows_from_notion_database(notion, notionDB_id)

# %%
# fix datetime
datetime = arrow.now().to('US/Pacific').date()
datetime

# %%
# filter based on datetime
todayNotionRows = filter_rows_to_be_posted_based_on_date(allNotionRows, datetime)
len(todayNotionRows)

# %%
# loop over row in filtered rows collection
for row in todayNotionRows: 
    row = NotionRow(row, notion)
    # post the row to twitter
    post_row_to_twitter(row, api, notion)

# %%
