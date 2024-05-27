import requests
from json import loads
from time import sleep
import re
import csv

from database import Database

AUTH = {
    "device_id": "a53f5e06-4663-4091-b046-85a9e5c05299",
    "user_agent": "Instagram 331.0.0.37.90 Android (26/8.0.0; 480dpi; 1080x1920; samsung; SM-G935F; hero2lte; samsungexynos8890; ru_RU; 598808576)",
    "authorization": "Bearer IGT:2:eyJkc191c2VyX2lkIjoiNjY0MzMyNTEzODMiLCJzZXNzaW9uaWQiOiI2NjQzMzI1MTM4MyUzQXpGMnpnOVo5cll1aEFnJTNBMjYlM0FBWWVENjdXNzFJMjVlUVVJZm1kdmV5TlJubm9YVDZWZDdSYURfS1J3MmcifQ=="
}
# a53f5e06-4663-4091-b046-85a9e5c05299
# Bearer IGT:2:eyJkc191c2VyX2lkIjoiNjY0MzMyNTEzODMiLCJzZXNzaW9uaWQiOiI2NjQzMzI1MTM4MyUzQXpGMnpnOVo5cll1aEFnJTNBMjYlM0FBWWVENjdXNzFJMjVlUVVJZm1kdmV5TlJubm9YVDZWZDdSYURfS1J3MmcifQ==
database = Database()
session = requests.Session()
session.headers.update({
    "User-Agent": AUTH["user_agent"],
    "Authorization": AUTH["authorization"],
    "x-ig-device-id": AUTH["device_id"]
})
result = []
parsed_items = 0
result_short_urls = []
cat_list = {}
with open('categori.txt', encoding='UTF-8') as file:
    cat_list = eval(file.readline())

def sku_info(sku, count):
    data = loads(requests.get(f'https://card.wb.ru/cards/detail?appType=1&curr=rub&dest=-1257786&spp=30&nm={sku}').text)
    card_info = {}
    card_info['request_count'] = count
    if len(data['data']['products']) == 0: return None
    else: return True
    card_info['feedbacks'] = data['data']['products'][0]['feedbacks']
    try: card_info['cat'] = cat_list[data['data']['products'][0]['subjectParentId']]
    except: card_info['cat'] = ""
    try: card_info['pod_cat'] = cat_list[data['data']['products'][0]['subjectId']]
    except: card_info['pod_cat'] = ""
    card_info['name'] = data['data']['products'][0]['name']
    card_info['brand'] = data['data']['products'][0]['brand']
    card_info['rating'] = data['data']['products'][0]['reviewRating']
    card_info['seller_id'] = data['data']['products'][0]['supplierId']
    card_info['price'] = data['data']['products'][0]['salePriceU']/100
    card_info['seller'] = seller_info(card_info['seller_id'])
    database.add_sku(sku,card_info)
    database.add_seller(card_info['seller_id'], card_info['seller'])
    return card_info

def seller_info(suppler_id):
    data = loads(requests.get(f'https://suppliers-shipment.wildberries.ru/api/v1/suppliers/{suppler_id}',
                                  headers={
                                    'Sec-Ch-Ua': '\"Chromium\";v=\"124\", \"Google Chrome\";v=\"124\", \"Not-A.Brand\";v=\"99\"',
                                    'Sec-Ch-Ua-Mobile': '?0',
                                    'Sec-Ch-Ua-Platform': '\"Windows\"',
                                    'Sec-Fetch-Dest': 'empty',
                                    'Sec-Fetch-Mode': 'cors',
                                    'Sec-Fetch-Site': 'same-site',
                                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
                                    'X-Client-Name': 'site'}).text)
    suppler_info = {}
    suppler_info['sale_item'] = data['saleItemQuantity']
    data =  loads(session.get(f'https://static-basket-01.wbbasket.ru/vol0/data/supplier-by-id/{suppler_id}.json').text)
    suppler_info['name'] = data['supplierName']
    suppler_info['fullname'] = data['supplierFullName']
    suppler_info['inn'] = data['inn']
    return suppler_info


def get_additional_user_info(user_id):
    response = session.post(f"https://i.instagram.com/api/v1/users/{user_id}/info_stream/", data={
        "is_prefetch": False,
        "entry_point": "profile",
        "from_module": "clips_viewer_serp_reels_subtab",
        "_uuid": AUTH["device_id"],
        "is_app_start": True
    }, headers={
        "content-type": "application/x-www-form-urlencoded; charset=UTF-8"
    })

    # Костыль, но он тут нужен =) Кривой ответ от Instagram
    json = loads(response.text.replace("\n{\"user\"", "%SECOND_JSON%{\"user\"").split("%SECOND_JSON%")[1])

    return {
        "biography": json["user"]["biography"],
        "follower_count": json["user"]["follower_count"],
        "following_count": json["user"]["following_count"],
        "media_count": json["user"]["media_count"]
    }


def get_last_user_publications_info(user_id):
    response = session.post(f"https://i.instagram.com/api/v1/feed/user_stream/{user_id}/", data={
        "_uuid": AUTH["device_id"]
    }, headers={
        "content-type": "application/x-www-form-urlencoded; charset=UTF-8"
    })
    # Костыль, но он тут нужен =) Кривой ответ от Instagram
    json = loads(response.text.replace("\n{\"profile_grid_items\"", "%SECOND_JSON%{\"profile_grid_items\"").split("%SECOND_JSON%")[-1])

    item_counter = 0
    likes_count_last_posts = 0
    comments_count_last_posts = 0

    for item in json["items"]:
        if item_counter >= 9:
            break

        likes_count_last_posts += item["like_count"]
        comments_count_last_posts += item["comment_count"]

        item_counter += 1

    return {
        "likes_count_last_posts": likes_count_last_posts,
        "comments_count_last_posts": comments_count_last_posts
    }


def reels_response_parse(response, SEARCH_QUERY):
    global parsed_items
    if len(response["reels_serp_modules"]) == 0: 
        response["has_more"] = False
        return response
    for clip in response["reels_serp_modules"][0]["clips"]:
        # DEBUG
        print("Получаем информацию о {}, пользователь: {}. Собрано: {}".format("https://www.instagram.com/reels/" + clip["media"]["code"], clip["media"]["user"]["username"], parsed_items))
        if database.is_reel_added("https://www.instagram.com/reels/" + clip["media"]["code"]):
            print("ДУБЛИКАТ! ЕСТЬ В БД: " + "https://www.instagram.com/reels/" + clip["media"]["code"])
            continue
        result_short_urls.append("https://www.instagram.com/reels/" + clip["media"]["code"])

        raw_videos = []

        for raw_video in clip["media"]["video_versions"]:
            raw_videos.append({
                "width": raw_video["width"],
                "height": raw_video["height"],
                "url": raw_video["url"]
            })

        user_info = {
            "id": clip["media"]["user"]["id"],
            "full_name": clip["media"]["user"]["full_name"],
            "username": clip["media"]["user"]["username"],
            "is_private": clip["media"]["user"]["is_private"],
            "is_verified": clip["media"]["user"]["is_verified"],
            "profile_pic_url": clip["media"]["user"]["profile_pic_url"]
        }

        user_info.update(get_additional_user_info(clip["media"]["user"]["id"]))
        sleep(1)
        user_info.update(get_last_user_publications_info(clip["media"]["user"]["id"]))

        result_object = {
            "short_url": "https://www.instagram.com/reels/" + clip["media"]["code"],
            "video_urls": raw_videos,
            "likes": clip["media"]["like_count"],
            "comments": clip["media"]["comment_count"],
            "reshare": clip["media"]["reshare_count"],
            "views": clip['media']['play_count'],
            "user": user_info
        }
        result.append(result_object)
        database.add_author(result_object["user"])
        database.add_reel(SEARCH_QUERY, result_object)

        sleep(1)
        parsed_items += 1

    return {
        "reels_max_id": response["reels_max_id"],
        "rank_token": response["rank_token"],
        "page_index": response["page_index"],
        "has_more": response["has_more"]
    }

def get_reels(SEARCH_QUERY):
# Получаем первую пачку Reels'ов
    response = reels_response_parse(session.get("https://i.instagram.com/api/v1/fbsearch/reels_serp", params={
        "search_surface": "clips_serp_page",
        "timezone_offset": 10800,
        "count": 12,
        "query": SEARCH_QUERY
    }).json(),SEARCH_QUERY)

    sleep(1)
    
    paging_token = 4
    while response["has_more"]:
        try:
            json = session.get("https://i.instagram.com/api/v1/fbsearch/reels_serp", params={
                "search_surface": "clips_serp_page",
                "reels_page_index": 11,
                "timezone_offset": 10800,
                "has_more_reels": response["has_more"],
                "count": 30,
                "query": SEARCH_QUERY,
                "reels_max_id": response["reels_max_id"],
                "next_max_id": response["reels_max_id"],
                "rank_token": response["rank_token"],
                "page_index": response["page_index"],
                "page_token": response["reels_max_id"],
                "paging_token": "{\"total_num_items\":" + str(paging_token) + "}"
            }).json()
            response = reels_response_parse(json, SEARCH_QUERY)
        except:
            response['has_more'] = False
        sleep(1)
        paging_token += 4

start = 0
end = 8000
with open('requests.csv',encoding='utf-8-sig') as file:
    rows = list(csv.reader(file))
    for i in range(start,end):
        sku,count = rows[i][0].split(';')[0], rows[i][0].split(';')[1]
        if(int(sku) > 999999 and int(sku) < 1000000000):
            try:
                card = sku_info(sku=sku,count=count)
            except Exception as e:
                print(e)
                continue
            if card != None:
                get_reels(str(sku))
        sleep(5)
                       