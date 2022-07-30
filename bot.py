import yaml
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.files import JSONStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import executor


import config


bot = Bot(token=config.token)
storage = JSONStorage(path=config.storage_filename)
dp = Dispatcher(bot, storage=storage)


class Quizes:
    def __init__(self, filename: str):
        self.filename = filename
        self.load()

    def reload(self):
        self.load()

    def load(self):
        yaml_from_file = load_yaml(self.filename)
        assert yaml_from_file is not None, f'Check that there is a correct file {self.filename}'
        self.questions = yaml_from_file['questions']
        self.topics = self.parse_topics(yaml_from_file['enabled_topics'])

    def parse_topics(self, enabled_topics):
        '''Return a dictionary of topics within enabled_topics that have at
        least one question the key is topic_code, the value is a dictionary
        with keys: 'name', 'q_count', etc
        {
            'ccna': {
                'name': 'CCNA',
                'q_count': 20,
                'show-correctness': False,
                },
        }
        '''
        topics = {}
        for item in enabled_topics:
            for topic_code, topic in item.items():
                # Count number of questions within each topic
                q_count = len([1 for q in self.questions if q['t'] == topic_code])
                if q_count:
                    # If questions are present, then create a dictionary for the topic
                    topics[topic_code] = {
                        'name': topic['name'],
                        'q_count': q_count,
                        'show-correctness': 'show-correctness' in topic.get('tags', []),
                    }
        return topics


def load_yaml(filename):
    '''Load yaml-file or return None if file does not exist'''
    try:
        with open(filename, 'r', encoding='utf8') as file:
            return yaml.safe_load(file)
    except FileExistsError:
        return None


def user_info_ok(user_info):
    '''Make sure user_info contains only allowed characters'''
    lat_low = 'abcdefghijklmnopqrstuvwxyz'
    lat_upp = lat_low.upper()
    cyr_low = 'абвгдеёжзийклмнопрстуфхцчшщъыьэюя'
    cyr_upp = cyr_low.upper()
    digits = '0123456789'
    additional = ' ,.-\n'
    allowed = lat_low + lat_upp + cyr_low + cyr_upp + digits + additional
    result = all(c in allowed for c in user_info)
    return result


class Info(StatesGroup):
    '''FSM for getting information about user'''
    get_user_info = State()


class Quiz(StatesGroup):
    '''FSM for selecting topic, waiting for admission and questioning'''
    get_topic = State()  # User selects a quiz topic
    get_admission = State()  # User waits for admission from administrator
    quiz = State()  # User is answering questions


async def del_other_msgs(state: FSMContext, final_msg_id=None):
    '''Delete all messages within the 'delete' list of the state (chat_id is
    also taken from a state object)
    Optionally add final_msg_id to the 'delete' list (to be deleted later on)
    '''
    data = await state.get_data()
    msgs_to_delete = data.get('delete', [])
    chat_id = state.chat
    for msg_id in msgs_to_delete.copy():
        result = await bot.delete_message(chat_id, msg_id)
        if result:
            msgs_to_delete.remove(msg_id)
    if msgs_to_delete:
        print(f'Oops, messages were not deleted: {msgs_to_delete}')
    if final_msg_id:
        msgs_to_delete.append(final_msg_id)
    if data or final_msg_id:
        await state.update_data({'delete': msgs_to_delete})
        dp.storage.write(dp.storage.path)


@dp.message_handler(state='*', commands='finish')
async def cmd_finish(msg: types.Message, state: FSMContext):
    '''Erase all the data of the user'''
    await state.finish()
    dp.storage.write(dp.storage.path)
    await cmd_cancel(msg, state)


@dp.message_handler(state='*', commands='cancel')
async def cmd_cancel(msg: types.Message, state: FSMContext):
    '''Cancel any FSM operation, clear unsaved data, delete messages from the
    'delete' list within the state, save resulting data
    '''
    await del_other_msgs(state)
    await msg.delete()
    cur_state = await state.get_state()
    data = await state.get_data()
    if cur_state == None:
        return
    elif cur_state == 'Quiz:quiz':
        admin_text_new = data.get('admin_msg_text') + f"\n\n{MESSAGES['test_canceled']}"
        try:
            await bot.edit_message_text(admin_text_new, ADMIN, data.get('admin_msg_id'))
        except:
            await bot.send_message(ADMIN, MESSAGES['test_canceled'], reply_to_message_id=data.get('admin_msg_id'))
    if data.get('qmessage_id'):
        await bot.delete_message(state.user, data.get('qmessage_id'))
    data = clear_data(data)
    await state.set_data(data)
    await state.reset_state(with_data=False)
    dp.storage.write(dp.storage.path)


@dp.message_handler(commands=['start', 'help'])
async def cmd_start(msg: types.Message, state: FSMContext):
    msg_start = await msg.answer(MESSAGES['start'])
    await del_other_msgs(state, msg_start.message_id)
    await msg.delete()


@dp.message_handler(commands=['reload'])
async def cmd_reload(msg: types.Message, state: FSMContext):
    if msg.chat.id == ADMIN:
        quizes.reload()
    await msg.delete()


@dp.message_handler(commands='info')
async def cmd_info(msg: types.Message, state: FSMContext):
    await Info.get_user_info.set()
    msg_info = await msg.answer(MESSAGES['info'])
    await del_other_msgs(state, msg_info.message_id)
    await msg.delete()


@dp.message_handler(state=Info.get_user_info)
async def fsm_get_user_info(msg: types.Message, state: FSMContext):
    '''Save user info if is OK
    Otherwise tell user to try again
    '''
    if user_info_ok(msg.text):
        await Info.next()
        await state.update_data({'user_info': msg.text})
        await msg.delete()
        msg_topic = await msg.answer(MESSAGES['topic'])
        msg_to_delete = msg_topic.message_id
        dp.storage.write(dp.storage.path)
    else:
        msg_info = await msg.answer(MESSAGES['info_allowed_characters'])
        msg_to_delete = msg_info.message_id
        await msg.delete()
    await del_other_msgs(state, msg_to_delete)


def get_kb_topics(topics):
    '''Return an inline keyboard with all available topics' names as well as
    number of questions within each
    Callback data is set to the code of the topic
    '''
    keyboard_markup = types.InlineKeyboardMarkup(row_width=1)
    buttons = []
    for topic_code, topic in topics.items():
        topic_name = topic['name']
        q_count = topic['q_count']
        buttons.append(
            types.InlineKeyboardButton(f'{topic_name} ({q_count})',
                                        callback_data=topic_code)
        )
    keyboard_markup.add(*buttons)
    return keyboard_markup


def get_kb_admit(user_id, topic):
    '''Prepare admin's keyboard for admition decision'''
    yes_text = MESSAGES['admit_buttons'][1]
    no_text = MESSAGES['admit_buttons'][0]
    text_and_data = (
        (yes_text, f'admit_{user_id}_{topic}'),
        (no_text, f'noadmit_{user_id}_{topic}'),
    )
    keyboard_markup = types.InlineKeyboardMarkup(row_width=1)
    buttons = (
        types.InlineKeyboardButton(text, callback_data=cb_data)
        for text, cb_data in text_and_data
    )
    keyboard_markup.add(*buttons)
    return keyboard_markup


@dp.message_handler(commands='topic')
async def cmd_topic(msg: types.Message, state: FSMContext):
    '''Start topic selection process if user_info is present
    Remind user about /info otherwise
    '''
    data = await state.get_data()
    if 'user_info' in data:
        await Quiz.get_topic.set()
        keyboard_markup = get_kb_topics(quizes.topics)
        msg_info = await msg.answer(MESSAGES['topic_select'], reply_markup=keyboard_markup)
    else:
        msg_info = await msg.answer(MESSAGES['start'])
    await del_other_msgs(state, msg_info.message_id)
    await msg.delete()


def oneline_tg_info(user: types.User):
    '''Return telegram user info in the following format:
    first_name[ last_name][ aka @username] (user_id)
    '''
    result = user.first_name
    if user.last_name:
        result += f' {user.last_name}'
    if user.username:
        result += f' aka @{user.username}'
    result += f' ({user.id})'
    return result


@dp.callback_query_handler(state=Quiz.get_topic)
async def fsm_cb_query_get_topic(query: types.CallbackQuery, state: FSMContext):
    topic_code = query.data
    if topic_code not in quizes.topics:
        # Shouldn't really ever happen, but ¯\_(ツ)_/¯
        await query.answer(MESSAGES['oops'])
        return

    # Go to Quiz.get_admission
    await Quiz.next()
    state_data = await state.get_data()

    # Tell admin about quiz request
    admit_text_admin = MESSAGES['admit_text_admin'].format(
        f"{quizes.topics[topic_code]['name']} ({topic_code})",
        state_data['user_info'],
        oneline_tg_info(query.from_user),
    )
    keyboard_markup = get_kb_admit(query.from_user.id, topic_code)
    admin_msg = await bot.send_message(ADMIN, admit_text_admin, reply_markup=keyboard_markup)
    await state.update_data({'admin_msg_id': admin_msg.message_id})
    await state.update_data({'admin_msg_text': admin_msg.text})
    dp.storage.write(dp.storage.path)

    # Tell user to wait for admission
    await state.update_data({'topic': topic_code})
    admit_text_user = MESSAGES['admit_text_user'].format(quizes.topics[topic_code]['name'])
    msg_sent = await bot.send_message(query.from_user.id, admit_text_user)
    await del_other_msgs(state, msg_sent.message_id)
    await query.answer()


def get_query_answer(show_correctness: bool, cb_data: str):
    '''Return text based on show_correctness
    (and int(cb_data) if show_correctness is True)
    '''
    if show_correctness:
        if int(cb_data):
            return MESSAGES['query_answer_correct']
        return MESSAGES['query_answer_incorrect']
    return ''


@dp.callback_query_handler(text=['0', '1'], state=Quiz.quiz)
async def fsm_cb_query_answer(query: types.CallbackQuery, state: FSMContext):
    mark = int(query.data)
    await del_other_msgs(state)
    data = await state.get_data()
    score = data.get('score', 0)
    show_correctness = data.get('show-correctness', False)
    if mark:
        score += int(query.data)
        await state.update_data({'score': score})
        dp.storage.write(dp.storage.path)
    result, q_id = await send_question(state, query.message.message_id)
    query_answer = get_query_answer(show_correctness, query.data)
    await query.answer(query_answer)
    if result is None:
        # If there were no more questions
        user_score = f'{score}/{q_id} = {round(score/q_id*100)}%'
        admin_text_new = data.get('admin_msg_text') + f'\n\n{user_score}'
        try:
            await bot.edit_message_text(admin_text_new, ADMIN, data.get('admin_msg_id'))
        # TODO Is there a specific error when message is too old to edit?
        except:
            await bot.send_message(ADMIN, str(user_score), reply_to_message_id=data.get('admin_msg_id'))
        await query.message.delete()


async def send_question(state: FSMContext, edit_msg=None):
    data = await state.get_data()
    # q_id is the id of the current question to ask
    q_id = data.get('q_id', -1) + 1
    topic = data.get('topic', None)
    if topic is None:
        print('Oops, topic is None!')
        return
    text, keyboard_markup, parse_mode = prepare_question(quizes.questions, topic, q_id)
    if text is None:
        # No more questions to ask
        score = data.get('score', 0)
        final_text = MESSAGES['test_ended'].format(
            quizes.topics[topic]['name'],
            q_id,
            score,
            round(score/q_id*100)
        )
        sent_msg = await bot.send_message(state.user, final_text)
        await del_other_msgs(state, sent_msg.message_id)
        data = clear_data(data)
        await state.set_data(data)
        await state.reset_state(with_data=False)
        dp.storage.write(dp.storage.path)
        return None, q_id
    if edit_msg:
        await bot.edit_message_text(text, state.user, edit_msg, reply_markup=keyboard_markup, parse_mode=parse_mode)
    else:
        question_message = await bot.send_message(state.user, text, reply_markup=keyboard_markup, parse_mode=parse_mode)
        if q_id == 0:
            # The very first question has just been asked
            await state.update_data({'qmessage_id': question_message.message_id})
            await state.update_data({'show-correctness': quizes.topics[topic]['show-correctness']})
    await state.update_data({'q_id': q_id})
    dp.storage.write(dp.storage.path)
    return q_id, q_id


def clear_data(data: dict):
    '''Clean up all the optional keys in data dictionary'''
    for key in [ 'topic', 'q_id', 'score',
                 'admin_msg_id', 'admin_msg_text',
                 'qmessage_id', 'show-correctness']:
        data.pop(key, None)
    return data


def my_md(text: str) -> str:
    '''Prepare text for Markdown by either removing 'MD:' prefix or
    escaping some characters for Telegram Markdown
    '''
    if text.startswith('MD:'):
        result = text.replace('MD:', '', 1)
        return result
    result = text
    for letter in '_*[]()~`>#+-=|{}.!':
        result = result.replace(letter, f'\{letter}')
    return result


def format_answer(use_md, letter, answer):
    '''Prepare answer line based on use_md:

    use_md == False
    - `Answer-A text`     ->  A. `Answer-A text`

    use_md == True
    - `Answer-A text`     ->  A\. \`Answer\-A text\`
    - MD:`Answer-B text`  ->  B\. `Answer-B text`
    '''
    result = letter + ('\\' if use_md else '') + '. '
    result += my_md(answer) if use_md else answer
    return result


def prepare_question(questions, topic_code, q_id):
    '''Return a tuple of q+rnd(asnwers) and inline_kb(('A',0), ('B',1), ('C',0)
    or (None, None) if there are no more questions
    '''
    from random import sample
    letters = 'ABCDEFGHIJ'
    counter = 0
    for top_question in questions:
        if top_question['t'] != topic_code:
            continue
        if counter < q_id:
            counter += 1
            continue
        final_q = top_question['q']
        raw_answers = top_question['a']
        correct_answer = raw_answers[0]
        # use_md will be True if question or any answer startswith 'MD:', False otherwise
        use_md = final_q.startswith('MD:') or any(
            map(lambda s: s.startswith('MD:'), raw_answers))
        if use_md:
            final_q = my_md(final_q)
        random_answers = sample([(a,int(a==correct_answer)) for a in raw_answers], len(raw_answers))
        buttons = []
        for i, (answer, points) in enumerate(random_answers):
            delimiter = '\n' if i else '\n\n'
            final_q += delimiter + format_answer(use_md, letters[i], answer)
            buttons.append(types.InlineKeyboardButton(
                letters[i], callback_data=str(points)))
        keyboard_markup = types.InlineKeyboardMarkup()
        keyboard_markup.row(*buttons)
        parse_mode = 'MarkdownV2' if use_md else ''
        return (final_q, keyboard_markup, parse_mode)
    return (None, None, None)


@dp.callback_query_handler(text_startswith=['admit_', 'noadmit_'])
async def cb_query_admit(query: types.CallbackQuery, state: FSMContext):
    if query.message.chat.id != ADMIN:
        await query.answer(MESSAGES['oops'])
        return

    admit, user_id, topic = query.data.split('_', 2)
    user_state = FSMContext(dp.storage, user_id, user_id)
    cur_state = await user_state.get_state()
    user_data = await user_state.get_data()
    cur_user_topic = user_data.get('topic')

    if cur_state != 'Quiz:get_admission':
        await query.answer(MESSAGES['oops'])
        text = f'User state is set to {cur_state} instead of Quiz:get_admission'
        await query.message.answer(text)
        return

    if cur_user_topic != topic:
        await query.answer(MESSAGES['oops'])
        text = f'User topic is set to {cur_user_topic} instead of requested {topic}'
        await query.message.answer(text)
        return

    if admit == 'noadmit':
        await query.answer('No admit')
        decision = MESSAGES['admit_no_admin']
        sent_message = await bot.send_message(user_id, MESSAGES['admit_no_user'])
        await user_state.reset_state(with_data=False)
    elif admit == 'admit':
        await query.answer('Admit')
        decision = MESSAGES['admit_yes_admin']
        sent_message = await bot.send_message(user_id, MESSAGES['admit_yes_user'])
        await user_state.set_state(Quiz.quiz)
        await send_question(user_state)
    else:
        await query.answer(MESSAGES['oops'])
        return

    await del_other_msgs(user_state, sent_message.message_id)
    new_text = '\n'.join(query.message.text.split('\n')[:-1] + [decision])
    await query.message.edit_text(new_text)
    await user_state.update_data({'admin_msg_text': new_text})
    dp.storage.write(dp.storage.path)


@dp.message_handler(state='*', content_types=types.ContentType.ANY)
async def any_message(msg: types.Message):
    '''Delete any unexpected messages'''
    await msg.delete()


ADMIN = config.admin
MESSAGES = load_yaml(config.messages_filename)
assert MESSAGES is not None, f'Check that there is a correct {config.messages_filename}'
quizes = Quizes(config.questions_filename)
executor.start_polling(dp)#, skip_updates=True)
