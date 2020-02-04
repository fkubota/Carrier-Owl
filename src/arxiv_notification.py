import ast
import datetime
import numpy as np
import textwrap
from bs4 import BeautifulSoup
import requests
from fastprogress import progress_bar
from googletrans import Translator
import slackweb
import warnings

# setting
warnings.filterwarnings('ignore')
weekday_dict = {0: 'Mon', 1: 'Tue', 2: 'Wed', 3: 'Thu',
                4: 'Fri', 5: 'Sat', 6: 'Sun'}
with open('slack_id.txt') as f:
    slack_id = f.read()
slack = slackweb.Slack(url=slack_id)
keywords_path = '/home/fkubota/Git/arxiv_notification/data/keywords.txt'


def get_articles_info():
    url = 'https://arxiv.org/list/cs/pastweek?show=100000'
    response = requests.get(url)
    html = response.text

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
    articles_html = html.split('2020</h3>')[idx]   # <--------- 要注意

    # 論文それぞれのurlを取得
    bs = BeautifulSoup(articles_html)
    id_list = bs.find_all(class_='list-identifier')
    return id_list


def serch_keywords(id_list):
    urls = []
    titles    = []
    abstracts = []
    words     = []
    scores    = []
    for id_ in progress_bar(id_list):
        a = id_.find('a')
        _url = a.get('href')
        url = 'https://arxiv.org'+_url

        response = requests.get(url)
        html = response.text

        bs = BeautifulSoup(html)
        title    = bs.find('meta', attrs={'property': 'og:title'})['content']
        abstract = bs.find('meta', attrs={'property': 'og:description'})['content']

        sum_score = 0
        hit_kwd_list = []

        # serch
        f = open(keywords_path)
        keywords_list = f.readlines() # 1行毎にファイル終端まで全て読む(改行文字も含まれる)
        f.close()
        for line in keywords_list:
            keywords_dict = ast.literal_eval(line)
            word = keywords_dict['word']
            score = keywords_dict['score']
            if word.lower() in abstract.lower(): # 全部小文字にすれば、大文字少文字区別しなくていい
                sum_score += score
                hit_kwd_list.append(word)
        if sum_score != 0:
            translator = Translator()
            title_trans = translator.translate(title, dest='ja', src='en').text
            abstract_trans = translator.translate(abstract.replace("\n",""), dest='ja', src='en').text
            abstract_trans = textwrap.wrap(abstract_trans, 40)  # 40行で改行
            abstract_trans = '\n'.join(abstract_trans)

            urls.append(url)
            titles.append(title_trans)
            abstracts.append(abstract_trans)
            words.append(hit_kwd_list)
            scores.append(sum_score)

    results = [urls, titles, abstracts, words, scores]

    return results

def send2slack(results):
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
                       \n<!here> \n score: `{score}`\n hit keywords: `{word}`\n url: {url}\n title:    {title}\n abstract: \n \t {abstract}\n{star}
                       '''
        slack.notify(text=text_slack)


def main():
    id_list = get_articles_info()
    results = serch_keywords(id_list)
    send2slack(results)


if __name__ == "__main__":
    main()

