"""
Author: Nandita Bhaskhar
Notion to Twitter helper functions
"""

import os
import re
import sys
import time
import traceback

import arrow
import requests
from tweepy.errors import (
    HTTPException
)

sys.path.append('../')


class NotionTweetRow():
    ''' A class denoting a row in the Notion twitter database '''

    def __init__(self, row, notion):
        '''
        Args:
            row: (notion row)
            notion: (notion Client) Notion client object
        '''

        self.pageID = row['id']
        self.created = arrow.get(row['created_time']).to('UTC')
        self.lastEdited = arrow.get(row['last_edited_time']).to('UTC')
        self.pageURL = row['url']

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

    def getTweetThread(self):
        '''
        Returns:
            tweetThread: (list of dict)
                                each dict has keys: 'text', 'images'
                                'text': (str)
                                'images': (list of str) list of image names
        '''
        tweetThread = []

        for item in self.rawContent['results']:
            try:
                para = ''.join([e['plain_text']
                                for e in item['paragraph']['rich_text']])
            except:
                pass
            tweet = {'text': para, 'images': self.medias}

            if para != '':
                tweetThread.append(tweet)

        return tweetThread, self.retweetURL


def extract_twitter_info(retweetURL):
    if retweetURL is None:
        return None, None
    # 提取 Twitter 账号和推文 ID
    match = re.match(r"https://twitter.com/([^/]+)/status/(\d+)", retweetURL)
    if match:
        username = match.group(1)
        tweet_id = match.group(2)
        return username, tweet_id
    else:
        return None, None


def getAllUntweetedRowsFromNotionDatabase(notion, notionDB_id):
    '''
    Gets all rows (pages) that are untweeted from a notion database using a notion client
    Args:
        notion: (notion Client) Notion client object
        notionDB_id: (str) string code id for the relevant database
    Returns:
        allNotionRows: (list of notion rows)
    '''
    start = time.time()
    hasMore = True
    allNotionRows = []
    i = 0

    while hasMore:
        if i == 0:
            try:
                query = notion.databases.query(
                    **{
                        "database_id": notionDB_id,
                        "filter": {"property": "Posted?", "checkbox": {"equals": False}},
                    }
                )
            except:
                print('Sleeping to avoid rate limit')
                time.sleep(30)
                query = notion.databases.query(
                    **{
                        "database_id": notionDB_id,
                        "filter": {"property": "Posted?", "checkbox": {"equals": False}},
                    }
                )

        else:
            try:
                query = notion.databases.query(
                    **{
                        "database_id": notionDB_id,
                        "start_cursor": nextCursor,
                        "filter": {"property": "Posted?", "checkbox": {"equals": False}},
                    }
                )
            except:
                print('Sleeping to avoid rate limit')
                time.sleep(30)
                query = notion.databases.query(
                    **{
                        "database_id": notionDB_id,
                        "start_cursor": nextCursor,
                        "filter": {"property": "Posted?", "checkbox": {"equals": False}},
                    }
                )

        allNotionRows = allNotionRows + query['results']
        nextCursor = query['next_cursor']
        hasMore = query['has_more']
        i += 1

    end = time.time()
    print('Number of rows in notion currently: ' + str(len(allNotionRows)))
    print('Total time taken: ' + str(end - start))

    return allNotionRows


def filterRowsToBePostedBasedOnDate(allRows, datetime):
    '''
    Filters rows (notion pages) from a list of rows whose 'Post Date' matches the given datetime
    Args:
        allRows: (list of notion rows)  each row should contain a date property named Post Date
        datetime: (arrow/str/datetime) representation of datetime
    Returns:
        filteredRows: (list of notion rows)
    '''
    arrowTime = arrow.get(datetime)

    filteredRows = [item for item in allRows if 'Post Date' in item['properties'] and item['properties']['Post Date']
    ['date'] is not None and arrow.get(item['properties']['Post Date']['date']['start']).datetime <= arrowTime.datetime]

    return filteredRows


def postRowToTwitter(row, api_v1, api_v2, notion):
    '''
    Post notion row to twitter + prints staus
    Args:
        row: (NotionTweetRow)
        api: (tweepy) instance of twitter api
        notion: (notion Client) Notion client object
    '''
    # verify if the row is not already tweeted
    if ~row.tweeted:

        # defaults
        replyToID, mediaID, tweetText = None, None, None
        errorText, tweetID = '', ''
        tweeted, firstTweet = True, True

        # get thread from notion and the retweet URL if retweet
        thread, retweetURL = row.getTweetThread()

        for tweet in thread:

            # tweet text
            tweetText = tweet['text']

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
                if replyToID:
                    # r = api.request(
                    #     'statuses/update', {'status': tweetText, 'in_reply_to_status_id': replyToID, 'media_ids': mediaID})
                    r = api_v2.create_tweet(
                        text=tweetText, in_reply_to_tweet_id=replyToID, media_ids=media_ids)
                else:
                    # r = api.request(
                    #     'statuses/update', {'status': tweetText, 'attachment_url': retweetURL})
                    print("retweetURLretweetURLretweetURL", retweetURL)
                    username, tweet_id = extract_twitter_info(retweetURL)

                    r = api_v2.create_tweet(
                        text=tweetText, in_reply_to_tweet_id=tweet_id, media_ids=media_ids)
                # update error text
                if r.errors:
                    # 将错误信息记录到 Notion 页面的 "Error Message" 属性中
                    error_messages = [error['message'] for error in r.errors]
                    errorText = '\n'.join(error_messages)
                    errorText = 'UPDATE STATUS FAILURE: ' + errorText
                else:
                    errorText = '\n' + 'UPDATE STATUS SUCCESS'
                # update reply to ID
                replyToID = r.data["id"]  # 不存在的话抛出错误 Keyerror
                # replyToID = data.get("id")
                # thread tweet ID
                if firstTweet:
                    tweetID = replyToID
                    firstTweet = False
            except HTTPException as e:
                tweeted = False
                # 打印错误的堆栈信息
                traceback.print_exc()
                # 获取错误的类型和值
                err_type, err_value = sys.exc_info()[:2]
                print(err_type, err_value)
                errorText = '\n' + 'UPDATE STATUS FAILURE: ' + \
                            str(e.response.json())
                pass

        # update Notion
        updates = {}
        updates['Posted?'] = {"checkbox": tweeted}
        updates['Error Message'] = {
            "rich_text": [{"text": {"content": "twitter error:{}".format(errorText)}}]}
        notion.pages.update(row.pageID, properties=updates)
        print('Updated Notion')

    else:
        print('Already tweeted')
