import re
import json
import logging
from typing import List, Dict, Any
from urllib.parse import urlparse
from scrapling import Fetcher
from .base import BaseSource

# Silence scrapling logger for clean output
logging.getLogger("scrapling").setLevel(logging.ERROR)

class DonghuaFunSource(BaseSource):
    @property
    def name(self) -> str:
        return "Donghua Fun"

    @property
    def base_url(self) -> str:
        return "https://donghuafun.com"

    def get_latest(self) -> List[Dict[str, str]]:
        fetcher = Fetcher()
        page = fetcher.get(self.base_url, follow_redirects=True)
        
        # Locate the Last Update section
        sections = page.css('.box-width')
        last_update_section = None
        for sec in sections:
            header = sec.css('h4.title-h::text').get()
            if header and "last update" in header.lower():
                last_update_section = sec
                break
                
        if not last_update_section:
            items = page.css(".public-list-box")
        else:
            items = last_update_section.css(".public-list-box")
            
        results = []
        for item in items:
            a_tag = item.css("a.public-list-exp")
            title = a_tag.css("::attr(title)").get("").strip()
            link = a_tag.css("::attr(href)").get()
            if title and link:
                results.append({
                    "title": title,
                    "link": link if link.startswith("http") else self.base_url + link
                })
        return results

    def get_popular(self) -> List[Dict[str, str]]:
        fetcher = Fetcher()
        page = fetcher.get(self.base_url, follow_redirects=True)
        popular_items = page.css('.slide-time-bj')
        results = []
        for item in popular_items:
            title = item.css('.this-desc-title::text').get("").strip()
            link = item.css('a::attr(href)').get("")
            if title and link:
                results.append({
                    "title": title,
                    "link": link if link.startswith("http") else self.base_url + link
                })
        return results

    def search(self, query: str) -> List[Dict[str, str]]:
        fetcher = Fetcher()
        search_url = f"{self.base_url}/index.php/vod/search.html?wd={query}"
        page = fetcher.get(search_url, follow_redirects=True)
        items = page.css(".public-list-box")
        results = []
        for item in items:
            a_tag = item.css("a.public-list-exp")
            title = a_tag.css("::attr(title)").get("").strip()
            link = a_tag.css("::attr(href)").get()
            if title and link:
                results.append({
                    "title": title,
                    "link": link if link.startswith("http") else self.base_url + link
                })
        return results

    def get_episodes(self, anime_url: str) -> List[Dict[str, str]]:
        fetcher = Fetcher()
        page = fetcher.get(anime_url, follow_redirects=True)
        
        boxes = page.css(".anthology-list-box")
        episodes_map = {}
        
        def get_ep_num(name):
            match = re.search(r'(?:EP|EO)\s*(\d+)', name, re.I)
            if match:
                return int(match.group(1))
            return 0

        for box in boxes:
            links = box.css("a")
            for ep in links:
                title = "".join(ep.css("::text").getall()).strip()
                href = ep.css("::attr(href)").get()
                if href:
                    full_link = href if href.startswith("http") else self.base_url + href
                    ep_num = get_ep_num(title)
                    if ep_num > 0 and ep_num not in episodes_map:
                        episodes_map[ep_num] = (title, full_link)

        episodes = []
        for ep_num, (title, link) in episodes_map.items():
            episodes.append({"name": title, "link": link, "num": ep_num})
            
        episodes.sort(key=lambda x: x["num"], reverse=True)
        
        return [{"name": e["name"], "link": e["link"]} for e in episodes]

    def get_servers(self, ep_url: str) -> List[Dict[str, Any]]:
        fetcher = Fetcher()
        page = fetcher.get(ep_url, follow_redirects=True)
        
        match = re.search(r'id/(\d+)/sid/(\d+)/nid/(\d+)', ep_url)
        if not match:
            return []
            
        vod_id = match.group(1)
        current_sid = match.group(2)
        nid = match.group(3)
        
        tabs = page.css('.vod-playerUrl')
        servers = []
        
        for idx, tab in enumerate(tabs):
            sid = idx + 1
            label_raw = "".join(tab.css('::text').getall()).strip()
            
            # Clean label from emojis/icons
            label = "".join(c for c in label_raw if ord(c) < 128 or c.isalnum() or c in '()[]-_ ').strip()
            
            tab_url = f"{self.base_url}/index.php/vod/play/id/{vod_id}/sid/{sid}/nid/{nid}.html"
            
            tab_page_content = None
            if str(sid) == current_sid:
                tab_page_content = page.get()
            else:
                try:
                    tab_page_content = fetcher.get(tab_url, follow_redirects=True).get()
                except Exception:
                    continue
                    
            player_match = re.search(r'var player_aaaa\s*=\s*(\{.*\})', tab_page_content)
            if player_match:
                try:
                    player_data = json.loads(player_match.group(1))
                    val = player_data.get("url")
                    flag = player_data.get("from")
                    
                    if val:
                        if flag == "dailymotion":
                            video_url = f"https://www.dailymotion.com/video/{val}"
                        else:
                            video_url = val
                        
                        servers.append({
                            "name": f"{label} ({flag})",
                            "value": video_url,
                            "type": "stream"
                        })
                except Exception:
                    pass
                    
        return servers
