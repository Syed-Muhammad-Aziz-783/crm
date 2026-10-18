#!/bin/bash
# Royal fast lane: copy a freshly built app into the running ERPNext containers.
# Usage: /root/hotpatch.sh crm            (code/screen change)
#        /root/hotpatch.sh crm migrate    (also run migrate, for field/doctype changes)
set -e
APP=${1:-crm}
MIGRATE=$2
P=et8nrlohz2nflwxnyetokc3m
IMG=ghcr.io/syed-muhammad-aziz-783/hotpatch-$APP:latest

docker pull -q "$IMG"
ID=$(docker create "$IMG" none)
docker cp "$ID:/$APP.tgz" "/tmp/$APP.tgz"
docker rm "$ID" >/dev/null
docker rmi "$IMG" >/dev/null

for S in frontend backend scheduler queue-long queue-short websocket; do
  C=$S-$P
  docker cp "/tmp/$APP.tgz" "$C:/tmp/$APP.tgz"
  docker exec -u root "$C" sh -c "cd /home/frappe/frappe-bench/apps/$APP && rm -rf $APP/public/frontend && tar xzf /tmp/$APP.tgz --no-same-owner && chown -R frappe:0 . && rm -f /tmp/$APP.tgz"
  echo "patched $C"
done
rm -f "/tmp/$APP.tgz"

docker restart backend-$P scheduler-$P queue-long-$P queue-short-$P websocket-$P >/dev/null
echo "restarted"
if [ "$MIGRATE" = "migrate" ]; then
  docker exec backend-$P bench --site frontend migrate
fi
docker exec backend-$P bench --site frontend clear-cache
echo "HOTPATCH DONE: $APP"
