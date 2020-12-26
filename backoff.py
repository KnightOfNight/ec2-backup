"""run a command with a geometric backoff"""

import logging
import time

def backoff(retries, func, *args, **kwargs):
    """run a command with a geometric backoff"""
    for attempt in range(retries):
        try:
            ret = func(*args, **kwargs)

        except: # pylint: disable=bare-except
            if attempt < retries:
                sleeptime = .25 * (attempt * 2)
                logging.warning("%s() failed, backing off %.2f seconds", func, sleeptime)
                time.sleep(sleeptime)
            else:
                logging.critical("%s() failed after %d retries", func, retries)
                raise

        else:
            logging.debug("%s() successful", func)
            return ret
