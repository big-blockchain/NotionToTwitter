"""
Author: Nandita Bhaskhar
Notion to Twitter helper functions
"""

import os
import re
import sys
import time
import traceback

from globalStore import constants

import arrow
import requests
from tweepy.errors import (
    HTTPException
)

sys.path.append('../')


class NotionRow():
    """ A class denoting a row in the Notion twitter database """

    def __init__(self, row, notion):
        """
        Args:
            row: (notion row)
            notion: (notion Client) Notion client object
        """

        self.pageID = row['id']
        self.created = arrow.get(row['created_time']).to('UTC')
        self.lastEdited = arrow.get(row['last_edited_time']).to('UTC')
        self.pageURL = row['url']
        self.platform = [obj["name"] for obj in row['properties']['Platform']['multi_select']]
        self.posted_platform = [obj["name"] for obj in row['properties']['Posted Platform']['multi_select']]

        self.title = row['properties']['Name']['title'][0]['text']['content'] if row['properties']['Name'][
            'title'] else None

        try:
            self.retweetURL = row['properties']['Retweet URL']['url']
        except KeyError:
            self.retweetURL = None

        try:
            self.postDate = arrow.get(
                row['properties']['Post Date']['date']['start'])
        except KeyError:
            self.postDate = None

        self.tweeted = row['properties']['Posted?']['checkbox']

        self.medias = row['properties']['medias']['files']

        self.rawContent = notion.blocks.children.list(self.pageID)
        self.threadCount = len(self.rawContent['results'])

    def get_tweet_thread(self):
        """
        Returns:
            tweet_thread: (list of dict)
                                each dict has keys: 'text', 'images'
                                'text': (str)
                                'images': (list of str) list of image names
        """
        tweet_thread = []

        for item in self.rawContent['results']:
            try:
                para = ''.join([e['plain_text'] for e in item['paragraph']['rich_text']])
            except:
                pass
            tweet = {'text': para, 'images': self.medias}

            if para != '':
                tweet_thread.append(tweet)

        return tweet_thread, self.retweetURL


def extract_twitter_info(retweet_url):
    if retweet_url is None:
        return None, None
    # 提取 Twitter 账号和推文 ID
    match = re.match(r"https://twitter.com/([^/]+)/status/(\d+)", retweet_url)
    if match:
        username = match.group(1)
        tweet_id = match.group(2)
        return username, tweet_id
    else:
        return None, None


def get_all_unpost_rows_from_notion_database(notion, notion_db_id):
    """
    Gets all rows (pages) that are untweeted from a notion database using a notion client
    Args:
        notion: (notion Client) Notion client object
        notion_db_id: (str) string code id for the relevant database
    Returns:
        all_notion_rows: (list of notion rows)
    """
    start = time.time()
    has_more = True
    all_notion_rows = []
    i = 0

    while has_more:
        if i == 0:
            try:
                query = notion.databases.query(
                    **{
                        "database_id": notion_db_id,
                        "filter": {"property": "Posted?", "checkbox": {"equals": False}},
                    }
                )
            except:
                print('Sleeping to avoid rate limit')
                time.sleep(30)
                query = notion.databases.query(
                    **{
                        "database_id": notion_db_id,
                        "filter": {"property": "Posted?", "checkbox": {"equals": False}},
                    }
                )

        else:
            try:
                query = notion.databases.query(
                    **{
                        "database_id": notion_db_id,
                        "start_cursor": next_cursor,
                        "filter": {"property": "Posted?", "checkbox": {"equals": False}},
                    }
                )
            except:
                print('Sleeping to avoid rate limit')
                time.sleep(30)
                query = notion.databases.query(
                    **{
                        "database_id": notion_db_id,
                        "start_cursor": next_cursor,
                        "filter": {"property": "Posted?", "checkbox": {"equals": False}},
                    }
                )

        all_notion_rows = all_notion_rows + query['results']
        next_cursor = query['next_cursor']
        has_more = query['has_more']
        i += 1

    end = time.time()
    print('Number of rows in notion currently: ' + str(len(all_notion_rows)))
    print('Total time taken: ' + str(end - start))

    return all_notion_rows


def filter_rows_to_be_posted_based_on_date(all_rows, datetime):
    """
    Filters rows (notion pages) from a list of rows whose 'Post Date' matches the given datetime
    Args:
        all_rows: (list of notion rows)  each row should contain a date property named Post Date
        datetime: (arrow/str/datetime) representation of datetime
    Returns:
        filteredRows: (list of notion rows)
    """
    arrow_time = arrow.get(datetime)

    filtered_rows = [item for item in all_rows if 'Post Date' in item['properties']
                     and item['properties']['Post Date']['date'] is not None
                     and arrow.get(item['properties']['Post Date']['date']['start']).datetime <= arrow_time.datetime]

    return filtered_rows


def post_row_to_twitter(row, api_v1, api_v2, notion):
    """
    Post notion row to twitter + prints staus
    Args:
        row: (NotionTweetRow)
        api_v1: (tweepy) instance of twitter v1 api
        api_v2: (tweepy) instance of twitter v2 api
        notion: (notion Client) Notion client object
    """
    # verify if the row is not already tweeted
    if ~row.tweeted:
        # defaults
        reply_to_id, media_id, tweet_text = None, None, None
        tweeted, first_tweet = True, True

        # get thread from notion and the retweet URL if retweet
        thread, retweet_url = row.get_tweet_thread()

        for tweet in thread:
            # tweet text
            tweet_text = tweet['text']

            # media images
            if tweet['images']:
                # loop through images, upload them, get their media ids
                media_ids = []
                for img in tweet['images']:
                    # check if img is a local file or a URL
                    if os.path.isfile(img[img['type']]['url']):
                        # read data from local file
                        file = open(img[img['type']]['url'], 'rb')
                        data = file.read()
                    else:
                        # read data from URL
                        response = requests.get(img[img['type']]['url'])
                        data = response.content
                    w = api_v1.request('media/upload', None, {'media': data})
                    print('UPLOAD MEDIA SUCCESS' if w.status_code ==
                                                    200 else 'UPLOAD MEDIA FAILURE: ' + w.text)
                    if w.status_code == 200:
                        media_ids.append(str(w.json()['media_id']))
            else:
                media_ids = None

            # post tweet with a reference to uploaded image as a reply to the replyToID
            try:
                if reply_to_id:
                    r = api_v2.create_tweet(
                        text=tweet_text, in_reply_to_tweet_id=reply_to_id, media_ids=media_ids)
                else:
                    print("retweetURLretweetURLretweetURL", retweet_url)
                    username, tweet_id = extract_twitter_info(retweet_url)

                    r = api_v2.create_tweet(
                        text=tweet_text, in_reply_to_tweet_id=tweet_id, media_ids=media_ids)
                # update error text
                if r.errors:
                    # 将错误信息记录到 Notion 页面的 "Error Message" 属性中
                    error_messages = [error['message'] for error in r.errors]
                    print('UPDATE STATUS FAILURE: '.join(error_messages))
                    tweeted = False
                    break
                else:
                    print('UPDATE TWITTER STATUS SUCCESS'.join(row.title))

                # update reply to ID
                reply_to_id = r.data["id"]  # 不存在的话抛出错误 Keyerror
                # replyToID = data.get("id")
                # thread tweet ID
                if first_tweet:
                    first_tweet = False
            except HTTPException as e:
                tweeted = False
                # 打印错误的堆栈信息
                traceback.print_exc()
                # 获取错误的类型和值
                err_type, err_value = sys.exc_info()[:2]
                print('UPDATE STATUS FAILURE:', str(e.response.json()), err_type, err_value)
                pass

        # update Notion
        if tweeted:
            row.posted_platform.append(constants.SUPPORT_PLATFORM.get('twitter'))
            posted_platform = [{'name': obj} for obj in row.posted_platform]
            updates = {'Posted Platform': {
                "multi_select": posted_platform}}
            notion.pages.update(row.pageID, properties=updates)
            print('Updated Notion')

    else:
        print('Already tweeted')


def post_row_to_instagram(row, webhook_url, notion):
    """
    Post notion row to twitter + prints staus
    Args:
        row: (NotionTweetRow)
        webhook_url: instance of zapier url
        notion: (notion Client) Notion client object
    """
    # verify if the row is not already tweeted
    if ~row.tweeted:
        # get thread from notion and the retweet URL if retweet
        thread, retweetURL = row.get_tweet_thread()

        for tweet in thread:
            # 定义要发送的数据
            data = {
                "text": tweet['text'],
                "images": tweet['images']
            }

            # 发送 POST 请求到 Zapier Webhook
            response = requests.post(webhook_url, json=data)

            # 检查响应状态码
            if response.status_code == 200:
                print("请求已成功发送到 Zapier Webhook！")
                # update Notion
                row.posted_platform.append(constants.SUPPORT_PLATFORM.get('instagram'))
                posted_platform = [{'name': obj} for obj in row.posted_platform]
                updates = {'Posted Platform': {
                    "multi_select": posted_platform}}
                notion.pages.update(row.pageID, properties=updates)
                print('Updated Notion')
            else:
                print("请求发送失败。响应状态码：", response.status_code)

    else:
        print('Already tweeted')
