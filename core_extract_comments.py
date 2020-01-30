import argparse
import logging
import math
import re
import textwrap
import string

from constants import AMAZON_BASE_URL, PREDEFINED_PRODUCT_ID
from core_utils import get_soup, persist_comment_to_disk, persist_comment_to_disk_in_csv

# https://www.amazon.co.jp/product-reviews/B00Z16VF3E/ref=cm_cr_arp_d_paging_btm_1?ie=UTF8&reviewerType=all_reviews&showViewpoints=1&sortBy=helpful&pageNumber=1

def get_product_reviews_url(item_id, page_number=None):
    if not page_number:
        page_number = 1
    return AMAZON_BASE_URL + '/product-reviews/{}/ref=' \
                             'cm_cr_arp_d_paging_btm_1?ie=UTF8&reviewerType=all_reviews' \
                             '&showViewpoints=1&sortBy=helpful&pageNumber={}'.format(
        item_id, page_number)


def get_comments_based_on_keyword(search):
    logging.info('SEARCH = {}'.format(search))
    url = AMAZON_BASE_URL + '/s/ref=nb_sb_noss_2?url=search-alias%3Daps&field-keywords=' + \
          search + '&rh=i%3Aaps%2Ck%3A' + search
    soup = get_soup(url)

    product_ids = [div.attrs['data-asin'] for div in soup.find_all('div') if 'data-index' in div.attrs]
    logging.info('Found {} items.'.format(len(product_ids)))
    for product_id in product_ids:
        logging.info('product_id is {}.'.format(product_id))
        reviews = get_comments_with_product_id(product_id)
        logging.info('Fetched {} reviews.'.format(len(reviews)))
        persist_comment_to_disk(reviews)


def get_comments_with_product_id(product_id, skip_comment):
    reviews = list()
    if product_id is None:
        return reviews
    if not re.match('^[A-Z0-9]{10}$', product_id):
        return reviews

    product_reviews_link = get_product_reviews_url(product_id)
    so = get_soup(product_reviews_link)

    product_title = so.find(attrs = {'data-hook': 'product-link'})
    if product_title is None:
        product_title = 'unknown'
    else:
        product_title = product_title.text
    logging.info('product title: {}'.format(product_title))

    max_page_number = so.find(attrs={'data-hook': 'total-review-count'})
    if max_page_number is None:
        return reviews
    # print(max_page_number.text)
    max_page_number = ''.join([el for el in max_page_number.text if el.isdigit()])
    # print(max_page_number)
    max_page_number = int(max_page_number) if max_page_number else 1
    skip_comment = skip_comment if skip_comment < max_page_number else 1

    max_page_number *= 0.1  # displaying 10 results per page. So if 663 results then ~66 pages.
    skip_comment *=0.1
    max_page_number = math.ceil(max_page_number)
    min_page_number = math.ceil(skip_comment)

    for page_number in range(min_page_number, max_page_number + 1):
        logging.info('{:<10s}      {:2.1f}%   page {} of {}'.format(
                        ('*'*math.floor(page_number/max_page_number*10)).ljust(10,'.'), 
                        page_number/max_page_number*100,
                        page_number, max_page_number)
                    )
        if page_number > 1:
            product_reviews_link = get_product_reviews_url(product_id, page_number)
            so = get_soup(product_reviews_link)

        cr_review_list_so = so.find(id='cm_cr-review_list')

        if cr_review_list_so is None:
            logging.info('No reviews for this item.')
            break

        reviews_list = cr_review_list_so.find_all('div', {'data-hook': 'review'})

        if len(reviews_list) == 0:
            logging.info('No more reviews to unstack.')
            break

        for review in reviews_list:
            rating = review.find(attrs={'data-hook': 'review-star-rating'}).attrs['class'][2].split('-')[-1].strip()
            body = review.find(attrs={'data-hook': 'review-body'}).text.strip()
            title = review.find(attrs={'data-hook': 'review-title'}).text.strip()
            author_url = review.find(attrs={'data-hook': 'genome-widget'}).find('a', href=True)
            review_url = review.find(attrs={'data-hook': 'review-title'}).attrs['href']
            review_date = review.find(attrs={'data-hook': 'review-date'}).text.strip()
            if author_url:
                author_url = author_url['href'].strip()
            try:
                helpful = review.find(attrs={'data-hook': 'helpful-vote-statement'}).text.strip()
                helpful = helpful.strip().split(' ')[0]
            except:
                # logging.warning('Could not find any helpful-vote-statement tag.')
                helpful = '0'

            print( '{:<20s}'.format(review_date if review_date else '--/--/----') + \
                    '\tRating:' + rating + \
                    '\t ' + title)

            reviews.append({'title': title,
                            'rating': rating,
                            'body': body,
                            'helpful': helpful,
                            'product_id': product_id,
                            'author_url': author_url,
                            'review_url': review_url,
                            'review_date': review_date
                           })
                           
            review_row = {  'title': title,
                            'rating': rating,
                            'body': body,
                            'helpful': helpful,
                            'product_id': product_id,
                            'author_url': author_url,
                            'review_url': review_url,
                            'review_date': review_date,
                            'product_title': product_title
                        }
            persist_comment_to_disk_in_csv(review_row)
    return reviews

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    parser = argparse.ArgumentParser()
    parser.add_argument('-pid', '--product_id')
    parser.add_argument('-s', '--skip')
    args = parser.parse_args()
    input_product_id = args.product_id
    input_skip_comment = args.skip
    product_id = input_product_id if input_product_id else PREDEFINED_PRODUCT_ID
    skip_comment = int(input_skip_comment) if input_skip_comment else 0
    logging.info('Product ID:{:>20s} skip {} comments'.format(product_id, skip_comment))

    _reviews = get_comments_with_product_id(product_id, skip_comment)
    
    persist_comment_to_disk(_reviews)
