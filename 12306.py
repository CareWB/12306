# -*- coding: utf-8 -*-

import aiohttp
import asyncio
import async_timeout
import sys
import io
import re
import os

stations = {}
charset = ''
myproxy = ''


stations_url = 'https://kyfw.12306.cn/otn/resources/js/framework/station_name.js'
ticket_url_fmt = 'https://kyfw.12306.cn/otn/leftTicket/queryA?leftTicketDTO.train_date={0}&leftTicketDTO.from_station={1}&leftTicketDTO.to_station={2}&purpose_codes=ADULT'
price_url = 'https://kyfw.12306.cn/otn/leftTicket/queryTicketPrice?train_no=240000G1010C&from_station_no=01&to_station_no=11&seat_types=OM9&train_date=2017-02-08'

sys.stdout = io.TextIOWrapper(sys.stdout.buffer,encoding='gb18030') 
title = ['车次', '出发站', '到达站', '历时', '商务座余票', '商务座价格', '特等座余票', '特等座价格', '一等座余票', '一等座价格', '二等座余票', '二等座价格', '高级软卧余票', '高级软卧价格', '软卧余票', '软卧价格', '硬卧余票', '硬卧价格', '软座余票', '软座价格', '硬座余票', '硬座价格', '无座余票', '无座价格', '其它余票', '其它价格']

async def get_stations(session):
    stations = {}
    charset = ''
    if not os.path.isfile('station_name.js'):
        print('start loading station_name.js')
        charset, html = await fetch(session, stations_url)
        with open('station_name.js', 'wb') as f:
             f.write(html);
    else:
        print('loading local station_name.js')
    with open('station_name.js', encoding='utf-8') as fp:
        data = fp.read()
        data = data.partition('=')[2].strip("'") #var station_names ='..'
    for station in data.split('@')[1:]:
        items = station.split('|') # bjb|北京北|VAP|beijingbei|bjb|0
        stations[ items[1] ] = items[2]
    return stations

async def get_trains(session, date, from_station, to_station):
    print('start getting trains...')
    charset, html = await fetch(session, ticket_url_fmt.format(date, from_station, to_station))
    return charset, html

async def fetch(session, url):
    with async_timeout.timeout(30):
        async with session.get(url) as rsp:
            assert rsp.status == 200
            matchObj = re.match( '.*charset=(.*)', rsp.headers['CONTENT-TYPE'], re.M|re.I)
            charset = matchObj.group(1)
            return charset, await rsp.read()
            
async def main(loop):
    global stations

    with aiohttp.TCPConnector(verify_ssl=False) as conn:
        async with aiohttp.ClientSession(connector=conn, loop=loop) as session:
            stations = await get_stations(session)
            #print(stations)

    with aiohttp.TCPConnector(verify_ssl=False) as conn:
        async with aiohttp.ClientSession(connector=conn, loop=loop) as session:
            charset, trains = await get_trains(session, '2017-02-08', stations['北京'], stations['上海'])
            print(trains.decode(charset))

    with aiohttp.TCPConnector(verify_ssl=False) as conn:
        async with aiohttp.ClientSession(connector=conn, loop=loop) as session:
            charset, html = await fetch(session, 'https://kyfw.12306.cn/otn/leftTicket/queryTicketPrice?train_no=240000G1010C&from_station_no=01&to_station_no=11&seat_types=OM9&train_date=2017-02-08')
            open('text.txt', 'w', encoding=charset).write(html.decode(charset))
            print(html.decode(charset))

loop = asyncio.get_event_loop()
loop.run_until_complete(main(loop))