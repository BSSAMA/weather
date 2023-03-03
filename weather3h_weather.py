#!/usr/bin/env python3
"""
cron: 1 0 7-21/3 * * ?
new Env('3小时判断一次天气');
"""
import sys
import requests
import json
import time
import ast
from bs4 import BeautifulSoup
import os, re

# 获取WxPusher appToken  WxPusher_appToken
if "WxPusher_appToken" in os.environ:
    if len(os.environ["WxPusher_appToken"]) > 1:
        WxPusher_appToken = os.environ["WxPusher_appToken"]
else:
    print('未配置环境变量 WxPusher_appToken')
    sys.exit()

# 获取WxPusher uid  WxPusher_uids ','分隔
if "WxPusher_uids" in os.environ:
    if len(os.environ["WxPusher_uids"]) > 1:
        WxPusher_uids = os.environ["WxPusher_uids"].split(',')
else:
    print('未配置环境变量 WxPusher_uids')
    sys.exit()

def get_cookies():
    # 字符串前加r 防止转义
    url = r'https://tianqi.moji.com/weather/china/henan/wenfeng-district'
    head = {
        "Host": "tianqi.moji.com",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/106.0.0.0 Safari/537.36 "
    }
    r = requests.get(url, headers=head)
    cookie = r.cookies
    r.encoding = "utf-8"
    soup = BeautifulSoup(r.text, 'lxml')
    now_temp = soup.select('body > div.wrap.clearfix.wea_info > div.left > div.wea_weather.clearfix > em')[0].text
    now_wea = soup.select('body > div.wrap.clearfix.wea_info > div.left > div.wea_weather.clearfix > b')[0].text
    return cookie, now_temp, now_wea


def get_24weather_data(temps):
    """
    获取当前到次日凌晨的每小时气温和未来5天的每天最低气温
    """
    cookie, now_temp, now_wea = temps
    head = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/106.0.0.0 Safari/537.36 "
    }
    url = r'https://tianqi.moji.com/index/getHour24'
    print('正在请求天气信息...')
    r = requests.get(url, headers=head, cookies=cookie)
    weather24 = ast.literal_eval(r.text)['hour24']
    if weather24[0]['Fpredict_hour'] <= int(time.strftime('%H')):
        weather24.pop(0)
    return weather24, now_temp, now_wea

def analyse_weather(temps):
    """
    分析气温变化，判断要不要发送消息提醒，如果不需要提醒，返回空字符串
    :param temps: 天气信息
    :return: 返回发送消息提醒的文本内容
    """

    weather24, now_temp, now_wea = temps
    message = ''

    print('当前气温: {},当前天气: {}'.format(now_temp,now_wea))
    print('未来3小时气温: {},{},{}'.format(weather24[0]['Ftemp'], weather24[1]['Ftemp'], weather24[2]['Ftemp']))
    print('未来3小时天气: {},{},{}'.format(weather24[0]['Fcondition'], weather24[1]['Fcondition'], weather24[2]['Fcondition']))

    for i, w in enumerate(weather24):
        if i < 4:  # 3小时内的天气变化
            if (w['Fcondition'] not in ('晴', '多云', '阴')) and (now_wea in ('晴', '多云', '阴')):
                message += '在{}:00将会是 {} 天气。\n'.format(w['Fpredict_hour'], w['Fcondition'])
                break

    return message


def send_reminder(message):
    url = 'http://wxpusher.zjiecode.com/api/send/message'

    headers = {
        'Content-Type': 'application/json'
    }

    data = {
        'appToken': WxPusher_appToken,
        'content': message,
        # 'summary': '消息摘要', # 消息摘要，显示在微信聊天页面或者模版消息卡片上，限制长度100，可以不传，不传默认截取content前面的内容。
        'contentType': 1,  # 内容类型 1表示文字 2表示html(只发送body标签内部的数据即可，不包括body标签) 3表示markdown
        # 'topicIds': [], # 发送目标的topicId，是一个数组！！！，也就是群发，使用uids单发的时候， 可以不传。
        # 'uids': ['', '']  # 发送目标的UID，是一个数组。注意uids和topicIds可以同时填写，也可以只填写一个。
        'uids': WxPusher_uids
        # 'url': "" # 原文链接，可选参数
    }

    if not message:
        print('气温变化适宜，不用发送消息提醒。')
        return
    r = requests.post(headers=headers, url=url, data=json.dumps(data))
    if r.status_code == 200:
        print('发送提醒成功,message:')
        print(message)
    else:
        print('发送提醒失败,status_code:', r.status_code)


if __name__ == '__main__':
    print('现在是{}'.format(time.strftime('%Y-%m-%d %H:%M')))
    temp = get_cookies()
    temp_wea = get_24weather_data(temp)
    message_text = analyse_weather(temp_wea)
    print('message:' + message_text)
    send_reminder(message_text)
