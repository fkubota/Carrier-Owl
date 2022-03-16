from webdriver_manager.chrome import ChromeDriverManager
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import os
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
from feedparser import FeedParserDict
from string import Template
# setting
warnings.filterwarnings('ignore')


@dataclass
class Result:
    article: FeedParserDict
    title_trans: str
    summary_trans: str
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
        abstract = article['summary']
        score, hit_keywords = calc_score(abstract, keywords)
        if (score != 0) and (score >= score_threshold):
            title_trans = get_translated_text(
                'ja', 'en', article['title'].replace('\n', ' '))
            summary_trans = get_translated_text(
                'ja', 'en', article['summary'].replace('\n', ' '))
            # summary_trans = textwrap.wrap(summary_trans, 40)  # 40行で改行
            # summary_trans = '\n'.join(summary_trans)
            result = Result(
                article=article, title_trans=title_trans, summary_trans=summary_trans, words=hit_keywords, score=score)
            results.append(result)
    return results


def send2app(text: str, slack_id: str, line_token: str) -> None:
    # slack
    if slack_id is not None:
        slack = slackweb.Slack(url=slack_id)
        slack.notify(text=text)

    # line
    if line_token is not None:
        line_notify_api = 'https://notify-api.line.me/api/notify'
        headers = {'Authorization': f'Bearer {line_token}'}
        data = {'message': f'message: {text}'}
        requests.post(line_notify_api, headers=headers, data=data)


def nice_str(obj) -> str:
    if isinstance(obj, list):
        if all(type(elem) is str for elem in obj):
            return ', '.join(obj)
    if type(obj) is str:
        return obj.replace('\n', ' ')
    return str(obj)


def notify(results: list, template: str, slack_id: str, line_token: str) -> None:
    # 通知
    star = '*'*80
    today = datetime.date.today()
    n_articles = len(results)
    text = f'{star}\n \t \t {today}\tnum of articles = {n_articles}\n{star}'
    send2app(text, slack_id, line_token)
    # descending
    for result in sorted(results, reverse=True, key=lambda x: x.score):
        article = result.article
        article_str = {key: nice_str(article[key]) for key in article.keys()}
        title_trans = result.title_trans
        summary_trans = result.summary_trans
        words = nice_str(result.words)
        score = result.score

        text = Template(template).substitute(
            article_str, words=words, score=score, title_trans=title_trans, summary_trans=summary_trans, star=star)

        send2app(text, slack_id, line_token)


def get_translated_text(from_lang: str, to_lang: str, from_text: str) -> str:
    '''
    https://qiita.com/fujino-fpu/items/e94d4ff9e7a5784b2987
    '''

    sleep_time = 1

    # urlencode
    from_text = urllib.parse.quote(from_text)

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

    for i in range(30):
        # 指定時間待つ
        time.sleep(sleep_time)
        html = driver.page_source
        to_text = get_text_from_page_source(html)

        if to_text:
            break

    # ブラウザ停止
    driver.quit()
    return to_text


def get_text_from_page_source(html: str) -> str:
    soup = BeautifulSoup(html, features='lxml')
    target_elem = soup.find(class_="lmt__translations_as_text__text_btn")
    text = target_elem.text
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
    subject = config['subject']
    keywords = config['keywords']
    score_threshold = float(config['score_threshold'])
    default_template = '\n score: `${score}`'\
                       '\n hit keywords: `${words}`'\
                       '\n url: ${arxiv_url}'\
                       '\n title:    ${title_trans}'\
                       '\n abstract:'\
                       '\n \t ${summary_trans}'\
                       '\n ${star}'
    template = config.get('template', default_template)

    day_before_yesterday = datetime.datetime.today() - datetime.timedelta(days=2)
    day_before_yesterday_str = day_before_yesterday.strftime('%Y%m%d')
    # datetime format YYYYMMDDHHMMSS
    arxiv_query = f'({subject}) AND ' \
                  f'submittedDate:' \
                  f'[{day_before_yesterday_str}000000 TO {day_before_yesterday_str}235959]'
    articles = arxiv.query(query=arxiv_query,
                           max_results=1000,
                           sort_by='submittedDate',
                           iterative=False)
    results = search_keyword(articles, keywords, score_threshold)

    slack_id = os.getenv("SLACK_ID") or args.slack_id
    line_token = os.getenv("LINE_TOKEN") or args.line_token
    notify(results, template, slack_id, line_token)


if __name__ == "__main__":
    main()
