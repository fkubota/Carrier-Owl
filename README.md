# Carrier Owl
伝書フクロウという意味です。

## About Carrier Owl
前日のarxivから気になる論文にスコアを付けてslackに通知するシステムです。  
通知の際に、abstractをDeepLで翻訳しています。  
**導入は20minぐらいで終わります！！**  
スコアは、ターゲットとなるキーワードに重み付けをして決まります。(例 resnet=5, kaggle=3, audio=3)    
ユーザーが**好きな領域**、**好きなキーワード**を登録することで、通知される論文は変わります。

- 登録キーワード例
    ```
    keywords:
        sound: 1
        audio: 1
        sound feature: 3
        audio feature: 3
        noise removal: 2
        spectrogram: 3
    ```

- 通知例(score昇順)

    <img src='./data/images/03.png' width='600'>


## Installation
**requirements**  
- google chrome
- python3

**step**
1. このリポジトリをフォークする
2. フォークしたリポジトリをクローンする
3. pythonライブラリのインストール
    `pip install -r reuirements.txt`
4. Selenium のインストール(Seleniumについては[こちら](https://qiita.com/Chanmoro/items/9a3c86bb465c1cce738a))
    - chromeのバージョンの確認をしてください。
        - linuxの場合、以下のコマンドで確認できます。
           `google-chrome --version`
    - webdriverのインストール。chromeのメジャーバージョンだけ抜き取って使います。
        - 例) chromeのバージョンが `84.0.4147.105`場合
            `pip install chromedriver-binary==84.*`
    
    - seleniumのインストール
        `pip install selenium`
    
5. webhook urlの取得
    - 特定のslackチャンネルに流すための準備を行います。
    - incomming webhookの**webhook url**を取得してください。
        - 参考サイト
            - [公式](https://slack.com/intl/ja-jp/help/articles/115005265063-Slack-での-Incoming-Webhook-の利用)
            - [紹介記事](https://qiita.com/vmmhypervisor/items/18c99624a84df8b31008)

6. webhook urlの設定
    - `config.yaml` 内の、`'your webhook url'` を取得したURlに変更します。

        <img src='./data/images/01.png' width='400'>

7. 領域の設定
    - 通知させたいarxivの論文の領域を指定します。
    - (computer scienceの人はこの手順を飛ばしてstep8に進んでも構いません)
    - `computer science` なら `cs` などそれぞれに名前がついています。以下の手順で確認します。
    - 手順
        1. [arxiv.org](https://arxiv.org)にアクセス
        2. 通知させたい領域の**resent**と書かれた部分をクリック。

            <img src='./data/images/02.png' width='400'>
        
        3. 遷移後のページのurlを見て、`list/`と`/recent`に囲われている文字列を使います。

            - computer scienceの例: `https://arxiv.org/list/cs/recent`
            - この場合、`cs` をこの後利用する。
        
        4. `config.yaml` 内の、`subject` を3で取得した文字列に変更します。(デフォルトでは`cs`になっています。)

8. キーワードの設定
    - `config.yaml` にキーワードとそのキーワードのスコアを設定します。
    - 例(音に関する論文を通知してほしい場合)
        ```
        keywords:
            sound: 1
            audio: 1
            sound feature: 3
            audio feature: 3
            noise removal: 2
            spectrogram: 3
        ```
    - 仕組みとしては、以下のような感じです。
        1. abstractにキーワードが含まれているか
        2. 含まれていれば、キーワードの合計をscoreとし、昇順で通知

            <img src='./data/images/03.png' width='600'>

9. 動作確認

    - 動作確認してみましょう。
        1. `cd Carrier-Owl/src`
        2. `python3 carrier-owl.py`
    - slackに通知が行けば成功です。

10. 定期実行
    - cron(linux)を使えば定期実行ができます。
    - 設定例(月火水木金の9:50に実行)
        - `50 9 * * 1,2,3,4,5 python3 ~/Git/Carrier-Owl/src/carrier-owl.py`


### Reference
- https://qiita.com/fujino-fpu/items/e94d4ff9e7a5784b2987