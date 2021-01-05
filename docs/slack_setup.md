1. **webhook urlの取得**
    - 特定のslackチャンネルに流すための準備を行います。
    - incomming webhookの**webhook url**を取得してください。
        - 参考サイト
            - [公式](https://slack.com/intl/ja-jp/help/articles/115005265063-Slack-での-Incoming-Webhook-の利用)
            - [紹介記事](https://qiita.com/vmmhypervisor/items/18c99624a84df8b31008)
    - slack通知の時のアイコンが設定できますので、よければこれ使ってください。
        - [icon](https://github.com/fkubota/Carrier-Owl/blob/master/data/images/carrier-owl.png)
            <img src='../data/images/carrier-owl.png' width='50'>



1. **webhook urlの設定**
    - step3で取得した `webhook url` を設定します。
    - 手順

        a. `settings` をクリック。

         <img src='../data/images/05.png' width='1000'>
        
        b. `Secrets` をクリック。  

        c. `New repository secret` をクリック。

        d. Nameを `SLACK_ID` と入力。Valueを **step2** で取得した`webhook url`を貼り付けます。

        <img src='../data/images/07.png' width='1000'>
        
        e. 最後に`Add secret`をクリックして登録完了です。
