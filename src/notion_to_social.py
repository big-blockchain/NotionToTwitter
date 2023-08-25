"""
Author: Damon Xiong
End-to-end script for posting twitter threads from a Notion Database of your choice to your Scocial account
"""

import sys
import time
import traceback
import arrow
import json
import argparse
import tweepy

from TwitterAPI import TwitterAPI
from notion_client import Client
from instagrapi import Client as Instagram

from lib.notion_utils import NotionRow, filter_rows_to_be_posted_based_on_date, \
    get_all_unpost_rows_from_notion_database
from lib.twitter_utils import post_row_to_twitter
from lib.instagram_utils import post_row_to_instagram
from globalStore import constants

# arguments
PYTHON = sys.executable
parser = argparse.ArgumentParser()
parser.add_argument('--project', default='test', type=str,
                    help='Project name with secrets. Options are: promptgogo')
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

    with open("../secrets/secrets_{}.json".format(args.project), "r") as f:
        secrets = json.load(f)

    if 'twitter' in secrets:
        print('Twitter secrets found')
        can_tweet = True
    if 'instagram' in secrets:
        print('Instagram secrets found')
        can_instagram = True

    # initialize notion client and determine notion DB
    notion = Client(auth=secrets.get('notion').get('notionToken'))
    notionDB_id = secrets.get('notion').get('databaseID')

    # if can_instagram:
    #     instagram = Instagram()
    #     instagram.login(secrets_instagram['username'], secrets_instagram['password'])

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
                api_v1 = TwitterAPI(consumer_key=secrets.get('twitter').get('APIConsumerKey'),
                                    consumer_secret=secrets.get('twitter').get('APIConsumerSecret'),
                                    access_token_key=secrets.get('twitter').get('AccessToken'),
                                    access_token_secret=secrets.get('twitter').get('AccessTokenSecret')
                                    )

                api_v2 = tweepy.Client(
                    bearer_token=secrets.get('twitter').get('BearerToken'),
                    consumer_key=secrets.get('twitter').get('APIConsumerKey'),
                    consumer_secret=secrets.get('twitter').get('APIConsumerSecret'),
                    access_token=secrets.get('twitter').get('AccessToken'),
                    access_token_secret=secrets.get('twitter').get('AccessTokenSecret')
                )
                try:
                    post_row_to_twitter(row, api_v1, api_v2, notion)
                except:
                    traceback.print_exc()
                    print('post twitter failed.')
            else:
                print('no tweet platform', can_tweet)

            if can_instagram and constants.SUPPORT_PLATFORM.get('instagram') in row.platform \
                    and constants.SUPPORT_PLATFORM.get('instagram') not in row.posted_platform:
                try:
                    webhook_url = secrets.get('instagram').get('zapierWebhook')
                    post_row_to_instagram(row, webhook_url, notion)
                    # post_row_to_instagram_by_api(row, instagram, notion)
                except:
                    traceback.print_exc()
                    print('post instagram failed.')
            else:
                print('no instagram platform', can_tweet)

            if sorted(row.posted_platform) == sorted(row.platform):
                print('All platform posted')

                updates = {'Posted?': {"checkbox": True}}
                notion.pages.update(row.pageID, properties=updates)

        time.sleep(int(args.sleep))
