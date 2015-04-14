# ec2-backup
Backup an EC2 instance by taking a snapshot of the EBS root volume.  Rotate snapshots with configurable aging.

## Backup Script
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
