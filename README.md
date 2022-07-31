### What

Aiogram-based telegram bot for conducting text-based single-answer tests.

### Why

To get to know aiogram as well as to conduct some tests.

I am pretty sure there are lot's of similar bots, but ¯\\\_(ツ)\_/¯.

### How to run

- Install required non-standard packages: aiogram, pyyaml;

- Clone this repository;

- Copy [`config_sample.py`](config_sample.py) to `config.py` and update variables:
  - `token` - bot token from [BotFather](https://t.me/BotFather);
  - `admin` - admin's chat ID (remember that a bot cannot **initiate** conversations);

- Add your quizes to `quizes.yaml` (check [`quizes_sample.yaml`](quizes_sample.yaml) for examples):
  - `topic` should be in `enabled_topics` in order to be available for testing;
  - `t` - a string of space-separated topics to which the question belongs to;
  - `q` - the question itself;
  - `a` - a list of the answers, correct answer should be the first one;
  - Topic within `enabled_topics` may have an optional `tags` list:
    - `show-correctness` tag shows notifications to indicate whether the answer was correct or not;
    - `show-correct` tag shows the  if the answer was incorrect (implies `show-correctness` tag);

- Run [`bot.py`](bot.py) using Python3 interpreter.

### How to use

- User starts the conversation with your bot using the Start button and receives instructions;
- The user supplies some information using the `/info` command;
- The user selects the quiz topic using the `/topic` command and waits for admission;
- Admin receives an admission message with user information and presses one of the buttons;
- The user gets notification about the admin's decision. If admitted then also receives the first question from the selected topic;
- At the end of the quiz the user gets a message with the results, admin's admission message is updated with the results as well;
- The user can `/cancel` any operation at any moment;
- The user can also send a `/finish` command that will clean up all the information within the bot's FSM storage;
- The admin can reload questions from the file using `/reload` command (no need to restart the bot after updating topics or questions).

#### Markdown support
You can start a question and/or answer(s) with `MD:` (will be removed) in order to format it using [MarkdownV2](https://core.telegram.org/bots/api#markdownv2-style).
In this case you will have to escape the following characters `` _*[]()~`>#+-=|{}.! `` inside the **corresponding** (`MD:`-containing) question and/or answer(s) using a backslash `\`.
