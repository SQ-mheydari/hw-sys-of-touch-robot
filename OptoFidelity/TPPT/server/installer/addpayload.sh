#!/bin/bash

# argument $1: name of zip file
# pargument $2: Server or UI

# Check for payload format option (default is uuencode).
uuencode=1
if [[ "$1" == '--binary' ]]; then
	binary=1
	uuencode=0
	shift
fi
if [[ "$1" == '--uuencode' ]]; then
	binary=0
	uuencode=1
	shift
fi

if [[ ! "$1" ]]; then
	echo "Usage: $0 [--binary | --uuencode] PAYLOAD_FILE"
	exit 1
fi

ZIP_FILE=$1
LENGTH="$(expr "${#ZIP_FILE}" '-' '4')"
FILE_NAME=${ZIP_FILE::LENGTH}"_Setup.sh"
LENGTH_2="$(expr "${#ZIP_FILE}" '-' '9')"
NEW_FILE=${ZIP_FILE:5:LENGTH_2}

if [[ $binary -ne 0 ]]; then
	# Append binary data.
	sed \
		-e 's/uuencode=./uuencode=0/' \
		-e 's/binary=./binary=1/' \
		-e 's/COMPONENT=/COMPONENT=\"'$2'\"/' \
		-e 's/NEW_FILE=/NEW_FILE=\"'$NEW_FILE'\"/' \
			 install.sh.in >$FILE_NAME
	echo "PAYLOAD:" >> $FILE_NAME

	cat $1 >>$FILE_NAME
fi
if [[ $uuencode -ne 0 ]]; then
	# Append uuencoded data.
	sed \
		-e 's/uuencode=./uuencode=1/' \
		-e 's/binary=./binary=0/' \
		-e 's/COMPONENT=/COMPONENT=\"'$2'\"/' \
		-e 's/NEW_FILE=/NEW_FILE=\"'$NEW_FILE'\"/' \
			 install.sh.in >$FILE_NAME
	echo "PAYLOAD:" >> $FILE_NAME

	cat $1 | uuencode $1 >>$FILE_NAME
	echo "$FILE_NAME"
fi