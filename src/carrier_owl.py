import chromedriver_binary   # これは必ず入れる
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import os
import time
import yaml
import datetime
import numpy as np
import textwrap
from bs4 import BeautifulSoup
import requests
from fastprogress import progress_bar
import slackweb
import warnings
import urllib.parse
from dataclasses import dataclass
import arxiv
# setting
warnings.filterwarnings('ignore')


@dataclass
class Result:
    url: str
    title: str
    abstract: str
    words: list
    score: float = 0.0


def calc_score(abst: str, keywords: dict) -> (float, list):
    sum_score = 0.0
    hit_kwd_list = []

    for word in keywords.keys():
        score = keywords[word]
        if word.lower() in abst.lower():
            sum_score += score
            hit_kwd_list.append(word)
    return sum_score, hit_kwd_list


def search_keyword(_get_article_func, keywords: dict) -> list:
    results = []

    for article in _get_article_func():
        url = article['arxiv_url']
        title = article['title']
        abst = article['summary']
        score, hit_keywords = calc_score(abst, keywords)
        if score != 0:
            title_trans = get_translated_text('ja', 'en', title)
            abstract = abst.replace('\n', '')
            abstract_trans = get_translated_text('ja', 'en', abstract)
            abstract_trans = textwrap.wrap(abstract_trans, 40)  # 40行で改行
            abstract_trans = '\n'.join(abstract_trans)
            result = Result(url=url, title=title_trans, abstract=abstract_trans,
                            score=score, words=hit_keywords)
            results.append(result)
    return results


def send2slack(results: list, slack: slackweb.Slack) -> None:

    # 通知
    star = '*'*120
    today = datetime.date.today()
    text = f'{star}\n \t \t {today}\n{star}'
    slack.notify(text=text)
    # descending
    for result in sorted(results, reverse=True, key=lambda x: x.score):
        url = result.url
        title = result.title
        abstract = result.abstract
        word = result.words
        score = result.score

        text_slack = f'''
                    \n score: `{score}`\n hit keywords: `{word}`\n url: {url}\n title:    {title}\n abstract: \n \t {abstract}\n{star}
                       '''
        slack.notify(text=text_slack)


def get_translated_text(from_lang, to_lang, from_text):
    '''
    https://qiita.com/fujino-fpu/items/e94d4ff9e7a5784b2987
    '''

    sleep_time = 1

    # urlencode
    from_text = urllib.parse.quote(from_text)

    # url作成
    url = 'https://www.deepl.com/translator#' + from_lang + '/' + to_lang + '/' + from_text

    # ヘッドレスモードでブラウザを起動
    options = Options()
    options.add_argument('--headless')

    # ブラウザーを起動
    driver = webdriver.Chrome(options=options)
    driver.get(url)
    driver.implicitly_wait(10)  # 見つからないときは、10秒まで待つ

    for i in range(30):
        # 指定時間待つ
        time.sleep(sleep_time)
        html = driver.page_source
        to_text = get_text_from_page_source(html)

        try_count = i + 1
        if to_text:
            wait_time = sleep_time * try_count
            # アクセス終了
            break

    # ブラウザ停止
    driver.quit()
    return to_text


def get_text_from_page_source(html):
    soup = BeautifulSoup(html, features='lxml')
    target_elem = soup.find(class_="lmt__translations_as_text__text_btn")
    text = target_elem.text
    return text


def get_config():
    file_abs_path = os.path.abspath(__file__)
    file_dir = os.path.dirname(file_abs_path)
    config_path = f'{file_dir}/../config.yaml'
    with open(config_path, 'r') as yml:
        config = yaml.load(yml)
    return config


def main():
    config = get_config()
    slack = slackweb.Slack(url=os.getenv("SLACK_ID"))
    subject = config['subject']
    keywords = config['keywords']
    arxiv_query = f'{subject}'
    get_article_func = arxiv.query(query=arxiv_query,
                                   max_results=1000,
                                   sort_by='submittedDate',
                                   iterative=True)
    results = search_keyword(get_article_func, keywords)
    send2slack(results, slack)


if __name__ == "__main__":
    main()
