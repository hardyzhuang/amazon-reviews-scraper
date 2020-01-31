import errno
from time import sleep

import string
import csv 
import logging
import os
import re
import requests
from bs4 import BeautifulSoup

from banned_exception import BannedException
from constants import AMAZON_BASE_URL

OUTPUT_DIR = 'comments'

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise

def get_reviews_csv_filename(product_title, product_id):
    # remove the punctuations and spaces from the product tile, they are incompatible to file system
    replace_dict = str.maketrans(string.punctuation, '_'*len(string.punctuation))
    replace_dict.update(str.maketrans(' ','_'))  # replace space
    product_title = product_title.translate(replace_dict)

    # limit the file name to 64 chars
    filename = os.path.join(OUTPUT_DIR, '{0:1.64s}-{1}.csv'.format(product_title, product_id))
    exist = os.path.isfile(filename)
    return filename, exist


def persist_comment_to_disk_in_csv(review):
    if len(review) == 0:
        return False
    product_id = review['product_id']
    product_title = review['product_title']
    output_filename, exist = get_reviews_csv_filename(product_title, product_id)
    mkdir_p(OUTPUT_DIR)
    
    with open(output_filename, 'a+', encoding='utf-8', newline='') as fp:
        fieldnames = ['Title', 'Comment', 'Rating', 'Date', 'Helpful', 'author_url', 'review_url']
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        if not(exist):
            writer.writeheader()
            tableTitle = "{:50}\t{:20}"
        writer.writerow({'Title': review['title'], 
                        'Comment': review['body'], 
                        'Rating': review['rating'], 
                        'Date': review['review_date'], 
                        'Helpful': review['helpful'],
                        'author_url': review['author_url'], 
                        'review_url': review['review_url'] })
    return True

def extract_product_id(link_from_main_page):
    p_id = -1
    tags = ['/dp/', '/gp/product/']
    for tag in tags:
        try:
            p_id = link_from_main_page[link_from_main_page.index(tag) + len(tag):].split('/')[0]
        except:
            pass
    m = re.match('[A-Z0-9]{10}', p_id)
    if m:
        return m.group()
    else:
        return None


def get_soup(url):
    if AMAZON_BASE_URL not in url:
        url = AMAZON_BASE_URL + url
    nap_time_sec = 1
    logging.debug('Script is going to sleep for {} (Amazon throttling). ZZZzzzZZZzz.'.format(nap_time_sec))
    sleep(nap_time_sec)
    header = {
        # 'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/43.0.2357.134 Safari/537.36'
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.74 Safari/537.36 Edg/79.0.309.43'
    }
    logging.debug('-> to Amazon : {}'.format(url))
    out = requests.get(url, headers=header)
    assert out.status_code == 200
    soup = BeautifulSoup(out.content, 'lxml')
    if 'captcha' in str(soup):
        raise BannedException('Your bot has been detected. Please wait a while.')
    return soup
