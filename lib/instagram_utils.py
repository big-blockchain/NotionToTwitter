"""
Author: Nandita Bhaskhar
Notion to Twitter helper functions
"""

from io import BytesIO
import requests

from PIL import Image

from lib.notion_utils import update_notion_posted_platform


class InstagramClient:
    def __init__(self, username, password):
        self.username = username
        self.password = password


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
            update_notion_posted_platform(notion, row, 'instagram')
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

        update_notion_posted_platform(notion, row, 'instagram')
