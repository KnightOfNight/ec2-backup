#!/usr/bin/env python


import argparse
import logging
import os
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
parser.add_argument('--tag', help = 'filter by tag, specified as a name:value pair', action = 'append')
parser.add_argument('--aws-region', default = 'us-east-1', help = 'AWS region', metavar ='REGION')
parser.add_argument('--aws-access', required = True, help = 'AWS access key', metavar = 'KEY')
parser.add_argument('--aws-secret', required = True, help = 'AWS secret key', metavar = 'KEY')
args = parser.parse_args()

tags = args.tag
aws_region = args.aws_region
aws_access = args.aws_access
aws_secret = args.aws_secret


# connect to the AWS API
try:
    conn = boto.ec2.connect_to_region(aws_region, aws_access_key_id = aws_access, aws_secret_access_key = aws_secret)
except:
    logging.critical('unable to connect to the AWS API')
    sys.exit(-1)


# get list of all snapshots
filters = { "status":"completed" }

for tag in tags:
    (name, value) = split(tag, ':')
    filters['tag:'+name] = value

snapshots = conn.get_all_snapshots(filters=filters)
print snapshots

for s in snapshots:
    tags = conn.get_all_tags(filters={'resource-id': s.id})
    print tags



