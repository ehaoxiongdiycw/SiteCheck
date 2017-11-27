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

from config import URLS_FILE, NORMAL_RESULT_FILE, ABNORMAL_RESULT_FILE, TITLE_FILE
from config import TITLE_REGEX, MAX_THREAD, TIMEOUT_SECONDE


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


def disk_to_queue(filename, queue):
    with open(filename) as f:
        urls = list(f)
        for url in urls:
            queue.put(url.strip())
            logging.info('{} added to Queue.'.format(url.strip()))


def queue_to_pool(
        queue,
        pool,
        normal_result_file,
        abnormal_result_file,
        title_unique_urls_file):
    seen_title = set()
    while not queue.empty():
        site = queue.get()
        pool.spawn(      # add to pool, start now
            fetch_site,
            site,
            queue,
            seen_title,
            normal_result_file,
            abnormal_result_file,
            title_unique_urls_file)
        logging.info('{} added to Pool'.format(site))


def fetch_site(
        site,
        queue,
        seen_title,
        normal_result_file,
        abnormal_result_file,
        title_unique_urls_file):
    if 'http' not in site:
        site_url = 'http://{}'.format(site)
    else:
        site_url = site
    start = time.time()
    logging.info('{} starting fetching.'.format(site))
    try:
        response = requests.get(
            site_url,
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
        pattern = re.compile(TITLE_REGEX, re.IGNORECASE)
        match = pattern.search(response.text)
        if match:
            site_title = match.group(0)
        else:
            site_title = None
        normal_result_file.add(
            list((response.url, response.status_code, site_title)))
        if response.status_code == 200 and site_title not in seen_title:
            title_unique_urls_file.add(response.url)
            seen_title.add(site_title)


def main():
    logging.basicConfig(
        # filename='concurrent_withPoolAndQueue.log',
        level=logging.INFO)

    queue = Queue(maxsize=10 * MAX_THREAD)
    pool = Pool(size=MAX_THREAD)
    main_pool = Pool(size=2)
    normal_result_file = CSVFile(filename=NORMAL_RESULT_FILE)
    abnormal_result_file = CSVFile(filename=ABNORMAL_RESULT_FILE)
    title_unique_urls_file = TXTFile(filename=TITLE_FILE)

    # first main pool
    main_pool.spawn(disk_to_queue, URLS_FILE, queue)
    # second main pool
    main_pool.spawn(
        queue_to_pool,
        queue,
        pool,
        normal_result_file,
        abnormal_result_file,
        title_unique_urls_file)
    main_pool.join()
    pool.join()

    normal_result_file.close()
    abnormal_result_file.close()
    title_unique_urls_file.close()

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
