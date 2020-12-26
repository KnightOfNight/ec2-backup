#!/usr/bin/env python3

"""Take a snapshot of an EBS volume"""

import argparse
import logging
import sys
import subprocess
import time
import boto.utils
import boto.ec2
import backoff

_FSFREEZE = '/sbin/fsfreeze'

def fs_freeze(mount):
    """Freeze a filesystem"""
    logging.info('freezing filesystem')
    ret = subprocess.call([_FSFREEZE, '-f', mount])
    if ret:
        logging.critical('failed to freeze filesystem')
        sys.exit(-1)

def fs_thaw(mount):
    """Thaw a filesystem"""
    logging.info('thawing filesystem')
    ret = subprocess.call([_FSFREEZE, '-u', mount])
    if ret:
        logging.critical('failed to thaw filesystem')

def parse_args():
    """parse CLI args"""
    parser = argparse.ArgumentParser(description='Backup an attached EBS volume',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('--device',
                        required=True,
                        help='name of the device to snapshot, e.g. /dev/xvda')

    parser.add_argument('--mount',
                        required=True,
                        help='mount point of the volume to snapshot, e.g. /')

    parser.add_argument('--aws-region',
                        default='us-east-1',
                        metavar='REGION',
                        help='AWS region')

    parser.add_argument('--aws-access',
                        required=True,
                        metavar='ACCESS',
                        help='AWS access key')

    parser.add_argument('--aws-secret',
                        required=True,
                        metavar='ACCESS',
                        help='AWS secret key')

    parser.add_argument('--aws-retries',
                        type=int,
                        default=10,
                        metavar='RETRIES',
                        help='maximum number of API retries before giving up')

    parser.add_argument('--log-level',
                        default='WARNING',
                        help='set log level')

    args = parser.parse_args()

    return args

def main():
    """Main"""
    # pylint: disable=too-many-locals
    # pylint: disable=too-many-branches
    # pylint: disable=too-many-statements
    version = sys.hexversion
    if version < 0x03070000:
        sys.stderr.write('python 3.7 or higher required\n')
        sys.exit(-1)

    # parse command line arguments
    args = parse_args()

    # setup logging
    logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s',
                        level=getattr(logging, args.log_level.upper()),
                        datefmt='%Y/%m/%d %H:%M:%S')

    # connect to the AWS API
    try:
        conn = boto.ec2.connect_to_region(args.aws_region,
                                          aws_access_key_id=args.aws_access,
                                          aws_secret_access_key=args.aws_secret)
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
    logging.info("instance ID = '%s'", instance_id)

    # get the ID of the volume
    try:
        instance_vols = conn.get_all_volumes(filters={'attachment.instance-id': instance_id})
    except:
        logging.critical('unable to get volumes')
        raise

    matching_vols = [v for v in instance_vols if v.attach_data.device == args.device]

    if not matching_vols:
        logging.critical("unable to find a volume attached at device '%s'", args.device)
        sys.exit(-1)

    volume = matching_vols[0]
    volume_id = volume.id
    logging.info("volume ID = '%s'", volume_id)

    # get the name of the current instance
    try:
        all_tags = conn.get_all_tags(filters={'resource-id': instance_id})
    except:
        logging.critical('unable to get tags')
        raise

    tags = [t for t in all_tags if t.name == 'Name']

    if not tags:
        logging.critical("unable to find Name tag for instance '%s'", instance_id)
        sys.exit(-1)

    instance_name_tag = tags[0].value
    timestamp_tag = str(int(time.time()))

    # take the snapshot
    fs_freeze(args.mount)

    logging.info('taking snapshot')

    try:
        snapshot = volume.create_snapshot(description='Created by backup.py')
    except:
        logging.critical('snapshot failed')
        raise
    finally:
        fs_thaw(args.mount)

    # tag the snapshot
    snapshot_id = snapshot.id

    logging.info("snapshot ID = '%s'", snapshot_id)

    logging.info('waiting for snapshot to appear')

    backoff.backoff(args.aws_retries, conn.get_all_snapshots, [snapshot_id])

    backoff.backoff(args.aws_retries,
                    snapshot.add_tag,
                    'Name', instance_name_tag + '-' + timestamp_tag)
    backoff.backoff(args.aws_retries,
                    snapshot.add_tag,
                    'Timestamp', timestamp_tag)
    backoff.backoff(args.aws_retries,
                    snapshot.add_tag,
                    'Instance', instance_name_tag)

    # exit
    logging.info('snapshot created and tagged successfully')
    sys.exit(0)

main()
