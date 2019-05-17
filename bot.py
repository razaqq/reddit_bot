#!/usr/bin/env python3
import praw
from praw.exceptions import *
from prawcore.exceptions import OAuthException, RequestException, ResponseException
import logging
from logging.handlers import RotatingFileHandler
import random
import sys
import os
import configparser as cp
import json


class Config(cp.ConfigParser):
    def __init__(self):
        super().__init__()
        self.path = os.path.dirname(os.path.abspath(__file__))
        self.file = os.path.join(self.path, 'config.ini')
        self.restart_needed = False
        self.read_config()

    def read_config(self):
        """reads the config and checks if its okay"""
        try:
            with open(self.file) as file:
                self.read_file(file)
        except FileNotFoundError as e:
            return self.create_default(e)
        except cp.NoOptionError as e:
            return self.create_default(e)
        except cp.ParsingError as e:
            return self.create_default(e)

    def create_default(self, error):
        """creates a default config"""
        self.restart_needed = True
        if not isinstance(error, FileNotFoundError):
            logging.error('Config error:\n{}\nMaking backup and creating default...'.format(error))
            os.rename(self.file, os.path.join(self.path, 'config.ini.bak'))
        else:
            logging.error('No default config found, creating new one...')

        config = cp.ConfigParser()
        config['MAIN'] = {
            'subreddit': 'all',
            'client_id': 'asdasd',
            'client_secret': 'sadas',
            'user_agent': 'some bot by u/someone',
            'username': 'someusername',
            'password': 'password',
            'keywords': ["some", "keywords", "here"],
            'phrases': ["Im a bot", "I am working"]
        }
        with open(self.file, 'w') as file:
            config.write(file)


class Bot:
    def __init__(self):
        self.initialize_logger()
        c = Config()
        if c.restart_needed:
            sys.exit(0)
        self.config = c['MAIN']
        self.phrases = json.loads(self.config['phrases'])
        self.keywords = json.loads(self.config['keywords'])
        self.r = self.auth()

    def auth(self):
        try:
            r = praw.Reddit(client_id=self.config['client_id'], client_secret=self.config['client_secret'],
                            user_agent=self.config['user_agent'], username=self.config['username'],
                            password=self.config['password'])
            return r
        except OAuthException as e:
            logging.error(e)

    def run_stream(self):
        try:
            logging.info('Starting the reddit comment stream...')
            for comment in self.r.subreddit(self.config['subreddit']).stream.comments(skip_existing=True):
                self.process_comment(comment)
        except KeyboardInterrupt:
            sys.exit(0)
        except RequestException as e:
            logging.error(e)
            sys.exit(1)  # restart the bot
        except ResponseException as e:
            logging.error(e)
            sys.exit(1)

    def process_comment(self, comment):
        if not comment:
            logging.error('Received an empty comment, restarting the stream...')
            sys.exit(1)
        for keyword in self.keywords:
            if keyword in comment.body.lower():
                try:
                    comment.reply(random.choice(self.phrases))
                except APIException as err:
                    logging.error(err)
                logging.info("Replied to: {} in {}".format(comment.id, comment.link_permalink))

    @staticmethod
    def initialize_logger():
        main_path = os.path.dirname(os.path.abspath(__file__))
        logs_dir = os.path.join(main_path, 'logs')
        if not os.path.exists(logs_dir):
            os.mkdir(logs_dir, 755)
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)
        file_handler = RotatingFileHandler(
            os.path.join(logs_dir, 'reddit_bot.log'),
            maxBytes=100000, backupCount=5
        )
        formatter = logging.Formatter('%(asctime)s - %(levelname)-5s -> %(message)s',
                                      datefmt='%d-%m-%Y|%H:%M:%S')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        stdout_handler = logging.StreamHandler(sys.stdout)
        stdout_handler.setLevel(logging.DEBUG)
        stdout_handler.setFormatter(formatter)
        logger.addHandler(stdout_handler)


if __name__ == '__main__':
    b = Bot()
    b.run_stream()
