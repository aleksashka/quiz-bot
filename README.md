### What

Aiogram-based telegram bot for conducting text-based single-answer tests.

### Why

To get to know aiogram as well as to conduct some tests.

I am pretty sure there are lot's of similar bots, but ¯\\\_(ツ)\_/¯.

### How to run

- Install required non-standard packages: aiogram, pyyaml.

- Clone this repository.

- Copy [`config_sample.py`](config_sample.py) to `config.py` and update variables:
  - `token` - bot token from [BotFather](https://t.me/BotFather);
  - `admin` - admin's chat ID (remember that bot cannot **initiate** conversations).

- Add your quizes to `questions.yaml` (check [`questions_sample.yaml`](questions_sample.yaml) for examples):
  - `topic` should be listed as `enabled_topics` to be accessible;
  - `t` - topic name;
  - `q` - text of the question;
  - `a` - answers, correct answer should be the first one.

- Run [`bot.py`](bot.py) using Python3 interpreter.

### How to use

- User starts the conversation with your bot using the Start button and receives [instructions](https://github.com/aleksashka/quiz-bot/blob/ce5e04796ad0c0e71cc4809f5e3389b2926a771d/messages.yaml#L3).
- The user supplies some [information](https://github.com/aleksashka/quiz-bot/blob/ce5e04796ad0c0e71cc4809f5e3389b2926a771d/messages.yaml#L10) using the `/info` command.
- The user selects the quiz [topic](https://github.com/aleksashka/quiz-bot/blob/ce5e04796ad0c0e71cc4809f5e3389b2926a771d/messages.yaml#L24) using the `/topic` command and waits for admission.
- Admin receives an [admission message](https://github.com/aleksashka/quiz-bot/blob/ce5e04796ad0c0e71cc4809f5e3389b2926a771d/messages.yaml#L27) with user information and presses one of the [buttons](https://github.com/aleksashka/quiz-bot/blob/ce5e04796ad0c0e71cc4809f5e3389b2926a771d/messages.yaml#L40).
- The user gets notification about the admin's decision. If admitted then also receives the first question from the selected topic.
- At the end of the quiz the user gets a [message](https://github.com/aleksashka/quiz-bot/blob/ce5e04796ad0c0e71cc4809f5e3389b2926a771d/messages.yaml#L66) with the results, admin's admission message is updated with the results as well
- The user can `/cancel` any operation at any moment.
- The user can also send a `/finish` command that will clean up all the information within the bot's FSM storage.

#### Markdown support
You can start a question and/or answer(s) with `MD:` (will be removed) in order to format it using [MarkdownV2](https://core.telegram.org/bots/api#markdownv2-style).
In this case you will have to escape the following characters `` _*[]()~`>#+-=|{}.! `` inside the **corresponding** (`MD:`-containing) question and/or answer(s) using a backslash `\`.
