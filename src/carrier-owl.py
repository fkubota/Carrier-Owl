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

# setting
warnings.filterwarnings('ignore')


def get_articles_info(subject):
    weekday_dict = {0: 'Mon', 1: 'Tue', 2: 'Wed', 3: 'Thu',
                  4: 'Fri', 5: 'Sat', 6: 'Sun'}
    url = f'https://arxiv.org/list/{subject}/pastweek?show=100000'
    response = requests.get(url)
    html = response.text
    year = datetime.date.today().year

    # いつの論文データを取得するか
    bs = BeautifulSoup(html)
    h3 = bs.find_all('h3')
    wd = weekday_dict[datetime.datetime.today().weekday()]
    day = datetime.datetime.today().day
    today = f'{wd}, {day}'

    # 今日、新しい論文が出てるかどうか(土日とか休みみたい)
    if today in h3[0].text:
        idx = 2
    else:
        idx = 1
    articles_html = html.split(f'{year}</h3>')[idx]   # <--------- 要注意

    # 論文それぞれのurlを取得
    bs = BeautifulSoup(articles_html)
    id_list = bs.find_all(class_='list-identifier')
    return id_list


def serch_keywords(id_list, keywords_dict):
    urls = []
    titles = []
    abstracts = []
    words = []
    scores = []
    for id_ in progress_bar(id_list):
        a = id_.find('a')
        _url = a.get('href')
        url = 'https://arxiv.org'+_url

        response = requests.get(url)
        html = response.text

        bs = BeautifulSoup(html)
        title = bs.find('meta', attrs={'property': 'og:title'})['content']
        abstract = bs.find(
                'meta',
                attrs={'property': 'og:description'})['content']

        sum_score = 0
        hit_kwd_list = []

        for word in keywords_dict.keys():
            score = keywords_dict[word]
            if word.lower() in abstract.lower():  # 全部小文字にすれば、大文字少文字区別しなくていい
                sum_score += score
                hit_kwd_list.append(word)
        if sum_score != 0:
            title_trans = get_translated_text('ja', 'en', title)
            abstract = abstract.replace('\n', '')
            abstract_trans = get_translated_text('ja', 'en', abstract)
            abstract_trans = textwrap.wrap(abstract_trans, 40)  # 40行で改行
            abstract_trans = '\n'.join(abstract_trans)

            urls.append(url)
            titles.append(title_trans)
            abstracts.append(abstract_trans)
            words.append(hit_kwd_list)
            scores.append(sum_score)

    results = [urls, titles, abstracts, words, scores]

    return results


def send2slack(results, slack):
    urls = results[0]
    titles = results[1]
    abstracts = results[2]
    words = results[3]
    scores = results[4]

    # rank
    idxs_sort = np.argsort(scores)
    idxs_sort = idxs_sort[::-1]

    # 通知
    star = '*'*120
    today = datetime.date.today()
    text = f'{star}\n \t \t {today}\n{star}'
    slack.notify(text=text)
    for i in idxs_sort:
        url = urls[i]
        title = titles[i]
        abstract = abstracts[i]
        word = words[i]
        score = scores[i]

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
    id_list = get_articles_info(config['subject'])
    results = serch_keywords(id_list, config['keywords'])
    send2slack(results, slack)


if __name__ == "__main__":
    main()
