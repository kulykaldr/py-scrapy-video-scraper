# Define here the models for your scraped items
#
# See documentation in:
# https://docs.org/en/latest/topics/items.html

from scrapy.item import Item, Field


class VideoScraperItem(Item):
    # define the fields for your item here like:
    title = Field()
    description = Field()
    author = Field()
    avatar = Field()

    video_height = Field()
    video_width = Field()

    thumbnail_url = Field()

    categories = Field()

    url = Field()
    project = Field()
    spider = Field()
    server = Field()
    date = Field()
