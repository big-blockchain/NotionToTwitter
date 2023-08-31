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

import tweepy.errors

from lib.notion_utils import NotionClient, NotionRow
from lib.instagram_utils import post_row_to_instagram, InstagramClient
from globalStore import constants
from lib.twitter_utils import TwitterClient

# arguments
PYTHON = sys.executable
parser = argparse.ArgumentParser()
parser.add_argument('--project', default='promptgogo', type=str,
                    help='Project name with secrets. Options are: promptgogo')
parser.add_argument('--sleep', default='14400', type=str,
                    help='Sleep time between posting default is 14400 seconds(4 hours)')

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

    while True:
        print('Start Action at ' + str(arrow.get(time.time()).to('utc').format('YYYY-MM-DD HH:mm:ss ZZ')) + '\n\n')
        # initialize notion client and determine notion DB
        notion = NotionClient(token=secrets.get('notion').get('notionToken'),
                              db_id=secrets.get('notion').get('databaseID'))

        # loop over row in filtered rows collection
        for row in notion.filtered_rows:
            row = NotionRow(row, notion)
            if can_tweet and constants.SUPPORT_PLATFORM.get('twitter') in row.platform \
                    and constants.SUPPORT_PLATFORM.get('twitter') not in row.posted_platform:
                twitter_client = TwitterClient(
                    bearer_token=secrets.get('twitter').get('BearerToken'),
                    consumer_key=secrets.get('twitter').get('APIConsumerKey'),
                    consumer_secret=secrets.get('twitter').get('APIConsumerSecret'),
                    access_token=secrets.get('twitter').get('AccessToken'),
                    access_token_secret=secrets.get('twitter').get('AccessTokenSecret')
                )
                # start a twitter api session
                try:
                    twitter_client.post_row_to_twitter(row, notion)
                except tweepy.errors.TooManyRequests:
                    print('Too many requests')
                    twitter_client.rate_limter.limiter_now()
                except Exception as e:
                    print(str(e))
                    traceback.print_exc()
                    print('post twitter failed.')
            else:
                print('no tweet platform', can_tweet)

            if can_instagram and constants.SUPPORT_PLATFORM.get('instagram') in row.platform \
                    and constants.SUPPORT_PLATFORM.get('instagram') not in row.posted_platform:
                try:
                    # webhook_url = secrets.get('instagram').get('zapierWebhook')
                    # post_row_to_instagram(row, webhook_url, notion)
                    # post_row_to_instagram_by_api(row, instagram, notion)
                    instagram = InstagramClient(
                        access_token=secrets.get('instagram').get('accessToken'),
                        client_id=secrets.get('instagram').get('clientId'),
                        client_secret=secrets.get('instagram').get('clientSecret'),
                        user_id=secrets.get('instagram').get('userId'),
                    )
                    instagram.post(row, notion)
                except Exception as e:
                    print(str(e))
                    traceback.print_exc()
                    print('post instagram failed.')
            else:
                print('no instagram platform', can_tweet)

            if sorted(row.posted_platform) == sorted(row.platform):
                print('All platform posted')
                notion.update_notion_checked_posted(row)

            # hold 60 seconds for every row sended
            time.sleep(60)

        print('End Action at ' + str(arrow.get(time.time()).to('utc').format('YYYY-MM-DD HH:mm:ss ZZ')) + '\n\n')
        time.sleep(int(args.sleep))
