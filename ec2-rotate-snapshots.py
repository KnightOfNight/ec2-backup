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
from backoff import backoff


version = sys.hexversion
if version < 0x02070000:
    sys.stderr.write('python 2.7 or higher required\n')
    sys.exit(-1)


# parse command line arguments
parser = argparse.ArgumentParser(description = 'Rotate EBS snapshots', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument('--dry-run', help = 'do not delete any snapshots', action = 'store_true')
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
parser.add_argument('--aws-retries', default = 10, type = int, help = 'maximum number of API retries before giving up', metavar = 'RETRIES')
parser.add_argument('--log-level', help = 'set the log level to increase or decrease verbosity', default = 'WARNING')
args = parser.parse_args()

dry_run = args.dry_run

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

tags = args.tags
aws_region = args.aws_region
aws_access = args.aws_access
aws_secret = args.aws_secret
aws_owner = args.aws_owner
aws_retries = args.aws_retries
log_level = args.log_level


# setup logging
logging.basicConfig(format = '%(asctime)s %(levelname)s: %(message)s', level = getattr(logging, log_level.upper()), datefmt = '%Y/%m/%d %H:%M:%S')


# connect to the AWS API
try:
    conn = boto.ec2.connect_to_region(aws_region, aws_access_key_id = aws_access, aws_secret_access_key = aws_secret)
except:
    logging.critical('unable to connect to the AWS API')
    raise


# get list of all snapshots
filters = { 'status': 'completed' }

if tags:
    for tag in tags:
        (name, value) = string.split(tag, ':')
        filters['tag:'+name] = value

snapshots = backoff(aws_retries, conn.get_all_snapshots, filters = filters, owner = aws_owner)

if not snapshots:
    logging.error('no snapshots found')
    sys.exit(-1)

logging.info('found %d completed snapshots that match the tags "%s"' % (len(snapshots), ', '.join(tags)))


# get the timestamp of every snapshot
timestamps = []

for s in snapshots:
    snapshot_id = s.id
    tags = backoff(aws_retries, conn.get_all_tags, filters = {'resource-id': snapshot_id})
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

    logging.info('finding last %d %s snapshots (%d second window)' % (keep, window.upper(), timeslice))

    for idx in range(0, keep):
        max = now - (idx * timeslice)
        min = max - timeslice

        logging.debug('UET %d to UET %d' % (max, min))

        found = filter( lambda x: x[1] > min and x[1] <= max, timestamps )
        found.sort( key = lambda x: x[1], reverse = True)
        logging.info('found %d %s snapshots (idx = %d, %s to %s)' % (len(found), window.upper(), idx, time.ctime(min), time.ctime(max)))

        if not found:
            continue

        # pop the last (oldest) item, it's the keeper
        f = found.pop()
        logging.info('KEEP snapshot %s (%s)' % (f[0], time.ctime(f[1])))

        if not found:
            continue

        for f in found:
            details = 'snapshot %s (%s)' % (f[0], time.ctime(f[1]))
            if dry_run:
                logging.warn('*WOULD DELETE* %s' % (details))
            else:
                logging.info('DELETE %s' % (details))
                backoff( aws_retries, conn.delete_snapshot, f[0] )

    now -= keep * timeslice

max = now
min = 0
logging.info('finding all other snapshots')
logging.debug('UET %d to UET %d' % (max, min))
found = filter( lambda x: x[1] > min and x[1] <= max, timestamps )
found.sort( key = lambda x: x[1], reverse = True)
logging.info('found %d remaining snapshots (%s to %s)' % (len(found), time.ctime(min), time.ctime(max)))
for f in found:
    details = 'snapshot %s (%s)' % (f[0], time.ctime(f[1]))
    if dry_run:
        logging.warn('*WOULD DELETE* %s' % (details))
    else:
        logging.info('DELETE %s' % (details))
        backoff( aws_retries, conn.delete_snapshot, f[0] )


sys.exit(0)

