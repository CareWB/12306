# -*- coding: utf-8 -*-

import aiohttp
import asyncio
import async_timeout
import sys
import io
import re
import os
import json

stations = {}
trains = {}
train_seq = []
charset = ''

myproxy = ''
stations_url = 'https://kyfw.12306.cn/otn/resources/js/framework/station_name.js'
ticket_url_fmt = 'https://kyfw.12306.cn/otn/leftTicket/queryA?leftTicketDTO.train_date={0}&leftTicketDTO.from_station={1}&leftTicketDTO.to_station={2}&purpose_codes=ADULT'
price_url_fmt = 'https://kyfw.12306.cn/otn/leftTicket/queryTicketPrice?train_no={0}&from_station_no={1}&to_station_no={2}&seat_types={3}&train_date={4}'


seat_code = {
  '特等'  : 'P',
  '商务座': '9',
  '一等座': 'M',
  '二等座': 'O',
  '硬座'  : '1',
  '硬卧'  : '3',
  '软卧'  : '4'
}

ticket_info = {
'station_train_code'    :[0,'车次'],
'from_station_name'     :[1,'出发站'],
'to_station_name'       :[2,'到达站'],
'start_time'            :[3,'出发时间'],
'arrive_time'           :[4,'到达时间'],
'lishi'                 :[5,'历时'],
'swz_num'               :[6,'商务座余票'],
'A9'                    :[7,'商务座价格'],
'tz_num'                :[8,'特等座余票'],
'tz_price'              :[9,'特等座价格'],
'zy_num'                :[10,'一等座余票'],
'M'                     :[11,'一等座价格'],
'ze_num'                :[12,'二等座余票'],
'O'                     :[13,'二等座价格'],
'gr_num'                :[14,'高级软卧余票'],
'gr_price'              :[15,'高级软卧价格'],
'rw_num'                :[16,'软卧余票'],
'A4'                    :[17,'软卧价格'],
'yw_num'                :[18,'硬卧余票'],
'A3'                    :[19,'硬卧价格'],
'rz_num'                :[20,'软座余票'],
'rz_price'              :[21,'软座价格'],
'yz_num'                :[22,'硬座余票'],
'A1'                    :[23,'硬座价格'],
'wz_num'                :[24,'无座余票'],
'WZ'                    :[25,'无座价格'],
'qt_num'                :[26,'其它余票'],
'qt_price'              :[27,'其它价格'],
'train_no'              :[28,'train_no'],
'from_station_no'       :[29,'from_station_no'],
'to_station_no'         :[30,'to_station_no'],
'seat_types'            :[31,'seat_types']
}

sys.stdout = io.TextIOWrapper(sys.stdout.buffer,encoding='gb18030') 


async def get_stations(session):
    print('start getting stations...')
    stations = {}
    charset = ''
    if not (os.path.isfile('station_name.js')) or (os.path.getsize('station_name.js') == 0) :
        print('start loading station_name.js')
        charset, html = await fetch(session, stations_url)
        with open('station_name.js', 'wb') as f:
             f.write(html.encode());
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
    trains = {}
    train_seq = []
    
    charset, json = await fetch(session, ticket_url_fmt.format(date, from_station, to_station), 'json')
    for train_data in json['data']:
        if train_data['secretStr'] != '':
        #if train_data['queryLeftNewDTO']['seat_types'] != '':
            train = ['' for i in range(len(ticket_info))]
            train_code = train_data['queryLeftNewDTO']['station_train_code']
            train_seq.append(train_code)
            for k in ticket_info.keys():
                if k in train_data['queryLeftNewDTO']:
                    train[ticket_info[k][0]] = train_data['queryLeftNewDTO'][k]
            trains[train_code] = train
    return train_seq, trains
    
async def get_price(session, station_train_code, train_no, from_station_no, to_station_no, seat_types, train_date):
    global trains
    print(price_url_fmt.format(train_no, from_station_no, to_station_no, seat_types, train_date))
    charset, json = await fetch(session, price_url_fmt.format(train_no, from_station_no, to_station_no, seat_types, train_date), 'json')
    for k in json['data']:
        if k in ticket_info:
            price = json['data'][k]
            if price.find(u'¥') >= 0:
                trains[station_train_code][ticket_info[k][0]] = json['data'][k][1:]

async def fetch(session, url, format="html"):
    with async_timeout.timeout(30):
        async with session.get(url) as rsp:
            assert rsp.status == 200
            
            charset = 'utf-8'
            if 'CONTENT-TYPE' in rsp.headers:
                matchObj = re.match( '.*charset=(.*)', rsp.headers['CONTENT-TYPE'], re.M|re.I)
                if matchObj != None:
                    charset = matchObj.group(1)
            if format == "json":
                return charset, await rsp.json(encoding=charset)
            else:
                return charset, await rsp.text(encoding=charset)
            
async def main(loop):
    global trains
    global train_seq
    global stations
    with aiohttp.TCPConnector(verify_ssl=False) as conn:
        async with aiohttp.ClientSession(connector=conn, loop=loop) as session:
            stations = await get_stations(session)
            #print(stations)

    with aiohttp.TCPConnector(verify_ssl=False) as conn:
        async with aiohttp.ClientSession(connector=conn, loop=loop) as session:
            train_seq, trains = await get_trains(session, '2017-02-08', stations['北京'], stations['上海'])
            #print(trains)
    
    for train in train_seq:
        with aiohttp.TCPConnector(verify_ssl=False) as conn:
            async with aiohttp.ClientSession(connector=conn, loop=loop) as session:
                await get_price(session, trains[train][ticket_info['station_train_code'][0]], trains[train][ticket_info['train_no'][0]], trains[train][ticket_info['from_station_no'][0]], trains[train][ticket_info['to_station_no'][0]], trains[train][ticket_info['seat_types'][0]],'2017-02-08')

    print(trains)

loop = asyncio.get_event_loop()
loop.run_until_complete(main(loop))