from webdriver_manager.chrome import ChromeDriverManager
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import os
import re
import time
import yaml
import datetime
import slackweb
import argparse
import textwrap
from bs4 import BeautifulSoup
import warnings
import urllib.parse
from dataclasses import dataclass
import arxiv
import requests
# setting
warnings.filterwarnings('ignore')


@dataclass
class Result:
    url: str
    title: str
    en_title: str
    abstract: str
    en_abstract: str
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


def search_keyword(
        articles: list, keywords: dict, score_threshold: float
        ) -> list:
    results = []

    for article in articles:
        url = article['arxiv_url']
        title = article['title']
        abstract = article['summary']
        score, hit_keywords = calc_score(abstract, keywords)
        if score >= score_threshold:
            title = title.replace('\n', ' ')
            title_trans = get_translated_text('ja', 'en', title)
            abstract = abstract.replace('\n', ' ')
            abstract_trans = get_translated_text('ja', 'en', abstract)
#             abstract_trans = textwrap.wrap(abstract_trans, 40)  # 40行で改行
#             abstract_trans = '\n'.join(abstract_trans)
            result = Result(
                    url=url, title=title_trans, en_title=title, abstract=abstract_trans, en_abstract=abstract,
                    score=score, words=hit_keywords)
            results.append(result)
    return results


def mask(labels, text):
    def _make_mask(ltx_text):
        raw_ltx = ltx_text.group(0)
        label = f'(L{len(labels) + 1:04})'
        labels[label] = raw_ltx
        return label

    text = re.sub(r'\$([^\$]+)\$', _make_mask, text)
    return text

def unmask(labels, text):
    for mask, raw in labels.items():
        text = text.replace(mask, raw)
    return text


def send2app(text: str, slack_id: str, line_token: str) -> None:
    # slack
    if slack_id is not None:
        slack = slackweb.Slack(url=slack_id)
        slack.notify(text=text, mrkdwn='false')

    # line
    if line_token is not None:
        line_notify_api = 'https://notify-api.line.me/api/notify'
        headers = {'Authorization': f'Bearer {line_token}'}
        data = {'message': f'message: {text}'}
        requests.post(line_notify_api, headers=headers, data=data)


def notify(results: list, slack_id: str, line_token: str) -> None:
    # 通知
    star = '*'*80
    
    today = datetime.datetime.today()
    deadline = today - datetime.timedelta(days=1)
    previous_deadline = today - datetime.timedelta(days=2)
    if today.weekday()==0:  # announce data is Monday
        deadline = deadline - datetime.timedelta(days=2)
        previous_deadline = previous_deadline - datetime.timedelta(days=2)
    if today.weekday()==1:  # announce data is Tuesday
        previous_deadline = previous_deadline - datetime.timedelta(days=2)
    deadline_str = deadline.strftime('%Y/%m/%d')
    previous_deadline_str = previous_deadline.strftime('%Y/%m/%d')
    day_range = f'{previous_deadline_str} 18:00:00 〜 {deadline_str} 18:00:00 UTC'
    
    n_articles = len(results)
    text = f'{star}\n \t \t {day_range}\tnum of articles = {n_articles}\n{star}'
    send2app(text, slack_id, line_token)
    # descending
    for result in sorted(results, reverse=True, key=lambda x: x.score):
        url = result.url
        title = result.title
        en_title = result.en_title
        abstract = result.abstract
        en_abstract = result.en_abstract
        word = result.words
        score = result.score
        
        title = title.replace('$', ' ')
        abstract = abstract.replace('$', ' ')
        en_abstract = re.sub(r' *([_\*~]) *', r'\1', en_abstract)
        en_abstract = en_abstract.replace("`", "'")
        abstract = re.sub(r' *([_\*~]) *', r'\1', abstract)
        abstract = abstract.replace("`", "'")
#         abstract = '```\t' + abstract + '```'

        text = f'\n Title:\t{title}'\
               f'\n English Title:\t{en_title}'\
               f'\n URL: {url}'\
               f'\n Abstract:'\
               f'\n {abstract}'\
               f'\n English abstract:'\
               f'\n \t {en_abstract}'\
               f'\n {star}'

        send2app(text, slack_id, line_token)


def get_translated_text(from_lang: str, to_lang: str, from_text: str) -> str:
    '''
    https://qiita.com/fujino-fpu/items/e94d4ff9e7a5784b2987
    '''

    sleep_time = 1
    
    # mask latex mathline
    labels = {}
    print(repr(from_text))
    from_text = mask(labels, from_text)

    # urlencode
    from_text = urllib.parse.quote(from_text, safe='')
    from_text = from_text.replace('%2F', '%5C%2F')
    

    # url作成
    url = 'https://www.deepl.com/translator#' \
        + from_lang + '/' + to_lang + '/' + from_text

    # ヘッドレスモードでブラウザを起動
    options = Options()
    options.add_argument('--headless')

    # ブラウザーを起動
    driver = webdriver.Chrome(ChromeDriverManager().install(), options=options)
    driver.get(url)
    driver.implicitly_wait(10)  # 見つからないときは、10秒まで待つ

    for i in range(50):
        # 指定時間待つ
        time.sleep(sleep_time)
        html = driver.page_source
        to_text = get_text_from_page_source(html)

        if to_text:
            break
    if to_text is None:
        to_text = 'Sorry, I timed out...>_<'

    # ブラウザ停止
    driver.quit()
    
    # unmask latex mathline
    to_text = to_text.replace('（', '(').replace('）', ')')  # to prevent from change label by deepL
    to_text = unmask(labels, to_text)

    return to_text


def get_text_from_page_source(html: str) -> str:
    soup = BeautifulSoup(html, features='lxml')
    target_elem = soup.find(class_="lmt__translations_as_text__text_btn")
    text = target_elem.text
    text = ' '.join(text.split())
    return text


def get_config() -> dict:
    file_abs_path = os.path.abspath(__file__)
    file_dir = os.path.dirname(file_abs_path)
    config_path = f'{file_dir}/../config.yaml'
    with open(config_path, 'r') as yml:
        config = yaml.load(yml)
    return config


def main():
    # debug用
    parser = argparse.ArgumentParser()
    parser.add_argument('--slack_id', default=None)
    parser.add_argument('--line_token', default=None)
    args = parser.parse_args()

    config = get_config()
    channels = config['channels']
    score_threshold = float(config['score_threshold'])
    
    today = datetime.datetime.today() 
    deadline = today - datetime.timedelta(days=1)
    previous_deadline = today - datetime.timedelta(days=2)
    if today.weekday()==0:  # announce data is Monday
        deadline = deadline - datetime.timedelta(days=2)
        previous_deadline = previous_deadline - datetime.timedelta(days=2)
    if today.weekday()==1:  # announce data is Tuesday
        previous_deadline = previous_deadline - datetime.timedelta(days=2)
    deadline_str = deadline.strftime('%Y%m%d')
    previous_deadline_str = previous_deadline.strftime('%Y%m%d')
    
    for channel_name, channel_config in channels.items():
        subject = channel_config['subject']
        keywords = channel_config['keywords']
        # datetime format YYYYMMDDHHMMSS
        arxiv_query = f'({subject}) AND ' \
                      f'submittedDate:' \
                      f'[{previous_deadline_str}180000 TO {deadline_str}175959]'
        articles = arxiv.query(query=arxiv_query,
                               max_results=1000,
                               sort_by='submittedDate',
                               iterative=False)
        results = search_keyword(articles, keywords, score_threshold)
#         # debug
#         for key, val in os.environ.items():
#             print('{}: {}'.format(key, val))
           
        slack_id = os.getenv("SLACK_ID_"+channel_name)
#         slack_id = os.getenv("SLACK_ID") or args.slack_id
        line_token = os.getenv("LINE_TOKEN") or args.line_token
        notify(results, slack_id, line_token)
        break


if __name__ == "__main__":
    main()
