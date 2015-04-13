

import ConfigParser
import logging
import MySQLdb
import os
import sys


def getcreds():
    config = ConfigParser.ConfigParser()

    config_files = config.read([os.path.expanduser('~/.my.cnf')])

    if not config_files:
        logging.critical('MySQL configuration file not found')
        sys.exit(-1)

    section = 'client'
    if not config.has_section(section):
        logging.critical('MySQL configuration error, [%s] section not found' % (section))
        sys.exit(-1)

    opt = 'user'
    if not config.has_option(section, opt):
        logging.critical('configuration error, [%s] section missing option "%s"' % (section, opt) )
    username = config.get('client', opt)

    opt = 'password'
    if not config.has_option(section, opt):
        logging.critical('configuration error, [%s] section missing option "%s"' % (section, opt) )
    password = config.get('client', opt)

    return( (username, password) )


class lock:
    def __init__(self):
        (username, password) = getcreds()

        self.db = MySQLdb.connect( user = username, passwd = password, host = 'localhost' )
        self.cur = self.db.cursor()

    def lock(self):
        self.cur.execute('flush logs')
        self.cur.execute('flush tables with read lock')

    def unlock(self):
        self.cur.execute('unlock tables')

class stop:
    def __init__(self, initscript = '/etc/init.d/mysql'):
        self.initscript = initscript

