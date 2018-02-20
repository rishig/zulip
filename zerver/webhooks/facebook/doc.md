Receive your Facebook notifications in Zulip!

1. {!create-stream.md!}

1. {!create-a-bot-indented.md!}

    Construct the URL for the {{ integration_display_name }}
    bot using the bot's API key and the desired stream name:

    `{{ api_url }}{{ integration_url }}?api_key=abcdefgh&stream={{ recommended_stream_name }}&token=unused`

    Modify the parameters of the URL above, where `api_key` is the API key
    of your Zulip bot, and `stream` is the stream name you want the
    notifications sent to.

1. Register on the [Facebook for developers page][1].
   Next, click on **+ Add a New App** in the top-right corner.
   Fill in the **Create a New App ID** form and click on **Create App ID**.

[1]: https://developers.facebook.com/apps/

1. Under **Webhooks**, click on the **Set up** button. NEEDS A SENTENCE HERE.
   As an example, this guide explains how to subscribe to a **"feed"**
   in the **User** category.

1. Select the **User** category from the dropdown. Click on the
   **Subscribe to this topic** button.

1. In the **Edit User Subscription** form, set **Callback URL** to the URL
   created above. Set **Verify Token** to `unused`, and activate the
   **Include Values** option. Click on the **Verify and Save** button.

1. Click on **Subscribe** and **Test** in the **feed** row:

    ![](/static/images/integrations/facebook/001.png)

    Optionally, you may click on the **Send to My Server** button to
    send a test message to your Zulip organization.

{!congrats.md!}

![](/static/images/integrations/facebook/002.png)
