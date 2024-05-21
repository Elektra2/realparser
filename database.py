from psycopg2 import connect
from psycopg2 import sql
from json import dumps

class Database:
    def __init__(self):
        self._connection = connect("""
            host=rc1b-lqzqezzwssl3kn0y.mdb.yandexcloud.net
            port=6432
            dbname=reels_parser
            user=reels_parser
            password= KLJddwe32FGV
            target_session_attrs=read-write
        """)
        self.cursor = self._connection.cursor()
    

    def add_author(self, user):
        self.cursor.execute(sql.SQL("""
            INSERT INTO authors (id, username, fullname, profile_pic_url, biography, follower_count, following_count, media_count, likes_count_last_posts, comments_count_last_posts)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id)
            DO UPDATE SET
                username = excluded.username,
                fullname = excluded.fullname,
                profile_pic_url = excluded.profile_pic_url,
                biography = excluded.biography,
                follower_count = excluded.follower_count,
                following_count = excluded.following_count,
                media_count = excluded.media_count,
                likes_count_last_posts = excluded.likes_count_last_posts,
                comments_count_last_posts = excluded.comments_count_last_posts
            """), (
                int(user["id"]),
                user["username"],
                user["full_name"],
                user["profile_pic_url"],
                user["biography"],
                user["follower_count"],
                user["following_count"],
                user["media_count"],
                user["likes_count_last_posts"],
                user["comments_count_last_posts"]))
        self._connection.commit()
    

    def add_reel(self, prompt, reel):
        self.cursor.execute(sql.SQL("""
            INSERT INTO reels (prompt, short_url, likes, comments, reshare, author_id, video_urls)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (short_url)
            DO UPDATE SET
                likes = excluded.likes,
                comments = excluded.comments,
                reshare = excluded.reshare,
                author_id = excluded.author_id,
                video_urls = excluded.video_urls
            """), (
                prompt,
                reel["short_url"],
                reel["likes"],
                reel["comments"],
                reel["reshare"],
                int(reel["user"]["id"]),
                dumps(reel["video_urls"])))
        self._connection.commit()

    def add_sku(self, id, sku):
        self.cursor.execute(sql.SQL("""
            INSERT INTO skus (sku, name, brand, category, subcategory, rating, feedbacks, price, seller_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (sku)
            DO UPDATE SET
                name = excluded.name,
                feedbacks = excluded.feedbacks,
                rating = excluded.rating,
                price = excluded.price
            """), (
                id,
                sku['name'],
                sku['brand'],
                sku['cat'],
                sku['pod_cat'],
                sku['rating'],
                sku['feedbacks'],
                sku['price'],
                sku['seller_id']))
        self._connection.commit()

    def add_seller(self, id, seller):
        self.cursor.execute(sql.SQL("""
            INSERT INTO sellers (id, name, fullname, inn, sale_items)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (id)
            DO UPDATE SET
                sale_items = excluded.sale_items
            """), (
                id,
                seller['name'],
                seller['fullname'],
                seller['inn'],
                seller['sale_item']))
        self._connection.commit()

    def is_reel_added(self, reel_url):
        self.cursor.execute("SELECT COUNT(*) FROM reels WHERE short_url = %s", (reel_url,))
        return self.cursor.fetchone()[0] > 0


    def disconnect(self):
        self.cursor.close()
        self._connection.close()