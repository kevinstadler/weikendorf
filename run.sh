#!/bin/bash

# make newly copied files deletable by www-data group
umask 002
#g+w

while [ -f "run" ]; do
	PYGAME_HIDE_SUPPORT_PROMPT="" ./run.py
done
echo "exiting"

