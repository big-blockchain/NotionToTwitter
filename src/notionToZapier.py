  
"""
Author: Nandita Bhaskhar
End-to-end script for posting twitter threads from a Notion Database of your choice to your Twitter account
"""

import sys
sys.path.append('../')

import time
import arrow
import json
import argparse

from TwitterAPI import TwitterAPI
from notion_client import Client

from lib.port_utils import getAllUntweetedRowsFromNotionDatabase, filterRowsToBePostedBasedOnDate, postRowToTwitter
from lib.port_utils import NotionRow

from globalStore import constants

# main script
if __name__ == "__main__":

    print('\n\n==========================================================')
    start = arrow.get(time.time()).to('US/Pacific').format('YYYY-MM-DD HH:mm:ss ZZ')
    print('Starting at ' + str(start) + '\n\n')

    # Iterate over the arguments
    for key, value in constants.NOTION_SECRETS.items():
        print(f'{key}: {value}')
        # open secrets
        with open(value, "r") as f:
            secrets_notion = json.load(f)

        # initialize notion client and determine notion DB
        notion = Client(auth = secrets_notion['notionToken'])
        notionDB_id = secrets_notion['databaseID']

        # get all untweeted notion rows
        allNotionRows = getAllUntweetedRowsFromNotionDatabase(notion, notionDB_id)

        # get today's date
        datetime = arrow.now().to('US/Pacific').date()
        print(datetime)

        # filter based on datetime
        todayNotionRows = filterRowsToBePostedBasedOnDate(allNotionRows, datetime)
        print(str(len(todayNotionRows)) + ' filtered rows for today')

        # loop over row in filtered rows collection
        for row in todayNotionRows:
            row = NotionRow(row, notion)
            # post the row to zapier

