import requests
from json import loads
from time import sleep
import re

from database import Database

AUTH = {
    "device_id": "a53f5e06-4663-4091-b046-85a9e5c05299",
    "user_agent": "Instagram 331.0.0.37.90 Android (26/8.0.0; 480dpi; 1080x1920; samsung; SM-G935F; hero2lte; samsungexynos8890; ru_RU; 598808576)",
    "authorization": "Bearer IGT:2:eyJkc191c2VyX2lkIjoiNjY0MzMyNTEzODMiLCJzZXNzaW9uaWQiOiI2NjQzMzI1MTM4MyUzQXpGMnpnOVo5cll1aEFnJTNBMjYlM0FBWWVENjdXNzFJMjVlUVVJZm1kdmV5TlJubm9YVDZWZDdSYURfS1J3MmcifQ=="
}

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

def sku_info(sku):
    data = loads(requests.get(f'https://card.wb.ru/cards/detail?appType=1&curr=rub&dest=-1257786&spp=30&nm={sku}').text)
    card_info = {}
    if len(data['data']['products']) == 0: return None
    card_info['feedbacks'] = data['data']['products'][0]['feedbacks']
    card_info['cat'] = cat_list[data['data']['products'][0]['subjectParentId']]
    card_info['pod_cat'] = cat_list[data['data']['products'][0]['subjectId']]
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
    json = loads(response.text.replace("\n{\"num_results\"", "%SECOND_JSON%{\"num_results\"").split("%SECOND_JSON%")[1])

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
        #sleep(1)
        user_info.update(get_last_user_publications_info(clip["media"]["user"]["id"]))

        result_object = {
            "short_url": "https://www.instagram.com/reels/" + clip["media"]["code"],
            "video_urls": raw_videos,
            "likes": clip["media"]["like_count"],
            "comments": clip["media"]["comment_count"],
            "reshare": clip["media"]["reshare_count"],
            "user": user_info
        }
        result.append(result_object)
        database.add_author(result_object["user"])
        database.add_reel(SEARCH_QUERY, result_object)

        #sleep(1)
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

        paging_token += 4

offset = 0
data = loads(requests.get(f'https://seller-weekly-report.wildberries.ru/ns/trending-searches/suppliers-portal-analytics/api?itemsPerPage=100&offset={offset}&period=month&query=&sort=desc',
                    headers={
                        'Cookie': '_wbauid=9067725811709906283; BasketUID=b655500ae9dd406db6dbc4a50247916d; ___wbu=d61fdc69-bf52-43d7-abda-5a22922d65b9.1709906284; external-locale=ru; wbx-validation-key=c929bb0f-41dd-4fa1-b565-9d9e753523ce; wb-pid=gYFAwYVW2apE67rsxsgi0bC2AAABju1TRCIhORp1gDM2ntIIQXYBfXQGJGlKslSVuXL3U7HP3g_6PQ; wb-id=gYFvRpusKspFKbGK4SO74X3bAAABjz7H_Er0gDwjoEuRxccMfBLqODN9i0RHJxlyaJebuIHoWtASUjVmMDdiNzA5LTk3YzQtNGU2YS1hYmQyLTYzYzRhNWI3NjNmNA; x-supplier-id-external=300c6525-8b71-49fd-957a-3f5908d9c25d; WBTokenV3=eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJpYXQiOjE3MTU3MDY5MTEsInZlcnNpb24iOjIsInVzZXIiOiI0ODc0MDIwNSIsInNoYXJkX2tleSI6IjQiLCJjbGllbnRfaWQiOiJzZWxsZXItcG9ydGFsIiwic2Vzc2lvbl9pZCI6IjMxMDFjNzExMDU3ZTRkZDVhOWMzN2E5NzczZmJkN2MyIiwidXNlcl9yZWdpc3RyYXRpb25fZHQiOjE2NzUwNTg1MTEsInZhbGlkYXRpb25fa2V5IjoiZGQ0NzRiMzJlNDRhNWQxOTUwMDM5NDJjNDBjMzU4N2U3ZDExY2E0ZDJhOTQyYmE3ZWI2MWNkMzRjNTM0OWQ1NiIsInBob25lIjoiMURNVE1JcnpYUHEwNEdUckJEZ3Zodz09In0.Mjgl0J45gBEnukHz8E1ugYlkw4tqJKDH6ga5itDRGWlubVFxecxVH3mfeZRuq_41IOzCXUQhU1bUgjtdmp1gufMeB83L22fn7KHFkCgCo194QFrPTWGfOk6nWGXenDddhT1Vt5gHMJgn47pQtFvBYq-qW7orAox6jZLr7p3fhCCxNpMaVoYpRXK49TBKyPUTznicQqlIwEtIq_ujPxV9RUDgA_6KMR7s_27jfq_6uq3dqUvsa0IqdG6gD3TYaAvwLu-tMEXmQDEFMa9r2bqlJHgEZpmvinBCyC-Jcbr1w0QE79k4g9yh-c-ieUFPV49EcjVoseIiPJoea9WiVIoBtg; ___wbs=f21425d5-c8c5-4c24-8415-6833102b0f6f.1716278552; __zzatw-wb=MDA0dC0cTHtmcDhhDHEWTT17CT4VHThHKHIzd2UtQ2whX0lZJDVRP0FaW1Q4NmdBEXUmCQg3LGBwVxlRExpceEdXeiwaF3lyLFcJC19ESmllbQwtUlFRS19/Dg4/aU5ZQ11wS3E6EmBWGB5CWgtMeFtLKRZHGzJhXkZpdRVSCAtccEhudClAbFJjexUkdF4IfCxKGn5yJg05P2JwQ19vG3siXyoIJGM1Xz9EaVhTMCpYQXt1J3Z+KmUzPGweZUlgKEtXTX0sIg1pN2wXPHVlLwkxLGJ5MVIvE0tsP0caRFpbQDsyVghDQE1HFF9BWncyUlFRS2EQR0lrZU5TQixmG3EVTQgNND1aciIPWzklWAgSPwsmIBJ9bSpYDw1bQUltbxt/Nl0cOWMRCxl+OmNdRkc3FSR7dSYKCTU3YnAvTCB7SykWRxsyYV5GaXUVUn8LFkNGb3gmQx8kYERdKHkRSgoqIEJ0bllUEAtjcUoodS5vVxlRDxZhDhYYRRcje0I3Yhk4QhgvPV8/YngiD2lIYCBJV1QKLRsRfHMlS3FPLH12X30beylOIA0lVBMhP05yjM/euA==; cfidsw-wb=V401U2fKq3wlQpSX1CJ6yQXZ8TekKTxTKXtd/x5WiTAD0amreGgmFqO3Mm/pHez8rHnCy+drDrKtEZUYCANLvuaFNoLz8Ztxd3mlKmYF9ufi3lwfenEHItIY1Gw85Qg1O70ZjGcyKly6Xh/s5OROK8G9AopCtQbc8AKIR7w=',
                        'Sec-Ch-Ua': '\"Chromium\";v=\"124\", \"Google Chrome\";v=\"124\", \"Not-A.Brand\";v=\"99\"',
                        'Sec-Ch-Ua-Mobile': '?0',
                        'Sec-Ch-Ua-Platform': '\"Windows\"',
                        'Sec-Fetch-Dest': 'empty',
                        'Sec-Fetch-Mode': 'cors',
                        'Sec-Fetch-Site': 'same-site',
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
                        'X-Client-Name': 'site'}).text)
while not data['error']:
    for item in data['data']['list']:
        sku = re.findall(r'\d+', item['text'])
        if len(sku) > 0:
            sku = int(sku[0])
            if(sku > 999999 and sku < 1000000000):
                card = sku_info(sku)
                if card != None:
                    get_reels(str(sku))

    offset += 100
    data = loads(requests.get(f'https://seller-weekly-report.wildberries.ru/ns/trending-searches/suppliers-portal-analytics/api?itemsPerPage=100&offset={offset}&period=month&query=&sort=desc',
                    headers={
                        'Cookie': '_wbauid=9067725811709906283; BasketUID=b655500ae9dd406db6dbc4a50247916d; ___wbu=d61fdc69-bf52-43d7-abda-5a22922d65b9.1709906284; external-locale=ru; wbx-validation-key=c929bb0f-41dd-4fa1-b565-9d9e753523ce; wb-pid=gYFAwYVW2apE67rsxsgi0bC2AAABju1TRCIhORp1gDM2ntIIQXYBfXQGJGlKslSVuXL3U7HP3g_6PQ; wb-id=gYFvRpusKspFKbGK4SO74X3bAAABjz7H_Er0gDwjoEuRxccMfBLqODN9i0RHJxlyaJebuIHoWtASUjVmMDdiNzA5LTk3YzQtNGU2YS1hYmQyLTYzYzRhNWI3NjNmNA; x-supplier-id-external=300c6525-8b71-49fd-957a-3f5908d9c25d; WBTokenV3=eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJpYXQiOjE3MTU3MDY5MTEsInZlcnNpb24iOjIsInVzZXIiOiI0ODc0MDIwNSIsInNoYXJkX2tleSI6IjQiLCJjbGllbnRfaWQiOiJzZWxsZXItcG9ydGFsIiwic2Vzc2lvbl9pZCI6IjMxMDFjNzExMDU3ZTRkZDVhOWMzN2E5NzczZmJkN2MyIiwidXNlcl9yZWdpc3RyYXRpb25fZHQiOjE2NzUwNTg1MTEsInZhbGlkYXRpb25fa2V5IjoiZGQ0NzRiMzJlNDRhNWQxOTUwMDM5NDJjNDBjMzU4N2U3ZDExY2E0ZDJhOTQyYmE3ZWI2MWNkMzRjNTM0OWQ1NiIsInBob25lIjoiMURNVE1JcnpYUHEwNEdUckJEZ3Zodz09In0.Mjgl0J45gBEnukHz8E1ugYlkw4tqJKDH6ga5itDRGWlubVFxecxVH3mfeZRuq_41IOzCXUQhU1bUgjtdmp1gufMeB83L22fn7KHFkCgCo194QFrPTWGfOk6nWGXenDddhT1Vt5gHMJgn47pQtFvBYq-qW7orAox6jZLr7p3fhCCxNpMaVoYpRXK49TBKyPUTznicQqlIwEtIq_ujPxV9RUDgA_6KMR7s_27jfq_6uq3dqUvsa0IqdG6gD3TYaAvwLu-tMEXmQDEFMa9r2bqlJHgEZpmvinBCyC-Jcbr1w0QE79k4g9yh-c-ieUFPV49EcjVoseIiPJoea9WiVIoBtg; ___wbs=f21425d5-c8c5-4c24-8415-6833102b0f6f.1716278552; __zzatw-wb=MDA0dC0cTHtmcDhhDHEWTT17CT4VHThHKHIzd2UtQ2whX0lZJDVRP0FaW1Q4NmdBEXUmCQg3LGBwVxlRExpceEdXeiwaF3lyLFcJC19ESmllbQwtUlFRS19/Dg4/aU5ZQ11wS3E6EmBWGB5CWgtMeFtLKRZHGzJhXkZpdRVSCAtccEhudClAbFJjexUkdF4IfCxKGn5yJg05P2JwQ19vG3siXyoIJGM1Xz9EaVhTMCpYQXt1J3Z+KmUzPGweZUlgKEtXTX0sIg1pN2wXPHVlLwkxLGJ5MVIvE0tsP0caRFpbQDsyVghDQE1HFF9BWncyUlFRS2EQR0lrZU5TQixmG3EVTQgNND1aciIPWzklWAgSPwsmIBJ9bSpYDw1bQUltbxt/Nl0cOWMRCxl+OmNdRkc3FSR7dSYKCTU3YnAvTCB7SykWRxsyYV5GaXUVUn8LFkNGb3gmQx8kYERdKHkRSgoqIEJ0bllUEAtjcUoodS5vVxlRDxZhDhYYRRcje0I3Yhk4QhgvPV8/YngiD2lIYCBJV1QKLRsRfHMlS3FPLH12X30beylOIA0lVBMhP05yjM/euA==; cfidsw-wb=V401U2fKq3wlQpSX1CJ6yQXZ8TekKTxTKXtd/x5WiTAD0amreGgmFqO3Mm/pHez8rHnCy+drDrKtEZUYCANLvuaFNoLz8Ztxd3mlKmYF9ufi3lwfenEHItIY1Gw85Qg1O70ZjGcyKly6Xh/s5OROK8G9AopCtQbc8AKIR7w=',
                        'Sec-Ch-Ua': '\"Chromium\";v=\"124\", \"Google Chrome\";v=\"124\", \"Not-A.Brand\";v=\"99\"',
                        'Sec-Ch-Ua-Mobile': '?0',
                        'Sec-Ch-Ua-Platform': '\"Windows\"',
                        'Sec-Fetch-Dest': 'empty',
                        'Sec-Fetch-Mode': 'cors',
                        'Sec-Fetch-Site': 'same-site',
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
                        'X-Client-Name': 'site'}).text)