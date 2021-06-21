import datetime
import os
import json
from pprint import pprint

import requests
from kubernetes import client, config, watch
import pytz

DEBUG = eval(os.environ.get('DEBUG', "False"))


def alert(webhook_url, icon_url, key, t, notification_log):
    if key in notification_log:
        if notification_log[key] + datetime.timedelta(minutes=1) > t.finished_at:
            return

    notification_log[key] = t.finished_at

    if t.signal:
        signal = f'(signal:{t.signal})'
    else:
        signal = ''

    jst = pytz.timezone('Asia/Tokyo')
    now = jst.localize(datetime.datetime.now())
    if t.finished_at < now - datetime.timedelta(minutes=30):
        return

    if DEBUG:
        pprint({'key': key, 'value': t})

    if webhook_url:
        requests.post(webhook_url, data=json.dumps({
            "attachments": [
                {
                    "fallback": f"{key} killed. reason: {t.reason}",
                    "color": "#dc3545",
                    "pretext": "Container killed",

                    "text": f"{key}",
                    "fields": [
                        {
                            "title": "reason",
                            "value": t.reason,
                            "short": True,
                        },
                        {
                            "title": "code",
                            "value": f"{t.exit_code}{signal}",
                            "short": True,
                        },

                    ],
                    "ts": datetime.datetime.timestamp(t.finished_at),
                }
            ],
            "icon_url": icon_url,
            "username": "k8s-alert-oom",
        }))


def main():
    in_cluster = eval(os.environ.get('IN_CLUSTER', "False"))
    if in_cluster:
        config.load_incluster_config()
    else:
        config.load_kube_config()
    webhook_url = os.environ.get('WEBHOOK_URL', None)
    icon_url = os.environ.get('ICON_URL', None)

    v1 = client.CoreV1Api()
    w = watch.Watch()

    notification_log = {}
    memo = {}
    for event in w.stream(v1.list_pod_for_all_namespaces):
        object = event['object']

        namespace = object.metadata.namespace
        pod_name = object.metadata.name

        for cs in object.status.container_statuses or []:
            container_name = cs.name
            key = f"{namespace}/{pod_name}/{container_name}"

            if not cs.state:
                continue

            if hasattr(cs, 'last_state') and cs.last_state.terminated:
                t = cs.last_state.terminated
                if 'OOM' in t.reason:
                    if (key not in memo) or memo[key] + datetime.timedelta(minutes=1) < t.finished_at:
                        alert(webhook_url, icon_url, key, t, notification_log)

            if cs.state.terminated:
                t = cs.state.terminated
                if 'OOM' in t.reason:
                    alert(webhook_url, icon_url, key, t, notification_log)
                elif DEBUG:
                    pprint({'key': key, 'value': t})

                    
if __name__ == '__main__':
    health_filename = '/tmp/healthchecks-sendalerts-alive'
    with open(health_filename, 'w') as fp:
        fp.write("alive")

    try:
        main()
    finally:
        if os.path.exists(health_filename):
            os.remove(health_filename)
