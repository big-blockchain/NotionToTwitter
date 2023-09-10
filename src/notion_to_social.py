"""
Author: Damon Xiong
End-to-end script for posting twitter threads from a Notion Database of your choice to your Scocial account
"""

import time
import traceback
import arrow
import json

import tweepy.errors

from lib.notion_utils import NotionClient, NotionRow
from lib.instagram_utils import InstagramClient
from globalStore import constants
from lib.twitter_utils import TwitterClient

# main script
if __name__ == "__main__":
    print('\n\n==========================================================')

    # open secrets
    can_tweet = False
    can_instagram = False

    with open("../secrets/secrets.json", "r") as f:
        secrets = json.load(f)

    proxy = secrets.get('proxy')
    if len(proxy) == 0:
        proxy = None
    print(f'get proxy:{proxy}')

    start = arrow.get(time.time()).to('utc').format('YYYY-MM-DD HH:mm:ss ZZ')
    print(secrets.get('project') + ' starting at ' + str(start) + '\n\n')

    if 'twitter' in secrets:
        print('Twitter secrets found')
        can_tweet = True
    if 'instagram' in secrets:
        print('Instagram secrets found')
        can_instagram = True

    cycle_time = secrets.get('sleep').get('cycle')
    row_time = secrets.get('sleep').get('row')

    while True:
        print('Start All Actions at ' + str(arrow.get(time.time()).to('utc').format('YYYY-MM-DD HH:mm:ss ZZ')) + '\n\n')
        # initialize notion client and determine notion DB
        notion = NotionClient(token=secrets.get('notion').get('notionToken'),
                              db_id=secrets.get('notion').get('databaseID'))

        # loop over row in filtered rows collection
        for row in notion.filtered_rows:
            row = NotionRow(row, notion)
            print('Start ' + row.title + ' at ' + str(
                arrow.get(time.time()).to('utc').format('YYYY-MM-DD HH:mm:ss ZZ')) + '\n\n')
            if can_tweet and constants.SUPPORT_PLATFORM.get('twitter') in row.platform \
                    and constants.SUPPORT_PLATFORM.get('twitter') not in row.posted_platform:
                twitter_client = TwitterClient(
                    bearer_token=secrets.get('twitter').get('BearerToken'),
                    consumer_key=secrets.get('twitter').get('APIConsumerKey'),
                    consumer_secret=secrets.get('twitter').get('APIConsumerSecret'),
                    access_token=secrets.get('twitter').get('AccessToken'),
                    access_token_secret=secrets.get('twitter').get('AccessTokenSecret'),
                    proxy=proxy
                )
                # start a twitter api session
                try:
                    twitter_client.post_row_to_twitter(row, notion)
                except tweepy.errors.TooManyRequests:
                    print('Too many requests')
                    twitter_client.rate_limiter.limiter_now()
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
                        proxy=proxy
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

            print('End ' + row.title + ' at ' + str(
                arrow.get(time.time()).to('utc').format('YYYY-MM-DD HH:mm:ss ZZ')) + '\n\n')

            # hold 60 seconds for every row is sent
            time.sleep(row_time)

        print('End All Actions at ' + str(arrow.get(time.time()).to('utc').format('YYYY-MM-DD HH:mm:ss ZZ')) + '\n\n')
        time.sleep(cycle_time)
