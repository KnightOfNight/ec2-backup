"""mysql library for ec2_backup"""


import logging
import os
import subprocess
import sys
import ConfigParser
import MySQLdb # pylint: disable=import-error


def getcreds():
    """get mysql credentials"""
    config = ConfigParser.ConfigParser()

    config_files = config.read([os.path.expanduser('~/.my.cnf')])

    if not config_files:
        logging.critical('MySQL configuration file not found')
        sys.exit(-1)

    section = 'client'
    if not config.has_section(section):
        logging.critical('MySQL configuration error, [%s] section not found', section)
        sys.exit(-1)

    opt = 'user'
    if not config.has_option(section, opt):
        logging.critical('configuration error, [%s] section missing option "%s"', section, opt)
    username = config.get('client', opt)

    opt = 'password'
    if not config.has_option(section, opt):
        logging.critical('configuration error, [%s] section missing option "%s"', section, opt)
    password = config.get('client', opt)

    return (username, password)


class Lock(): # pylint: disable=old-style-class
    """class that manages mysql locking"""
    def __init__(self):
        (username, password) = getcreds()

        self.database = MySQLdb.connect(user=username, passwd=password, host='localhost')
        self.cur = self.database.cursor()

    def green(self):
        """lock tables"""
        logging.info('locking mysql tables')
        self.cur.execute('flush logs')
        self.cur.execute('flush tables with read lock')

    def red(self):
        """unlock tables"""
        logging.info('unlocking mysql tables')
        self.cur.execute('unlock tables')


class Stop(): # pylint: disable=old-style-class
    """class that manages mysql service"""
    def __init__(self, initscript='/etc/init.d/mysqld'):
        self.initscript = initscript

    def green(self):
        """stop database service"""
        logging.info('stopping mysql')
        cmd = self.initscript + ' stop > /dev/null'
        if subprocess.call(cmd, shell=True):
            logging.critical('unable to stop mysql')
            sys.exit(-1)

    def red(self):
        """start database service"""
        logging.info('starting mysql')
        cmd = self.initscript + ' start > /dev/null'
        if subprocess.call(cmd, shell=True):
            logging.critical('unable to start mysql')
            sys.exit(-1)
