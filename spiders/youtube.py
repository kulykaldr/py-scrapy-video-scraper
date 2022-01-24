import datetime
import json
import re
import socket
from json import JSONDecodeError

from scrapy.spiders import Spider
from scrapy.loader import ItemLoader

from ..items import VideoScraperItem

import chompjs


class YoutubeSpider(Spider):
    name = 'youtube'
    allowed_domains = ['youtube.com']
    start_urls = ['https://youtube.com/']

    def parse(self, res, **kwargs):
        # Находим на странице https://youtube.com/ все ссылки на видео
        category_links = []
        watch_pattern = r'\"(/watch\?v=.*?)\"'
        videos = re.findall(watch_pattern, res.text)
        category_links.extend(videos)  # Находим ссылки в html json
        channels = []
        channels.extend(re.findall(r'\"(/channel/.*?)\"', res.text))  # Находим ссылки в html json
        channels.extend(re.findall(r'\"(/user/.*?)\"', res.text))  # Находим ссылки в html json
        category_links = [f'{x}/videos' for x in set(channels)]
        yield from res.follow_all(category_links)  # Переходим по ссылкам

        # Находим ссылки на видео в html json
        yield from res.follow_all(videos, callback=self.extract_data)  # собираем данные про видео

    def extract_data(self, res):
        item = ItemLoader(item=VideoScraperItem(), response=res)

        # Находим html json
        script_css = 'script:contains("ytInitialPlayerResponse")::text'
        script_text: str = res.css(script_css).re_first(r'{.+}')

        # Парсим json
        try:
            jss = chompjs.parse_js_object(script_text, unicode_escape=False, json_params={'strict': False})
        except ValueError as err:
            self.log(f'Failed to extract data from {res.url}, error: {err}')
            print(f'Failed to extract data from {res.url}, error: {err}')
            return

        # Вытягиваем данные про видео и записываем в ItemLoader
        contents = jss['contents']['twoColumnWatchNextResults']['results']['results']['contents']
        item.add_value('title', contents[1]['videoPrimaryInfoRenderer']['title']['runs'][0]['text'])
        descriptions = contents[1]['videoSecondaryInfoRenderer']['description']['runs']
        descriptions = [x['text'] for x in descriptions]
        item.add_value('description', ''.join(descriptions))

        owner = jss['contents']['twoColumnWatchNextResults']['results']['results']['contents'][1]['videoSecondaryInfoRenderer']['owner']
        item.add_value('author', owner['videoOwnerRenderer']['title']['runs'][0]['text'])
        item.add_value('avatar', owner['videoOwnerRenderer']['thumbnail']['thumbnails'][-1]['url'])

        videoId = re.search(r'watch\?v=(.*)', res.url).group(1)
        thumbnail = f'https://i.ytimg.com/vi/{videoId}/hqdefault.jpg'
        item.add_value('thumbnail_url', thumbnail)

        item.add_value('categories', jss['data_layer']['video_categories'].split(','))

        dimensions = jss['player']['dimensions']
        item.add_value('video_height', dimensions['height'])
        item.add_value('video_width', dimensions['width'])

        item.add_value('url', res.url)
        item.add_value('project', self.settings.get('BOT_NAME'))
        item.add_value('spider', self.name)
        item.add_value('server', socket.gethostname())
        item.add_value('date', datetime.datetime.now())

        return item.load_item()
