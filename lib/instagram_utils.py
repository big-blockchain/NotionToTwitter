"""
Author: Damon Xiong
Notion to Twitter helper functions
"""

import requests


class InstagramClient:
    api_version = 'v17.0'

    def __init__(self, access_token, client_id, client_secret, user_id):
        self.quota_usage = None
        self.access_token = access_token
        self.client_id = client_id
        self.client_secret = client_secret
        self.user_id = user_id
        self.content_publishing_limit()

    def exchange_token(self):
        """ exchange access token """
        params = {
            'grant_type': 'fb_exchange_token',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'fb_exchange_token': self.access_token
        }
        requests.get(f"https://graph.facebook.com/{self.api_version}/oauth/access_token", params=params)
        pass

    def content_publishing_limit(self):
        """ content publishing limit """
        headers = {
            "Authorization": f"Bearer {self.access_token}"
        }
        response = requests.get(f"https://graph.facebook.com/{self.user_id}/content_publishing_limit", headers=headers)
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
            'image_url': image_url,
            'caption': caption,
        }

        response = requests.post(f"https://graph.facebook.com/{self.api_version}/{self.user_id}/media", headers=headers,
                                 params=params)
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
        response = requests.post(f"https://graph.facebook.com/{self.api_version}/{self.user_id}/media_publish",
                                 headers=headers,
                                 params=params)
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