all: pylint pylint3

pylint:
	@echo pylint ec2_backup
	@python -m pylint ec2_backup.py
	@echo pylint backoff
	@python -m pylint backoff.py
	@echo pylint mysql
	@python -m pylint mysql.py

pylint3:
	@echo pylint v3 ec2_backup
	@python3 -m pylint ec2_backup.py
	@echo pylint v3 backoff
	@python3 -m pylint backoff.py
