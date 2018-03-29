Get Zulip notifications from your Trello boards!

1. {!create-stream.md!}

1. {!create-bot-construct-url-indented.md!}

* We will first collect four items: a **Board ID**, an **API Key**, a
  **User Token**, and an **ID Model**.

    * **Board ID**: Go to your Trello board. The URL should look like
      `https://trello.com/b/<BOARD_ID>/<BOARD_NAME>`. Note down the
      `<BOARD_ID>`.

    * **API Key**: Go to <https://trello.com/1/appkey/generate>. Note down the
      key listed under **Developer API Keys**.

    * **User Token**: Go to the URL below, after replacing `<API_KEY>` with the
      API Key you just wrote down.

       `https://trello.com/1/authorize?key=<API_KEY>&name=Issue+Manager&expiration=never&response_type=token&scope=read`

      Click on **Allow**. Note down the token generated.

    * **ID Model**: Go to the following URL, after replacing `<BOARD_ID>`,
      `<API_KEY>`, and `<USER_TOKEN>` appropriately:

       `https://api.trello.com/1/board/<BOARD_ID>?key=<API_KEY>&token=<USER_TOKEN>`

      You should see a bunch of structured text. Find the row that looks like
      `id: <some number>`. Note down that number.

1. To create the webhook, send a **POST** request to

    `https://api.trello.com/1/tokens/<USER_TOKEN>/webhooks/?key=<API_KEY>`

    with the following data:

```
{
    "description": "Webhook for Zulip integration",
    "callbackURL": "<URL_FROM_STEP_2>",
    "idModel": "<ID_MODEL>",
}
```

For example, you can do this using the `curl` program as follows:

```
curl 'https://api.trello.com/1/tokens/<USER_TOKEN>/webhooks/?key=<API_KEY>'
-H 'Content-Type: application/json' -H 'Accept: application/json'
--data-binary $'{\n  "description": "Webhook for Zulip integration",\n  "callbackURL": "<URL_FROM_STEP_2>",\n  "idModel": "<ID_MODEL>"\n}'
--compressed
```

Remember to replace `<USER_TOKEN>`, `<API_KEY>`, `<URL_FROM_STEP_2>`, and `<ID_MODEL>`, keeping the quotes (`"`) in place.

The response from Trello should look like:

```
{
    "id": "<WEBHOOK_ID>",
    "description": "Webhook for Zulip integration",
    "idModel": "<ID_MODEL>",
    "callbackURL": "<URL_FROM_STEP_2>",
    "active": true
}
```

!!! tip ""
    To learn more, see [Trello's webhooks documentation][1].

[1]: https://developers.trello.com/page/webhooks

{!congrats.md!}

![](/static/images/integrations/trello/001.png)
