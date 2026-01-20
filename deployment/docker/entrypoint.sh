#!/bin/sh
set -e

mkdir -p /data/logs /data/media
chown -R pretixuser:pretixuser /data
chmod 755 /data /data/logs /data/media

if [ -f /data/.secret ]; then
  chmod 640 /data/.secret
fi

exec gosu pretixuser "$@"
