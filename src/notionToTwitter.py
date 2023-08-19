"""
Author: Nandita Bhaskhar
End-to-end script for posting twitter threads from a Notion Database of your choice to your Twitter account
"""

import sys

import tweepy

sys.path.append('../')

import time
import arrow
import json
import argparse

from TwitterAPI import TwitterAPI
from notion_client import Client

from lib.port_utils import getAllUntweetedRowsFromNotionDatabase, filterRowsToBePostedBasedOnDate, postRowToTwitter
from lib.port_utils import NotionTweetRow

from globalStore import constants

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
    start = arrow.get(time.time()).to('US/Pacific').format('YYYY-MM-DD HH:mm:ss ZZ')
    print('Starting at ' + str(start) + '\n\n')

    # parse all arguments
    args = parser.parse_args()

    # open secrets 
    with open("../secrets/secrets_twitter_{}.json".format(args.project), "r") as f:
        secrets = json.load(f)
    with open("../secrets/secrets_notion_{}.json".format(args.project), "r") as f:
        secrets_notion = json.load(f)

    # initialize notion client and determine notion DB
    notion = Client(auth=secrets_notion['notionToken'])
    notionDB_id = secrets_notion['databaseID']

    # start a twitter api session
    api_v1 = TwitterAPI(consumer_key=secrets['APIConsumerKey'],
                        consumer_secret=secrets['APIConsumerSecret'],
                        access_token_key=secrets['AccessToken'],
                        access_token_secret=secrets['AccessTokenSecret']
                        )

    # You can provide the consumer key and secret with the access token and access
    # token secret to authenticate as a user
    # auth = tweepy.OAuth1UserHandler(
    #     secrets['APIConsumerKey'], secrets['APIConsumerSecret'], secrets['AccessToken'], secrets['AccessTokenSecret']
    # )
    # api_v1 = tweepy.API(auth)

    api_v2 = tweepy.Client(
                        bearer_token=secrets['BearerToken'],
                        consumer_key=secrets['APIConsumerKey'], consumer_secret=secrets['APIConsumerSecret'],
                        access_token=secrets['AccessToken'], access_token_secret=secrets['AccessTokenSecret']
                        )

    while True:
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
            row = NotionTweetRow(row, notion)
            # post the row to twitter
            postRowToTwitter(row, api_v1, api_v2, notion)

        time.sleep(int(args.sleep))
