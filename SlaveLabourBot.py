#! /usr/bin/env python3
import praw
import re
import logging
import time
import threading
import traceback
import telegram.error
from os import getcwd
from telegram.ext import Updater
from telegram.ext import CommandHandler
from telegram.ext import PicklePersistence
from secrets import telegram_token, telegram_username, reddit_client_id, reddit_client_secret, reddit_user_agent

"""
Available commands:
start - Start receiving tasks
add_keyword - Add a keyword to mark tasks
remove_keyword - Remove a keyword
list_keywords - List keywords
stop - Stop receiving tasks
"""
CWD=getcwd() + "/"
print(CWD)

started_id = {}
to_stop_id = []

REGEX_TITLE_PATTERN='^\[TASK\]'
title_regex = re.compile(REGEX_TITLE_PATTERN, re.IGNORECASE)

logging.basicConfig(filename=CWD + 'SlaveLabourBotLog.log', filemode='a', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

persistent_data = PicklePersistence(filename=CWD + 'persistent_data')
updater = Updater(token=telegram_token, persistence=persistent_data, use_context=True)
dispatcher = updater.dispatcher

reddit = praw.Reddit(client_id=reddit_client_id, client_secret=reddit_client_secret, user_agent=reddit_user_agent)

def start(update, context):
	allowed_users = []

	logging.info('start sent by id:%s username:%s first_name:%s last_name:%s' % (update.effective_user.id, update.effective_user.username, update.effective_user.first_name, update.effective_user.last_name))

	with open(CWD + 'allowed_users.txt') as f:
		for line in f:
			allowed_users.append(line.strip())

	if update.effective_user.username not in allowed_users:
		update.message.reply_text(f'You are not allowed to use this bot. Send a message to @{telegram_username} to require the access.')
		return

	if started_id.get(update.effective_user.id):
		logging.info('replied: Bot already started. Use `/stop` to stop the bot')
		update.message.reply_text('Bot already started. Use `/stop` to stop the bot', parse_mode='Markdown')
		return
	context.bot.send_message(chat_id=update.effective_chat.id, text="Hello, I'm your SlaveLabour bot, you will be notified when new tasks are available, here's a couple to start with.")
	logging.info('Bot started succesfully for user %s' % update.effective_user.username)
	id_set = set()
	routine_thread = threading.Thread(target=routine, args=(update, context, 10, id_set))
	started_id[update.effective_user.id] = routine_thread
	routine_thread.start()

def stop(update, context):
	logging.info('stop sent by id:%s username:%s first_name:%s last_name:%s' % (update.effective_user.id, update.effective_user.username, update.effective_user.first_name, update.effective_user.last_name))
	thread = started_id.get(update.effective_user.id)
	if thread:
		to_stop_id.append(update.effective_user.id)
		thread.join()
		to_stop_id.remove(update.effective_user.id)
		logging.info('replied: Bot stopped')
		update.message.reply_text('Bot stopped')
		del started_id[update.effective_user.id]
	else:
		logging.info('replied: Bot isn\'t running')
		update.message.reply_text('Bot isn\'t running')

def routine(update, context, limit, id_set):
	while True:
		try:
			allowed_users = []
			with open(CWD + 'allowed_users.txt') as f:
				for line in f:
					allowed_users.append(line.strip())

			if update.effective_user.username not in allowed_users:
				update.message.reply_text('You are not allowed to use this bot. Send a message to @gdandrea97 to require the access.')
				return

			logging.info('Checking for new tasks for %s' % update.effective_user.username)
			kw_flag = False

			# Try except block to prevent blocking if api can't retrieve user_data
			try:
				kw_list = context.user_data['keywords']
				if kw_list and len(kw_list):
					kw_flag = True
					kw_str = '|'.join(kw_list)
					kw_regex_pattern = r'\b(%s)\b' % kw_str
					kw_regex = re.compile(kw_regex_pattern, re.IGNORECASE)
			except KeyError:
				logging.error('Unable to retrieve keywords for user %s:%s' % (update.effective_user.id, update.effective_user.username))
				try:
					update.message.reply_text('Unable to store and retrieve information about your keywords, maybe is for your privacy settings?')
				except telegram.error.Unauthorized:
					logging.error('Unable to send message to user %s, the user blocked the bot. Requiring forced stop.' % (update.effective_user.username))
					del started_id[update.effective_user.id]
					return

			for submission in reddit.subreddit('slavelabour').new(limit=limit):
				if submission.id not in id_set and title_regex.search(submission.title):
					id_set.add(submission.id)
					message_text="*%s*\nhttps://redd.it/%s\n\n`%s`" % (submission.title, submission.id, submission.selftext)
					if kw_flag and (kw_regex.search(submission.title) or kw_regex.search(submission.selftext)):
						message_text = '*[MARKED]* %s' % message_text
					try:
						context.bot.send_message(chat_id=update.effective_chat.id, text=message_text, parse_mode='Markdown', disable_web_page_preview=True)
					except:
						context.bot.send_message(chat_id=update.effective_chat.id, text=message_text, disable_web_page_preview=True)

			for i in range(30):
				if update.effective_user.id in to_stop_id:
					return
				time.sleep(2)
		except telegram.error.Unauthorized:
			logging.error('Unable to send message to user %s, the user blocked the bot. Requiring forced stop.' % (update.effective_user.username))
			del started_id[update.effective_user.id]
			return
		except Exception as e:
			logging.error('Error: %s' % e)
			logging.error(traceback.format_exc())
			time.sleep(60)

def add_keyword(update, context):
	"""Usage: /add_keyword value"""
	# Generate ID and seperate value from command
	logging.info('%s sent by id:%s username:%s first_name:%s last_name:%s' % (update.message.text, update.effective_user.id, update.effective_user.username, update.effective_user.first_name, update.effective_user.last_name))
	value = update.message.text.partition(' ')[2].strip().lower()
	if value == '':
		logging.info('replied: Blank keyword is not allowed.\nUse `/add_keyword keyword`')
		update.message.reply_text('Blank keyword is not allowed.\nUse `/add_keyword keyword`', parse_mode='Markdown')
		return

	try:
		if value in context.user_data['keywords']:
			logging.info('replied: Keyword %s already in the list.' % value)
			update.message.reply_text('Keyword %s already in the list.' % value)
			return
		context.user_data['keywords'].append(value)
	except KeyError:
		context.user_data['keywords'] = []
		context.user_data['keywords'].append(value)

	logging.info('replied: Keyword %s added' % value)
	update.message.reply_text('Keyword %s added' % value)

def remove_keyword(update, context):
	"""Usage: /remove_keyword value"""
	logging.info('%s sent by id:%s username:%s first_name:%s last_name:%s' % (update.message.text, update.effective_user.id, update.effective_user.username, update.effective_user.first_name, update.effective_user.last_name))
	value = update.message.text.partition(' ')[2].strip().lower()
	if value == '':
		logging.info('replied: Blank keyword is not allowed.\nUse `/remove_keyword keyword`')
		update.message.reply_text('Blank keyword is not allowed.\nUse `/remove_keyword keyword`', parse_mode='Markdown')
		return
	try:
		context.user_data['keywords'].remove(value)
		logging.info('replied: Keyword %s removed' % value)
		update.message.reply_text('Keyword %s removed' % value)
	except (KeyError, ValueError):
		logging.info('replied: Keyword %s not found' % value)
		update.message.reply_text('Keyword %s not found' % value)
		 	

def list_keywords(update, context):
	"""Usage: /list_keywords"""
	logging.info('%s sent by id:%s username:%s first_name:%s last_name:%s' % (update.message.text, update.effective_user.id, update.effective_user.username, update.effective_user.first_name, update.effective_user.last_name))
	try:
		if len(context.user_data['keywords']) == 0:
			raise KeyError
		text = ''
		for kw in context.user_data['keywords']:
			text += '%s\n' % kw
		text = text[:-1]
		logging.info('replied: Keywords list:\n%s' % text)
		update.message.reply_text('Keywords list:\n%s' % text)
	except KeyError:
		"""List is empty or never created"""
		logging.info('replied: No keywords added. Please use /add_keyword to add a new keyword.')
		update.message.reply_text('No keywords added. Please use /add_keyword to add a new keyword.')
			

start_handler = CommandHandler('start', start)
stop_handler = CommandHandler('stop', stop)
add_keyword_handler = CommandHandler('add_keyword', add_keyword)
list_keywords_handler = CommandHandler('list_keywords', list_keywords)
remove_keyword_handler = CommandHandler('remove_keyword', remove_keyword) 
dispatcher.add_handler(start_handler)
dispatcher.add_handler(stop_handler)
dispatcher.add_handler(add_keyword_handler)
dispatcher.add_handler(list_keywords_handler)
dispatcher.add_handler(remove_keyword_handler)

updater.start_polling()
