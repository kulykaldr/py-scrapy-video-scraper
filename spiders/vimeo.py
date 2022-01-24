import datetime
import json
import re
import socket
from json import JSONDecodeError

from scrapy.spiders import Spider
from scrapy.loader import ItemLoader

from ..items import VideoScraperItem

import chompjs


class VimeoSpider(Spider):
    name = 'vimeo'
    allowed_domains = ['vimeo.com']
    start_urls = ['https://vimeo.com/categories/']

    def parse(self, res, **kwargs):
        # Находим на странице https://vimeo.com/categories/ все ссылки на подкатегории
        category_links = []
        category_links.extend(res.xpath('//a[contains(@href, "/categories/")]/@href').getall()) # находим ссылки на странице
        category_links.extend(re.findall(r'\"(\\/categories\\/.*?)\"', res.text)) # Находим ссылки в html json
        category_links = [x.replace('\\', '') for x in category_links] # Очищаем ссылки с json от лишних слешей
        yield from res.follow_all(category_links) # Переходим по ссылкам

        # Находим ссылки на видео в html json
        item_links = re.findall(r'\"(\\/\d+)\"', res.text)
        item_links = [x.replace('\\', '') for x in item_links]

        yield from res.follow_all(item_links, callback=self.extract_data) # собираем данные про видео

    def extract_data(self, res):
        item = ItemLoader(item=VideoScraperItem(), response=res)

        # Находим html json
        script_css = 'script:contains("window.vimeo.clip_page_config")::text'
        script_text: str = res.css(script_css).re_first(r'{.+}')

        # Парсим json
        try:
            jss = chompjs.parse_js_object(script_text, unicode_escape=False, json_params={'strict': False})
        except ValueError as err:
            self.log(f'Failed to extract data from {res.url}, error: {err}')
            print(f'Failed to extract data from {res.url}, error: {err}')
            return

        # Вытягиваем данные про видео и записываем в ItemLoader
        clip = jss['clip']
        item.add_value('title', clip['title'])
        item.add_value('description', clip['description'])

        owner = jss['owner']
        item.add_value('author', owner['display_name'])
        item.add_value('avatar', owner['portrait']['src_2x'])

        thumbnail = jss['thumbnail']
        item.add_value('thumbnail_url', thumbnail['src_2x'])

        item.add_value('categories', jss['data_layer']['video_categories'].split(','))

        item.add_value('url', res.url)
        item.add_value('project', self.settings.get('BOT_NAME'))
        item.add_value('spider', self.name)
        item.add_value('server', socket.gethostname())
        item.add_value('date', datetime.datetime.now())

        dimensions = jss['player']['dimensions']
        item.add_value('video_height', dimensions['height'])
        item.add_value('video_width', dimensions['width'])

        return item.load_item()




