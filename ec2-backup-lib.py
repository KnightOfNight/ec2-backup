

import logging
import time


# run a command with a geometric backoff
def backoff(max, f, *args, **kwargs):
    for attempt in range(1, max):
        try:
            ret = f(*args, **kwargs)

        except:
            if attempt < max:
                sleeptime = .25 * (attempt * 2)
                logging.warning('"%s" failed, backing off %.2f seconds' % (f, sleeptime))
                time.sleep(sleeptime)
            else:
                logging.critical('failed to execute function "%s", maximum attempts exceeded' % (f))
                raise
        else:
            logging.debug('function "%s" try was successful, no backoff needed' % (f))
            return(ret)

