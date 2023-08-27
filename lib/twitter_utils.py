"""
Author: Nandita Bhaskhar
Notion to Twitter helper functions
"""

import os
import re
import requests
import tweepy
from TwitterAPI import TwitterAPI

from lib.notion_utils import update_notion_posted_platform
from rateLimiter.rate_limiter import RateLimiter


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


class TwitterClient:
    def __init__(self, consumer_key, consumer_secret, access_token, access_token_secret, bearer_token):
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.access_token = access_token
        self.access_token_secret = access_token_secret
        self.bearer_token = bearer_token
        self.rate_limter = RateLimiter(max_requests=50, duration=24 * 60 * 60)

        self.api_v1 = TwitterAPI(consumer_key=consumer_key,
                                 consumer_secret=consumer_secret,
                                 access_token_key=access_token,
                                 access_token_secret=access_token_secret
                                 )

        self.api_v2 = tweepy.Client(
            bearer_token=bearer_token,
            consumer_key=consumer_key,
            consumer_secret=consumer_secret,
            access_token=access_token,
            access_token_secret=access_token_secret
        )

    def post_row_to_twitter(self, row, notion):
        """
        Post notion row to twitter + prints staus
        Args:
            row: (NotionTweetRow)
            notion: (notion Client) Notion client object
        """
        # verify if the row is not already tweeted
        if ~row.tweeted:
            # defaults
            reply_to_id, media_id, tweet_text = None, None, None
            tweeted = True

            # get thread from notion and the retweet URL if retweet
            thread, retweet_url = row.get_tweet_thread()

            for tweet in thread:
                # tweet text
                tweet_text = tweet['text']

                # post tweet with a reference to uploaded image as a reply to the replyToID
                if reply_to_id:
                    max_length = 279

                    if len(tweet_text) > max_length:
                        # 使用正则表达式将长文本分割为段落
                        paragraphs = re.split(r'\n', tweet_text)

                        # 分割后的片段列表
                        fragments = []

                        # 当前片段的文本
                        current_fragment_text = ""
                        for paragraph in paragraphs:
                            if len(current_fragment_text + paragraph) <= max_length:
                                current_fragment_text += (paragraph + '\n')
                            else:
                                if len(current_fragment_text) > 0:
                                    fragments.append(current_fragment_text)
                                    current_fragment_text = ""
                                if len(paragraph) <= max_length:
                                    current_fragment_text = (paragraph + '\n')
                                else:
                                    # 使用正则表达式将段落分割为句子
                                    sentences = re.split(r'(?<=[.!?\n])\s+', paragraph)
                                    for sentence in sentences:
                                        # 如果当前片段的文本加上当前句子不超过最大长度，则将句子添加到当前片段的文本中
                                        if len(current_fragment_text + sentence) <= max_length:
                                            current_fragment_text += (sentence + '\n')
                                        # 否则，将当前片段添加到片段列表中，并开始一个新的片段
                                        else:
                                            fragments.append(current_fragment_text)
                                            current_fragment_text = (sentence + '\n')

                                    # 将最后一个片段添加到片段列表中
                                    fragments.append(current_fragment_text)

                        parent_tweet = reply_to_id
                        if not self.rate_limter.is_allowed_for_request_length(len(fragments)):
                            raise Exception("Too many requests. Please try again later.")

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
                                w = self.api_v1.request('media/upload', None, {'media': data})
                                print('UPLOAD MEDIA SUCCESS' if w.status_code ==
                                                                200 else 'UPLOAD MEDIA FAILURE: ' + w.text)
                                if w.status_code == 200:
                                    media_ids.append(str(w.json()['media_id']))
                        else:
                            media_ids = None

                        for tweet_text in fragments:
                            if parent_tweet is None and len(media_ids) > 0:
                                print(len(tweet_text))
                                r = self.api_v2.create_tweet(text=tweet_text, media_ids=media_ids)
                                self.rate_limter.add_allowed_time()
                                parent_tweet = r.data['id']
                            else:
                                print(len(tweet_text))
                                r = self.api_v2.create_tweet(text=tweet_text, in_reply_to_tweet_id=parent_tweet)
                                self.rate_limter.add_allowed_time()
                                parent_tweet = r.data['id']

                            if r.errors:
                                error_messages = [error['message'] for error in r.errors]
                                print('UPDATE STATUS FAILURE: '.join(error_messages))
                            else:
                                print('UPDATE TWITTER STATUS SUCCESS'.join(row.title))
                    else:
                        if self.rate_limter.is_allowed_for_request_length(1):
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
                                    w = self.api_v1.request('media/upload', None, {'media': data})
                                    print('UPLOAD MEDIA SUCCESS' if w.status_code ==
                                                                    200 else 'UPLOAD MEDIA FAILURE: ' + w.text)
                                    if w.status_code == 200:
                                        media_ids.append(str(w.json()['media_id']))
                            else:
                                media_ids = None

                            r = self.api_v2.create_tweet(
                                text=tweet_text, in_reply_to_tweet_id=reply_to_id, media_ids=media_ids)
                            self.rate_limter.add_allowed_time()

                            if r.errors:
                                error_messages = [error['message'] for error in r.errors]
                                print('UPDATE STATUS FAILURE: '.join(error_messages))
                            else:
                                print('UPDATE TWITTER STATUS SUCCESS'.join(row.title))
                        else:
                            raise Exception("Too many requests. Please try again later.")
                else:
                    print("retweetURLretweetURLretweetURL", retweet_url)
                    username, tweet_id = extract_twitter_info(retweet_url)
                    max_length = 279
                    if len(tweet_text) > max_length:
                        # 使用正则表达式将长文本分割为段落
                        paragraphs = re.split(r'\n', tweet_text)

                        # 分割后的片段列表
                        fragments = []

                        # 当前片段的文本
                        current_fragment_text = ""
                        for paragraph in paragraphs:
                            if len(current_fragment_text + paragraph) <= max_length:
                                current_fragment_text += (paragraph + '\n')
                            else:
                                if len(current_fragment_text) > 0:
                                    fragments.append(current_fragment_text)
                                    current_fragment_text = ""
                                if len(paragraph) <= max_length:
                                    current_fragment_text = (paragraph + '\n')
                                else:
                                    # 使用正则表达式将段落分割为句子
                                    sentences = re.split(r'(?<=[.!?\n])\s+', paragraph)
                                    for sentence in sentences:
                                        # 如果当前片段的文本加上当前句子不超过最大长度，则将句子添加到当前片段的文本中
                                        if len(current_fragment_text + sentence) <= max_length:
                                            current_fragment_text += (sentence + '\n')
                                        # 否则，将当前片段添加到片段列表中，并开始一个新的片段
                                        else:
                                            fragments.append(current_fragment_text)
                                            current_fragment_text = (sentence + '\n')

                                    # 将最后一个片段添加到片段列表中
                                    fragments.append(current_fragment_text)

                        parent_tweet = tweet_id
                        if not self.rate_limter.is_allowed_for_request_length(len(fragments)):
                            raise Exception("Too many requests. Please try again later.")

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
                                w = self.api_v1.request('media/upload', None, {'media': data})
                                print('UPLOAD MEDIA SUCCESS' if w.status_code ==
                                                                200 else 'UPLOAD MEDIA FAILURE: ' + w.text)
                                if w.status_code == 200:
                                    media_ids.append(str(w.json()['media_id']))
                        else:
                            media_ids = None

                        for tweet_text in fragments:
                            if parent_tweet is None and len(media_ids) > 0:
                                print(len(tweet_text))
                                r = self.api_v2.create_tweet(text=tweet_text, media_ids=media_ids)
                                self.rate_limter.add_allowed_time()
                                parent_tweet = r.data['id']
                            else:
                                print(len(tweet_text))
                                r = self.api_v2.create_tweet(text=tweet_text, in_reply_to_tweet_id=parent_tweet)
                                self.rate_limter.add_allowed_time()
                                parent_tweet = r.data['id']

                            if r.errors:
                                error_messages = [error['message'] for error in r.errors]
                                print('UPDATE STATUS FAILURE: '.join(error_messages))
                            else:
                                print('UPDATE TWITTER STATUS SUCCESS'.join(row.title))
                    else:
                        if self.rate_limter.is_allowed():
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
                                    w = self.api_v1.request('media/upload', None, {'media': data})
                                    print('UPLOAD MEDIA SUCCESS' if w.status_code ==
                                                                    200 else 'UPLOAD MEDIA FAILURE: ' + w.text)
                                    if w.status_code == 200:
                                        media_ids.append(str(w.json()['media_id']))
                            else:
                                media_ids = None

                            r = self.api_v2.create_tweet(
                                text=tweet_text, in_reply_to_tweet_id=tweet_id, media_ids=media_ids)
                            self.rate_limter.add_allowed_time()

                            if r.errors:
                                error_messages = [error['message'] for error in r.errors]
                                print('UPDATE STATUS FAILURE: '.join(error_messages))
                            else:
                                print('UPDATE TWITTER STATUS SUCCESS'.join(row.title))
                        else:
                            raise Exception("Too many requests. Please try again later.")

                # update reply to ID
                reply_to_id = r.data["id"]  # 不存在的话抛出错误 Keyerror

            # update Notion
            if tweeted:
                update_notion_posted_platform(notion, row, 'twitter')

        else:
            print('Already tweeted')
