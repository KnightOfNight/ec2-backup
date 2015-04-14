# ec2-backup
Backup an EC2 instance by taking a snapshot of the EBS root volume.  Rotate snapshots with configurable aging.
## Backup Script
<pre>
usage: ec2-backup.py [-h] --device DEVICE --mount MOUNT [--aws-region REGION]
                     --aws-access KEY --aws-secret KEY [--mysql]
                     [--mysql-stop] [--mysql-lock] [--max-retries RETRIES]
                     [--log-level LOG_LEVEL]

Backup an attached EBS volume

optional arguments:
  -h, --help            show this help message and exit
  --device DEVICE       device name of the attached volume, e.g. /dev/xvda
                        (default: None)
  --mount MOUNT         mount point of the attached volume, e.g. / (default:
                        None)
  --aws-region REGION   AWS region (default: us-east-1)
  --aws-access KEY      AWS access key (default: None)
  --aws-secret KEY      AWS secret key (default: None)
  --mysql               stop MySQL before taking the snapshot and restart it
                        after (default: False)
  --mysql-stop          stop MySQL before taking the snapshot and restart it
                        after (default: False)
  --mysql-lock          lock MySQL before taking the snapshot and unlock it
                        after (default: False)
  --max-retries RETRIES
                        maximum number of API retries before giving up
                        (default: 10)
  --log-level LOG_LEVEL
                        set the log level to increase or decrease verbosity
                        (default: WARNING)
</pre>

## Rotator Script
<pre>
usage: ec2-rotate-snapshots.py [-h] [--keep-hourly HOURLY]
                               [--keep-daily DAILY] [--keep-weekly WEEKLY]
                               [--keep-monthly MONTHLY] [--keep-yearly YEARLY]
                               [--tags TAGS] [--aws-region REGION]
                               --aws-access KEY --aws-secret KEY --aws-owner
                               AWS_OWNER [--max-retries RETRIES] [--dry-run]
                               [--log-level LOG_LEVEL]

Rotate EBS snapshots

optional arguments:
  -h, --help            show this help message and exit
  --keep-hourly HOURLY  keep this many hourly snapshots (default: 24)
  --keep-daily DAILY    keep this many daily snapshots (default: 7)
  --keep-weekly WEEKLY  keep this many weekly snapshots (default: 4)
  --keep-monthly MONTHLY
                        keep this many monthly snapshots (default: 3)
  --keep-yearly YEARLY  keep this many yearly snapshots (default: 1)
  --tags TAGS           filter by tag, specified as a name:value pair
                        (default: None)
  --aws-region REGION   AWS region (default: us-east-1)
  --aws-access KEY      AWS access key (default: None)
  --aws-secret KEY      AWS secret key (default: None)
  --aws-owner AWS_OWNER
                        AWS account ID (default: None)
  --max-retries RETRIES
                        maximum number of API retries before giving up
                        (default: 10)
  --dry-run
  --log-level LOG_LEVEL
                        set the log level to increase or decrease verbosity
                        (default: WARNING)
</pre>
