from googlesearch import search
def get_reels_id(sku):
     urls = []
     for url in search(f'{sku} site:instagram.com/reel', pause=1.0):
          id = url.split('/')[4]
          if id not in urls: urls.append(id)
     return urls

