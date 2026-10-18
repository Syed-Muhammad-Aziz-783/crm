#!/bin/bash
# Royal auto updater. Runs from cron every 2 minutes.
# Patches the running containers when (a) a new fast-lane build is on ghcr,
# or (b) the containers were recreated (Coolify redeploy) and lost the patch.
# Install once:  /root/auto-hotpatch.sh install
P=et8nrlohz2nflwxnyetokc3m
APP=crm
IMG=ghcr.io/syed-muhammad-aziz-783/hotpatch-$APP:latest
STATE=/root/.royal-hotpatch-state
LOG=/var/log/royal-auto.log

digest() { docker buildx imagetools inspect "$IMG" --format '{{.Manifest.Digest}}' 2>/dev/null; }

if [ "$1" = "install" ]; then
  chmod +x /root/auto-hotpatch.sh
  ( crontab -l 2>/dev/null | grep -v 'auto-hotpatch.sh' | grep -v 'update-crm.sh'
    echo "*/2 * * * * /root/auto-hotpatch.sh >> $LOG 2>&1"
    echo "0 3 * * * /root/update-crm.sh >> $LOG 2>&1" ) | crontab -
  echo "cron installed:"; crontab -l
  D=$(digest)
  if [ -z "$D" ]; then echo "WARNING: cannot read ghcr digest. Auto patch will NOT work. Send this to Claude."; else echo "digest check OK: $D"; fi
  exit 0
fi

exec 9>/var/lock/royal-auto.lock
flock -n 9 || exit 0

D=$(digest)
[ -z "$D" ] && exit 0
C=$(docker inspect -f '{{.Id}}' "backend-$P" 2>/dev/null)
[ -z "$C" ] && exit 0
NOW="$D $C"
[ "$(cat "$STATE" 2>/dev/null)" = "$NOW" ] && exit 0

echo "$(date '+%F %T') change found, patching"
if /root/hotpatch.sh "$APP"; then
  echo "$(date '+%F %T') AUTO PATCH OK"
else
  echo "$(date '+%F %T') AUTO PATCH FAILED - run /root/hotpatch.sh $APP by hand"
fi
echo "$NOW" > "$STATE"
