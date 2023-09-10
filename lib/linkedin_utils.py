"""
Author: Damon Xiong
Notion to Twitter helper functions
"""

from io import BytesIO
import requests

from PIL import Image
from lib.proxy import disable_proxy, enable_proxy


class LinkedinClient:
    api_version = 'v17.0'

    def __init__(self, access_token, client_id, client_secret, user_id, proxy):
        self.quota_usage = None
        self.access_token = access_token
        self.client_id = client_id
        self.client_secret = client_secret
        self.user_id = user_id
        self.proxy = proxy

        self.content_publishing_limit()

    def exchange_token(self):
        """ exchange access token """
        params = {
            'grant_type': 'fb_exchange_token',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'fb_exchange_token': self.access_token
        }
        if self.proxy is not None:
            enable_proxy(self.proxy.get('http'), self.proxy.get('https'))
        requests.get(f"https://graph.facebook.com/{self.api_version}/oauth/access_token", params=params)
        if self.proxy is not None:
            disable_proxy()
        pass

    def content_publishing_limit(self):
        """ content publishing limit """
        headers = {
            "Authorization": f"Bearer {self.access_token}"
        }
        if self.proxy is not None:
            enable_proxy(self.proxy.get('http'), self.proxy.get('https'))
        response = requests.get(f"https://graph.facebook.com/{self.user_id}/content_publishing_limit", headers=headers)
        if self.proxy is not None:
            disable_proxy()
        print(response.json())
        # 检查响应状态码
        if response.status_code == 200:
            # 请求成功
            data = response.json()
            self.quota_usage = data['data'][0]['quota_usage']
            print("Request successful", self.quota_usage)
            return True
        else:
            # 请求失败
            print("Request failed with status code:", response.status_code)
            return False

    def upload_media(self, image_url, caption):
        headers = {
            "Authorization": f"Bearer {self.access_token}"
        }

        params = {
            'image_url': image_url[0]['external']['url'],
            'caption': caption,
        }
        if self.proxy is not None:
            enable_proxy(self.proxy.get('http'), self.proxy.get('https'))
        response = requests.post(f"https://graph.facebook.com/{self.api_version}/{self.user_id}/media", headers=headers,
                                 params=params)
        if self.proxy is not None:
            disable_proxy()
        print(response.json())
        # 检查响应状态码
        if response.status_code == 200:
            # 请求成功
            data = response.json()
            return data['id']
        else:
            # 请求失败
            print("Request failed with status code:", response.status_code)
            return None

    def media_publish(self, creation_id):
        headers = {
            "Authorization": f"Bearer {self.access_token}"
        }

        params = {
            'creation_id': creation_id,
        }
        if self.proxy is not None:
            enable_proxy(self.proxy.get('http'), self.proxy.get('https'))
        response = requests.post(f"https://graph.facebook.com/{self.api_version}/{self.user_id}/media_publish",
                                 headers=headers,
                                 params=params)
        if self.proxy is not None:
            disable_proxy()

        print(response.json())
        # 检查响应状态码
        if response.status_code == 200:
            # 请求成功
            data = response.json()
            return data['id']
        else:
            # 请求失败
            print("Request failed with status code:", response.status_code)
            return None

    def upload_photo(self, image_url, caption):
        """ upload photo """
        creation_id = self.upload_media(image_url, caption)
        if creation_id is not None:
            media_id = self.media_publish(creation_id)
            if media_id is not None:
                return True
            else:
                return False
        else:
            print("No media uplaod")
            return False

    def post(self, row, notion):
        """
        Post notion row to twitter + prints staus
        Args:
            row: (NotionRow)
            notion: (notion Client) Notion client object
        """
        # verify if the row is not already tweeted
        # get thread from notion and the retweet URL if retweet
        thread, retweet_url = row.get_tweet_thread()

        for tweet in thread:
            # 定义要发送的数据
            data = {
                "text": tweet['text'],
                "images": tweet['images']
            }

            if self.quota_usage < 50:
                res = self.upload_photo(tweet['images'], tweet['text'])

                # 检查响应状态码
                if res:
                    print("Post Instagram Success！")
                    # update Notion
                    notion.update_notion_posted_platform(row, 'instagram')
                else:
                    print("Post Instagram Failed.")
            else:
                print("Rate Limiter", self.quota_usage)


def post_row_to_instagram(row, webhook_url, notion):
    """
    Post notion row to twitter + prints staus
    Args:
        row: (NotionTweetRow)
        webhook_url: instance of zapier url
        notion: (notion Client) Notion client object
    """
    # verify if the row is not already tweeted
    # get thread from notion and the retweet URL if retweet
    thread, retweet_url = row.get_tweet_thread()

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
            notion.update_notion_posted_platform(row, 'instagram')
        else:
            print("请求发送失败。响应状态码：", response.status_code)


def post_row_to_instagram_by_api(row, ins_client, notion):
    """
    Post notion row to instagram by api
    Args:
        row: (NotionTweetRow)
        ins_client: instance of instagram api
        notion: (notion Client) Notion client object
    """

    # get thread from notion and the retweet URL if retweet
    thread, retweet_url = row.get_tweet_thread()

    for tweet in thread:
        # 定义要发送的数据
        paths = []
        for index, media in enumerate(tweet['images']):
            image_url = media
            # 发起 GET 请求获取图片数据
            response = requests.get(image_url)
            # 将图片数据转换为 Pillow 图像对象
            image = Image.open(BytesIO(response.content))
            # 转换为 JPG 格式
            image = image.convert("RGB")
            # 保存为 JPG 格式
            name = "output_image_" + str(index) + '.jpg'
            image.save(name)
            paths.append(name)

        if len(paths) > 1:
            ins_client.album_upload(paths, tweet['text'])
            print("upload album success")
        else:
            ins_client.photo_upload(paths[0], tweet['text'])
            print("upload photo success")

        notion.update_notion_posted_platform(row, 'instagram')
