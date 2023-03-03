#!/usr/bin/env python3
"""
cron: 0 40 22 * * *
new Env('明日天气');
"""
import sys
import requests
import json
import time
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

    
def get_weather_data(city_id):
    """
    获取当前到次日凌晨的每小时气温和未来5天的每天最低气温
    """
    head = {
        "referer": "http://m.weather.com.cn/",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/100.0.4896.127 Safari/537.36 Edg/100.0.1185.44 "
    }
    timestamp = str(int(time.time())) + '761'
    url = r'https://d1.weather.com.cn/wap_40d/{}.html?_={}'.format(city_id, timestamp)
    print('正在请求天气信息...')
    r = requests.get(url, headers=head)
    if r.status_code != 200:
        print('status code:', r.status_code)
        return False

    r.encoding = r.apparent_encoding
    html = r.text.split(';')  # html[0]为40天预报  html[2]为48小时预报

    weather40 = html[0][html[0].find('['):]
    tomorrow = {}
    i = 0
    for day in json.loads(weather40):
        if int(day['009']) < int(time.strftime('%Y%m%d')):
            continue  # 009是日期，如果日期小于今天则舍去
        if int(day['009']) == int(time.strftime('%Y%m%d')):
            i = i + 1
            continue
        if i == 1:
            tomorrow = day
            i = i + 1
        else:
            break
    return tomorrow


def analyse_weather(tomorrow):
    """
    分析气温变化，判断要不要发送消息提醒，如果不需要提醒，返回空字符串
    :param tomorrow: 明天天气信息
    :return: 返回发送消息提醒的文本内容
    """

    message = ''

    moji_url = 'https://tianqi.moji.com/weather/china/henan/anyang'

    headers = {
        'Host': 'tianqi.moji.com',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 Safari/537.36',
    }

    r = requests.get(moji_url, headers=headers)
    r.encoding = "utf-8"
    soup = BeautifulSoup(r.text, 'lxml')
    today_temp = soup.select('body > div:nth-child(5) > div.left > div.forecast.clearfix > ul:nth-child(2) > '
                             'li:nth-child(3)')[0].text.replace(" ", "").replace("°", "")
    today_min_temp, today_max_temp = today_temp.split('/')
    tomorrow_temp = soup.select('body > div:nth-child(5) > div.left > div.forecast.clearfix > ul:nth-child(3) > '
                                'li:nth-child(3)')[0].text.replace(" ", "")
    tomorrow_min_temp, tomorrow_max_temp = tomorrow_temp.replace("°", "").split('/')
    tomorrow_weather = soup.select('body > div:nth-child(5) > div.left > div.forecast.clearfix > ul:nth-child(3) > '
                                   'li:nth-child(2)')[0].text.strip()

    # 明日天气
    today_avg_temp = (int(today_min_temp) + int(today_max_temp)) / 2
    tomorrow_avg_temp = (int(tomorrow_min_temp) + int(tomorrow_max_temp)) / 2
    diff = today_avg_temp - tomorrow_avg_temp
    print(diff)
    if diff > 5:
        message += '明日降温,平均温度下降{}℃\n'.format(diff)
    elif diff < -5:
        message += '明日升温,平均温度上升{}℃\n'.format(diff)
    year, month, days = time.strftime('%Y-%m-%d', time.strptime(tomorrow['009'], '%Y%m%d')).split('-')
    message += '明 日: {}年{}月{}日 {}\n'.format(year, month, days, tomorrow['016'])
    message += '天 气: {}\n'.format(tomorrow_weather)
    message += '温 度: {}\n'.format(tomorrow_temp)
    message += '农 历: {}\n'.format(tomorrow['010'])
    if tomorrow['017'] != '':
        message += '节 日: {}\n'.format(tomorrow['017'])
    if tomorrow['018'] != '':
        message += '节 气: {}\n'.format(tomorrow['018'])
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
        'uids':WxPusher_uids
        # 'url': "" # 原文链接，可选参数
    }

    if not message:
        print('气温变化适宜，不用发送消息提醒')
        return
    r = requests.post(headers=headers, url=url, data=json.dumps(data))
    if r.status_code == 200:
        print('发送提醒成功,message:')
        print(message)
    else:
        print('发送提醒失败，status_code:', r.status_code)


if __name__ == '__main__':
    cityID = '101180201'  # 安阳
    assert cityID

    time5 = time24 = time5_2 = time24_2 = 0
    print('现在是{}'.format(time.strftime('%Y-%m-%d %H:%M')))
    tomorrow = get_weather_data(cityID)
    assert tomorrow
    message = analyse_weather(tomorrow)
    assert message
    send_reminder(message)
