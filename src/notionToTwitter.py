"""
Author: Nandita Bhaskhar
End-to-end script for posting twitter threads from a Notion Database of your choice to your Twitter account
"""

import sys

import time
import arrow
import json
import argparse

from TwitterAPI import TwitterAPI
from notion_client import Client

from lib.port_utils import get_all_unpost_rows_from_notion_database, filter_rows_to_be_posted_based_on_date, \
    post_row_to_twitter, \
    post_row_to_instagram
from lib.port_utils import NotionRow

from globalStore import constants
import tweepy

sys.path.append('../')


# arguments
PYTHON = sys.executable
parser = argparse.ArgumentParser()
parser.add_argument('--project', default='test', type=str,
                    help='Twitter username key in dict. Options are: test')
parser.add_argument('--sleep', default='300', type=str,
                    help='Sleep time between posting')

# main script
if __name__ == "__main__":
    print('\n\n==========================================================')
    start = arrow.get(time.time()).to('utc').format('YYYY-MM-DD HH:mm:ss ZZ')
    print('Starting at ' + str(start) + '\n\n')

    # parse all arguments
    args = parser.parse_args()

    # open secrets
    can_tweet = False
    can_instagram = False
    try:
        with open("../secrets/secrets_twitter_{}.json".format(args.project), "r") as f:
            secrets_twitter = json.load(f)
            can_tweet = True
    except FileNotFoundError:
        print("twitter config is not found")
        can_tweet = False

    with open("../secrets/secrets_notion_{}.json".format(args.project), "r") as f:
        secrets_notion = json.load(f)

    try:
        with open("../secrets/secrets_instagram_{}.json".format(args.project), "r") as f:
            secrets_instagram = json.load(f)
            can_instagram = True
    except FileNotFoundError:
        print("instagram config is not found")
        can_instagram = False

    # initialize notion client and determine notion DB
    notion = Client(auth=secrets_notion['notionToken'])
    notionDB_id = secrets_notion['databaseID']

    while True:
        # get all unpost notion rows
        allNotionRows = get_all_unpost_rows_from_notion_database(notion, notionDB_id)

        # get today's date
        datetime = arrow.now().to('utc').date()
        print(datetime)

        # filter based on datetime
        todayNotionRows = filter_rows_to_be_posted_based_on_date(allNotionRows, datetime)
        print(str(len(todayNotionRows)) + ' filtered rows for today')

        # loop over row in filtered rows collection
        for row in todayNotionRows:
            row = NotionRow(row, notion)
            if can_tweet and constants.SUPPORT_PLATFORM.get('twitter') in row.platform \
                    and constants.SUPPORT_PLATFORM.get('twitter') not in row.posted_platform:
                # start a twitter api session
                api_v1 = TwitterAPI(consumer_key=secrets_twitter['APIConsumerKey'],
                                    consumer_secret=secrets_twitter['APIConsumerSecret'],
                                    access_token_key=secrets_twitter['AccessToken'],
                                    access_token_secret=secrets_twitter['AccessTokenSecret']
                                    )

                api_v2 = tweepy.Client(
                    bearer_token=secrets_twitter['BearerToken'],
                    consumer_key=secrets_twitter['APIConsumerKey'],
                    consumer_secret=secrets_twitter['APIConsumerSecret'],
                    access_token=secrets_twitter['AccessToken'],
                    access_token_secret=secrets_twitter['AccessTokenSecret']
                )
                post_row_to_twitter(row, api_v1, api_v2, notion)
            else:
                print('no tweet platform', can_tweet)

            if can_instagram and constants.SUPPORT_PLATFORM.get('instagram') in row.platform \
                    and constants.SUPPORT_PLATFORM.get('instagram') not in row.posted_platform:
                webhook_url = secrets_instagram['zapierWebhook']
                post_row_to_instagram(row, webhook_url, notion)
            else:
                print('no instagram platform', can_tweet)

            if sorted(row.posted_platform) == sorted(row.platform):
                print('All platform posted')

                updates = {'Posted?': {"checkbox": True}}
                notion.pages.update(row.pageID, properties=updates)

        time.sleep(int(args.sleep))
