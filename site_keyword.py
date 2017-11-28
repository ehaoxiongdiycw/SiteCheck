from gevent import monkey
monkey.patch_all()

from gevent.queue import Queue
from gevent.pool import Pool
from requests.exceptions import SSLError
import csv
import time
import requests
import logging
import re

from config import URLS_FILE, NORMAL_RESULT_FILE, ABNORMAL_RESULT_FILE, KEYWORDS_FILE
from config import MAX_THREAD, TIMEOUT_SECONDE
from config import USER_AGENT


class TXTFile(object):
    def __init__(self, filename):
        self.file = open(filename, 'w')

    def add(self, row):
        if isinstance(row, str) or isinstance(row, bytes):
            self.file.write('{}\n'.format(row))
        else:
            raise Exception(
                'Type Error',
                'Only str or bytes able to add to TXT file.')

    def close(self):
        self.file.close()


class CSVFile(object):
    def __init__(self, filename):
        self.file = open(filename, 'w')
        self.csv_writer = csv.writer(self.file)

    def add(self, row):
        if isinstance(row, list):
            self.csv_writer.writerow(row)
        else:
            raise Exception('Type Error', 'Only list able to add to CSV file.')

    def close(self):
        self.file.close()


def disk_to_queue(urlfile, keywordfile, queue):
    with open(urlfile) as url_file, open(keywordfile) as keyword_file:
        urls = list(url_file)
        keywords = list(keyword_file)
        for url in urls:
            for keyword in keywords:
                queue.put({'keyword': keyword.strip(), 'url': url.strip()})
                logging.info('{}:{} added to Queue.'.format(url.strip(), keyword.strip()))


def queue_to_pool(
        queue,
        pool,
        normal_result_file,
        abnormal_result_file):
    while not queue.empty():
        site_keyword = queue.get()
        pool.spawn(      # add to pool, start now
            fetch_site,
            site_keyword,
            queue,
            normal_result_file,
            abnormal_result_file)
        logging.info('{} added to Pool'.format(site_keyword))


def fetch_site(
        site_keyword,
        normal_result_file,
        abnormal_result_file):
    site = site_keyword['url']
    keyword = site_keyword['keyword']
    site_url = 'https://www.baidu.com/s?wd=site%3A{0}%20{1}'.format(site, keyword)
    headers = {'User-Agent': USER_AGENT}
    start = time.time()
    logging.info('{}:{} starting fetching.'.format(site, keyword))
    try:
        response = requests.get(
            site_url,
            headers=headers,
            verify=False,
            timeout=TIMEOUT_SECONDE,
            allow_redirects=True)
    # queue 中无法添加这个URL，奇怪
    #except SSLError:
    #    queue.put('https://{}'.format(site))
    except Exception as e:
        abnormal_result_file.add(list((site_url, '{}'.format(e.args))))
    else:
        logging.info(
            '{}\tSucess Response\t{}'.format(
                site, time.time() - start))
        pattern = re.compile('<div class="content_none">', re.IGNORECASE)
        match = pattern.search(response.text)
        if match:
            exist = 0
        else:
            exist = 1
        normal_result_file.add(
            list((site, keyword, exist)))


def main():
    logging.basicConfig(
        # filename='concurrent_withPoolAndQueue.log',
        level=logging.INFO)

    queue = Queue(maxsize=10 * MAX_THREAD)
    pool = Pool(size=MAX_THREAD)
    main_pool = Pool(size=2)
    normal_result_file = CSVFile(filename=NORMAL_RESULT_FILE)
    abnormal_result_file = CSVFile(filename=ABNORMAL_RESULT_FILE)

    # first main pool
    main_pool.spawn(disk_to_queue, URLS_FILE, KEYWORDS_FILE, queue)
    # second main pool
    main_pool.spawn(
        queue_to_pool,
        queue,
        pool,
        normal_result_file,
        abnormal_result_file)
    main_pool.join()
    pool.join()

    normal_result_file.close()
    abnormal_result_file.close()

def url_check(url):
    pattern = re.compile(r'(^localhost.*)|(^www\.localhost.*)|(^192\..*)|(^172\..*)|(^10\..*)')
    match = pattern.search(url)
    if match:
        return False
    return True


if __name__ == '__main__':
    start = time.time()
    try:
        main()
    finally:
        logging.info(
            'Total Time consumption: {}.\n'.format(
                time.time() - start))
