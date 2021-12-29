import requests


class Notifier:
    def __init__(self, gotify_url):
        self.gotify_url = gotify_url

    def notify(self, msg):
        requests.post(self.gotify_url, json={
            'message': msg,
            'priority': 5,
        })
