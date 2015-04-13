#!/usr/bin/env python


import argparse
import logging
import os
import sys
import subprocess
import time
import boto.utils
import boto.ec2
from backoff import backoff
from mysql import lock


fsfreeze = '/sbin/fsfreeze'


version = sys.hexversion
if version < 0x02070000:
    sys.stderr.write('python 2.7 or higher required\n')
    sys.exit(-1)


def fs_freeze(mount):
    logging.info('freezing filesystem')
    ret = subprocess.call( [ fsfreeze, '-f', mount ] )
    if ret:
        logging.critical('failed to freeze filesystem')
        sys.exit(-1)


def fs_thaw(mount):
    logging.info('thawing filesystem')
    ret = subprocess.call( [ fsfreeze, '-u', mount ] )
    if ret:
        logging.critical('failed to thaw filesystem')


# parse command line arguments
parser = argparse.ArgumentParser(description = 'Backup an attached EBS volume', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument('--device', required = True, help = 'device name of the attached volume, e.g. /dev/xvda')
parser.add_argument('--mount', required = True, help = 'mount point of the attached volume, e.g. /')
parser.add_argument('--aws-region', default = 'us-east-1', help = 'AWS region', metavar ='REGION')
parser.add_argument('--aws-access', required = True, help = 'AWS access key', metavar = 'KEY')
parser.add_argument('--aws-secret', required = True, help = 'AWS secret key', metavar = 'KEY')
parser.add_argument('--mysql', help = 'stop MySQL before taking the snapshot and restart it after', action='store_true')
parser.add_argument('--mysql-stop', help = 'stop MySQL before taking the snapshot and restart it after', action='store_true')
parser.add_argument('--mysql-lock', help = 'lock MySQL before taking the snapshot and unlock it after', action='store_true')
parser.add_argument('--max-retries', default = 10, type = int, help = 'maximum number of API retries before giving up', metavar = 'RETRIES')
parser.add_argument('--log-level', help = 'set the log level to increase or decrease verbosity', default = 'WARNING')
args = parser.parse_args()

device = args.device
mount = args.mount
aws_region = args.aws_region
aws_access = args.aws_access
aws_secret = args.aws_secret
mysql_stop = args.mysql_stop
mysql_lock = args.mysql_lock
max_retries = args.max_retries
log_level = args.log_level


# setup logging
logging.basicConfig(format = '%(asctime)s %(levelname)s: %(message)s', level = getattr(logging, log_level.upper()), datefmt = '%Y/%m/%d %H:%M:%S')


# connect to the AWS API
try:
    conn = boto.ec2.connect_to_region(aws_region, aws_access_key_id = aws_access, aws_secret_access_key = aws_secret)
except:
    logging.critical('unable to connect to the AWS API')
    raise


# get the instance ID
try:
    meta = boto.utils.get_instance_metadata()
except:
    logging.critical('unable to get instance meta information')
    raise

instance_id = meta['instance-id']
logging.info('instance ID = "%s"' % instance_id)


# get the volume ID of the volume to be snapshotted
try:
    instance_vols = conn.get_all_volumes(filters={'attachment.instance-id': instance_id})
except:
    logging.critical('unable to get volumes')
    raise

matching_vols = [v for v in instance_vols if v.attach_data.device == device]

if not matching_vols:
    logging.critical('unable to find a volume attached at device "%s"' % device)
    sys.exit(-1)

volume = matching_vols[0]
volume_id = volume.id
logging.info('volume ID = "%s"' % volume_id)


# get the name tag of the instance
try:
    all_tags = conn.get_all_tags(filters={'resource-id': instance_id})
except:
    logging.critical('unable to get tags')
    raise

tags = filter(lambda tag: tag.name == 'Name', all_tags)

if not tags:
    logging.critical('unable to find Name tag for instance "%s"' % instance_id)
    sys.exit(-1)

instance_name_tag = tags[0].value
timestamp_tag = str(int(time.time()))


# handle mysql
if mysql_stop:
    mysql = mysql.stop()
    mysql.green()

elif mysql_lock:
    mysql = mysql.lock()
    mysql.green()

else:
    mysql = None


# take the snapshot
fs_freeze(mount)

logging.info('taking snapshot')

try:
    snapshot = volume.create_snapshot(description = 'Created by backup.py')

except:
    fs_thaw(mount)
    if mysql:
        mysql.red()
    logging.critical('snapshot failed')
    raise

fs_thaw(mount)


# handle mysql
if mysql:
    mysql.red()


# tag the snapshot
snapshot_id = snapshot.id

logging.info('snapshot ID = "%s"' % snapshot_id)

logging.info('waiting for snapshot to appear')

snapshots = backoff(max_retries, conn.get_all_snapshots, [snapshot_id])

backoff(max_retries, snapshot.add_tag, 'Name', instance_name_tag + '-' + timestamp_tag)
backoff(max_retries, snapshot.add_tag, 'Timestamp', timestamp_tag)
backoff(max_retries, snapshot.add_tag, 'Instance', instance_name_tag)


# exit
logging.info('snapshot created and tagged successfully')
sys.exit(0)

