#!/usr/bin/env python


import argparse
import logging
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


logging.basicConfig(format = '%(levelname)s: %(message)s', level = logging.INFO)


parser = argparse.ArgumentParser(description = 'Rotate EBS snapshots', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument('--dry-run', action = 'store_true')
parser.add_argument('--keep-houry', default = 24, type = int, help = 'keep this many hourly snapshots', metavar = 'HOURLY')
parser.add_argument('--keep-daily', default = 7, type = int, help = 'keep this many daily snapshots', metavar = 'DAILY')
parser.add_argument('--keep-weekly', default = 4, type = int, help = 'keep this many weekly snapshots', metavar = 'WEEKLY')
parser.add_argument('--keep-monthly', default = 3, type = int, help = 'keep this many monthly snapshots', metavar = 'MONTHLY')
parser.add_argument('--keep-yearly', default = 1, type = int, help = 'keep this many yearly snapshots', metavar = 'YEARLY')
parser.add_argument('--tags', help = 'filter by tag, specified as a name:value pair', action = 'append')
parser.add_argument('--aws-region', default = 'us-east-1', help = 'AWS region', metavar ='REGION')
parser.add_argument('--aws-access', required = True, help = 'AWS access key', metavar = 'KEY')
parser.add_argument('--aws-secret', required = True, help = 'AWS secret key', metavar = 'KEY')
parser.add_argument('--aws-owner', required = True, help = 'AWS account ID')
args = parser.parse_args()

tags = args.tags
aws_region = args.aws_region
aws_access = args.aws_access
aws_secret = args.aws_secret
aws_owner = args.aws_owner


# connect to the AWS API
try:
    conn = boto.ec2.connect_to_region(aws_region, aws_access_key_id = aws_access, aws_secret_access_key = aws_secret)
except:
    logging.critical('unable to connect to the AWS API')
    sys.exit(-1)


# get list of all snapshots
filters = { "status":"completed" }

if tags:
    for tag in tags:
        (name, value) = string.split(tag, ':')
        filters['tag:'+name] = value

snapshots = conn.get_all_snapshots(filters=filters, owner = aws_owner)
print snapshots

if not snapshots:
    logging.info('no snapshots found')
    sys.exit(-1)


for s in snapshots:
    tags = conn.get_all_tags(filters={'resource-id': s.id})
    print tags



