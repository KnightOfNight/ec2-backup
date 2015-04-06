#!/usr/bin/env python


import argparse
import logging
import operator
import os
import string
import sys
import subprocess
import time
import boto.utils
import boto.ec2


version = sys.hexversion
if version < 0x02070000:
    sys.stderr.write('python 2.7 or higher required\n')
    sys.exit(-1)


# run a command with a geometric backoff
def backoff(max, f, *args):
    for attempt in range(1, max):
        try:
            ret = f(*args)
        except:
            if attempt < max:
                sleeptime = .25 * (attempt * attempt)
                logging.warning('"%s" failed, backing off %.2f seconds' % (f, sleeptime))
                time.sleep(sleeptime)
            else:
                logging.critical('failed to execute function "%s", maximum attempts exceeded' % (f))
                raise
        else:
            logging.debug('no backoff needed')
            return(ret)


# get all tags for a snapshot
def get_all_tags(conn, snapshot_id):
    return( conn.get_all_tags( filters = {'resource-id': snapshot_id} ) )


# parse command line arguments
parser = argparse.ArgumentParser(description = 'Rotate EBS snapshots', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument('--dry-run', action = 'store_true')
parser.add_argument('--max-retries', default = 10, type = int, help = 'maximum number of API retries before giving up', metavar = 'RETRIES')
parser.add_argument('--keep-hourly', default = 24, type = int, help = 'keep this many hourly snapshots', metavar = 'HOURLY')
parser.add_argument('--keep-daily', default = 7, type = int, help = 'keep this many daily snapshots', metavar = 'DAILY')
parser.add_argument('--keep-weekly', default = 4, type = int, help = 'keep this many weekly snapshots', metavar = 'WEEKLY')
parser.add_argument('--keep-monthly', default = 3, type = int, help = 'keep this many monthly snapshots', metavar = 'MONTHLY')
parser.add_argument('--keep-yearly', default = 1, type = int, help = 'keep this many yearly snapshots', metavar = 'YEARLY')
parser.add_argument('--tags', help = 'filter by tag, specified as a name:value pair', action = 'append')
parser.add_argument('--aws-region', default = 'us-east-1', help = 'AWS region', metavar ='REGION')
parser.add_argument('--aws-access', required = True, help = 'AWS access key', metavar = 'KEY')
parser.add_argument('--aws-secret', required = True, help = 'AWS secret key', metavar = 'KEY')
parser.add_argument('--aws-owner', required = True, help = 'AWS account ID')
parser.add_argument('--debug', help = 'print debugging information to screen', action = 'store_true')
args = parser.parse_args()

windows = [ 'hourly', 'daily', 'weekly', 'monthly', 'yearly' ]
window_sizes = {
    windows[0]: 60*60,
    windows[1]: 60*60*24,
    windows[2]: 60*60*24*7,
    windows[3]: 60*60*24*30,
    windows[4]: 60*60*24*365
}
keep_per_window = {
    windows[0]: 0,
    windows[1]: 0,
    windows[2]: 0,
    windows[3]: 0,
    windows[4]: 0
}
if args.keep_hourly:
    keep_per_window['hourly'] = args.keep_hourly
if args.keep_daily:
    keep_per_window['daily'] = args.keep_daily
if args.keep_weekly:
    keep_per_window['weekly'] = args.keep_weekly
if args.keep_monthly:
    keep_per_window['monthly'] = args.keep_monthly
if args.keep_yearly:
    keep_per_window['yearly'] = args.keep_yearly

max_retries = args.max_retries
dry_run = args.dry_run
tags = args.tags
aws_region = args.aws_region
aws_access = args.aws_access
aws_secret = args.aws_secret
aws_owner = args.aws_owner
debug = args.debug


# setup logging
if debug:
    logging.basicConfig(format = '%(asctime)s %(levelname)s: %(message)s', level = logging.DEBUG, datefmt = '%Y/%m/%d %H:%M:%S')
else:
    logging.basicConfig(format = '%(asctime)s %(levelname)s: %(message)s', datefmt = '%Y/%m/%d %H:%M:%S')


# connect to the AWS API
try:
    conn = boto.ec2.connect_to_region(aws_region, aws_access_key_id = aws_access, aws_secret_access_key = aws_secret)
except:
    logging.critical('unable to connect to the AWS API')
    raise


# get list of all snapshots
filters = { "status": "completed" }

if tags:
    for tag in tags:
        (name, value) = string.split(tag, ':')
        filters['tag:'+name] = value

snapshots = conn.get_all_snapshots(filters = filters, owner = aws_owner)

if not snapshots:
    logging.error('no snapshots found')
    sys.exit(-1)


# get the timestamp of every snapshot
timestamps = []

for s in snapshots:
    snapshot_id = s.id
    tags = backoff(max_retries, get_all_tags, conn, s.id)
    timestamp = filter( lambda tag: tag.name == 'Timestamp', tags )
    if timestamp:
        timestamps.append( (s.id, int(timestamp[0].value)) )
    else:
        logging.warning('snapshot "%s" does not have a tag named "Timestamp"' % (s.id))


# do the rotation
now = time.time()

for window in windows:
    timeslice = window_sizes[window]
    keep = keep_per_window[window]

    logging.info('finding last %d %s snapshots (%d second window)' % (keep, window, timeslice))

    for idx in range(0, keep):
        max = now - (idx * timeslice)
        min = max - timeslice
        logging.debug("UET %d to UET %d" % (max, min))
        found = filter( lambda x: x[1] > min and x[1] <= max, timestamps )
        logging.info("found %d %s snapshots (idx = %d, %s to %s)" % (len(found), window, idx, time.ctime(min), time.ctime(max)))

        if not found:
            continue

        found.sort( key = lambda x: x[1], reverse = True)

        f = found.pop(0)
        logging.info('keeping snapshot %s (%s)' % (f[0], time.ctime(f[1])))

        if found:
            for f in found:
                details = 'snapshot %s (%s)' % (f[0], time.ctime(f[1]))
                if dry_run:
                    logging.warn('*would* delete %s' % (details))
                else:
                    logging.info('deleting %s' % (details))
                    backoff( max_retries, conn.delete_snapshot, f[0] )

    now -= keep * timeslice


sys.exit(0)

