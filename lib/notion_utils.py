"""
Author: Damon Xiong
Notion to Twitter helper functions
"""

import time
import arrow
from globalStore import constants
from notion_client import Client


class NotionClient:
    def __init__(self, token, db_id):
        self.db_id = db_id
        self.token = token

        self.notion_client = Client(auth=token)
        self.all_unpost_rows = self.get_all_unpost_rows()
        self.filtered_rows = self.filter_rows_to_be_posted_based_on_date()

    def get_all_unpost_rows(self):
        """
        Gets all rows (pages) that are unposted from a notion database using a notion client
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
                    query = self.notion_client.databases.query(
                        **{
                            "database_id": self.db_id,
                            "filter": {"property": "Posted?", "checkbox": {"equals": False}},
                        }
                    )
                except Exception as e:
                    print(str(e))
                    print('Sleeping to avoid rate limit')
                    time.sleep(30)
                    query = self.notion_client.databases.query(
                        **{
                            "database_id": self.db_id,
                            "filter": {"property": "Posted?", "checkbox": {"equals": False}},
                        }
                    )

            else:
                try:
                    query = self.notion_client.databases.query(
                        **{
                            "database_id": self.db_id,
                            "start_cursor": next_cursor,
                            "filter": {"property": "Posted?", "checkbox": {"equals": False}},
                        }
                    )
                except Exception as e:
                    print(str(e))
                    print('Sleeping to avoid rate limit')
                    time.sleep(30)
                    query = self.notion_client.databases.query(
                        **{
                            "database_id": self.db_id,
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

    def filter_rows_to_be_posted_based_on_date(self):
        """
        Filters rows (notion pages) from a list of rows whose 'Post Date' matches the given datetime
        Args:
        Returns:
            filteredRows: (list of notion rows)
        """
        # get today's date
        datetime = arrow.now().to('utc').date()
        print(datetime)
        arrow_time = arrow.get(datetime)

        filtered_rows = [item for item in self.all_unpost_rows if 'Post Date' in item['properties']
                         and item['properties']['Post Date']['date'] is not None
                         and arrow.get(
            item['properties']['Post Date']['date']['start']).datetime <= arrow_time.datetime]

        print(str(len(filtered_rows)) + ' filtered rows for today')

        return filtered_rows

    def update_notion_posted_platform(self, row, platform):
        row.posted_platform.append(constants.SUPPORT_PLATFORM.get(platform))
        posted_platform = [{'name': obj} for obj in row.posted_platform]
        updates = {'Posted Platform': {
            "multi_select": posted_platform}}
        self.notion_client.pages.update(row.pageID, properties=updates)
        print('Updated Notion')

    def update_notion_checked_posted(self, row):
        updates = {'Posted?': {"checkbox": True}}
        self.notion_client.pages.update(row.pageID, properties=updates)


class NotionRow:
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
        self.platform = [obj["name"] for obj in row['properties']['Social Media Platform']['multi_select']]
        self.posted_platform = [obj["name"] for obj in row['properties']['Posted Platform']['multi_select']]

        self.title = row['properties']['Title']['title'][0]['text']['content'] if row['properties']['Title'][
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

        self.medias = row['properties']['Medias Link']['rich_text'][0]['text']['content']
        if len(row['properties']['Medias Link']['rich_text']) > 0:
            self.medias = [item for item in
                           row['properties']['Medias Link']['rich_text'][0]['text']['content'].split(";") if item != '']
        else:
            self.medias = []

        self.rawContent = notion.notion_client.blocks.children.list(self.pageID)
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
            except Exception as e:
                print(str(e))
                continue
            tweet = {'text': para, 'images': self.medias}

            if para != '':
                tweet_thread.append(tweet)

        return tweet_thread, self.retweetURL
