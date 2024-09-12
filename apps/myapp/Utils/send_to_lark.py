import requests
import json

from core import settings

def send_message_to_optlark(message):
    webhook_url = settings.opt_LARK_WEBHOOK_URL  # 替换为你的机器人Webhook URL
    headers = {'Content-Type': 'application/json; charset=utf-8'}
    data = {
        "msg_type": "text",  # 使用文本类型消息，飞书还支持其他类型如：post, image, file 等
        "content": {
            "text": message
        }
    }

    response = requests.post(webhook_url, headers=headers, data=json.dumps(data))

    if response.status_code == 200:
        print("Message sent successfully")
    else:
        print("Failed to send message, status code:", response.status_code)

def send_message_to_spclark(message):
    webhook_url = settings.spc_LARK_WEBHOOK_URL  # 替换为你的SPC群的Webhook URL
    headers = {'Content-Type': 'application/json; charset=utf-8'}
    data = {
        "msg_type": "text",  # 使用文本类型消息，飞书还支持其他类型如：post, image, file 等
        "content": {
            "text": message
        }
    }

    response = requests.post(webhook_url, headers=headers, data=json.dumps(data))

    if response.status_code == 200:
        print("Message sent successfully")
    else:
        print("Failed to send message, status code:", response.status_code)

def send_message_to_streamlark(message):
    webhook_url = settings.stream_LARK_WEBHOOK_URL  # 替换为你的SPC群的Webhook URL
    headers = {'Content-Type': 'application/json; charset=utf-8'}
    data = {
        "msg_type": "text",  # 使用文本类型消息，飞书还支持其他类型如：post, image, file 等
        "content": {
            "text": message
        }
    }

    response = requests.post(webhook_url, headers=headers, data=json.dumps(data))

    if response.status_code == 200:
        print("Message sent successfully")
    else:
        print("Failed to send message, status code:", response.status_code)

def send_message_to_Vodlark(message):
    webhook_url = settings.VOD_LARK_WEBHOOK_URL  # 替换为你的SPC群的Webhook URL
    headers = {'Content-Type': 'application/json; charset=utf-8'}
    data = {
        "msg_type": "text",  # 使用文本类型消息，飞书还支持其他类型如：post, image, file 等
        "content": {
            "text": message
        }
    }

    response = requests.post(webhook_url, headers=headers, data=json.dumps(data))

    if response.status_code == 200:
        print("Message sent successfully")
    else:
        print("Failed to send message, status code:", response.status_code)

