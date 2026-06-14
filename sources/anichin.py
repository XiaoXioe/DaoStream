import re
import logging
import base64
from typing import List, Dict, Any
from urllib.parse import urlparse
from scrapling import Fetcher
from .base import BaseSource

# Silence scrapling logger for clean output
logging.getLogger("scrapling").setLevel(logging.ERROR)

class AnichinSource(BaseSource):
    @property
    def name(self) -> str:
        return "Anichin"

    @property
    def base_url(self) -> str:
        return "https://anichin.moe"

    def get_latest(self) -> List[Dict[str, str]]:
        fetcher = Fetcher()
        page = fetcher.get(self.base_url, follow_redirects=True)
        items = page.css(".section .serieslist ul li")
        results = []
        for item in items:
            title = item.css("h4 a::text").get("").strip()
            link = item.css("h4 a::attr(href)").get()
            if title and link:
                results.append({
                    "title": title,
                    "link": link if link.startswith("http") else self.base_url + link
                })
        return results

    def get_popular(self) -> List[Dict[str, str]]:
        fetcher = Fetcher()
        page = fetcher.get(self.base_url, follow_redirects=True)
        popular_items = page.css(".popularslider article.bs")
        results = []
        for item in popular_items:
            series_title = item.css(".tt::text").get("").strip()
            ep_link = item.css("a::attr(href)").get("")
            if not ep_link:
                continue
            full_ep_link = ep_link if ep_link.startswith("http") else self.base_url + ep_link
            
            parsed_ep = urlparse(full_ep_link)
            ep_path = parsed_ep.path.strip("/")
            
            series_link = None
            if "-episode-" in ep_path:
                slug = ep_path.split("-episode-")[0]
                series_link = f"{self.base_url}/{slug}/"
            else:
                series_link = full_ep_link
                
            if not series_title:
                a_title = item.css("a::attr(title)").get("")
                series_title = a_title.split(" Episode")[0].split(" Ep ")[0].strip()
                
            if series_title and series_link:
                results.append({"title": series_title, "link": series_link})
        return results

    def search(self, query: str) -> List[Dict[str, str]]:
        fetcher = Fetcher()
        search_url = f"{self.base_url}/?s={query}"
        page = fetcher.get(search_url, follow_redirects=True)
        items = page.css(".listupd .bsx")
        results = []
        for item in items:
            title = item.css("a::attr(title)").get("")
            link = item.css("a::attr(href)").get()
            if title and link:
                full_link = link if link.startswith("http") else self.base_url + link
                results.append({"title": title, "link": full_link})
        return results

    def get_episodes(self, anime_url: str) -> List[Dict[str, str]]:
        fetcher = Fetcher()
        page = fetcher.get(anime_url, follow_redirects=True)
        ep_items = page.css(".eplister ul li a")
        episodes = []
        for ep in ep_items:
            num = ep.css(".epl-num::text").get("").strip()
            title = ep.css(".epl-title::text").get("").strip()
            link = ep.css("::attr(href)").get()
            full_link = link if link.startswith("http") else self.base_url + link
            episodes.append({"name": f"Ep {num}: {title}", "link": full_link})

        # Look for any new episodes listed on the homepage that are not in the list
        parsed_series = urlparse(anime_url)
        slug = parsed_series.path.strip('/')
        if not slug:
            return episodes

        try:
            homepage = fetcher.get(self.base_url, follow_redirects=True)
            all_articles = homepage.css('.listupd article.bs')
            
            seen_links = set(e["link"] for e in episodes)
            new_episodes = []
            
            for article in all_articles:
                a_tag = article.css('a')
                if not a_tag:
                    continue
                link = a_tag.css('::attr(href)').get()
                if not link:
                    continue
                    
                full_link = link if link.startswith("http") else self.base_url + link
                if full_link in seen_links:
                    continue
                    
                parsed_ep = urlparse(full_link)
                ep_path = parsed_ep.path.strip('/').lower()
                slug_lower = slug.lower()
                
                if ep_path.startswith(f"{slug_lower}-episode-"):
                    title = a_tag.css('::attr(title)').get("")
                    ep_text = a_tag.css('.epx::text').get("")
                    
                    num = ep_text.replace("Ep", "").replace("ep", "").strip() if ep_text else ""
                    if not num:
                        match = re.search(r'-episode-([a-zA-Z0-9-]+)', ep_path)
                        if match:
                            num = match.group(1).upper()
                    
                    title_clean = title.strip() if title else f"{slug.replace('-', ' ').title()} Episode {num}"
                    
                    new_episodes.append({
                        "name": f"Ep {num}: {title_clean}",
                        "link": full_link
                    })
                    seen_links.add(full_link)
                    
            if new_episodes:
                episodes = new_episodes + episodes
        except Exception:
            pass

        return episodes

    def get_servers(self, ep_url: str) -> List[Dict[str, Any]]:
        fetcher = Fetcher()
        page = fetcher.get(ep_url, follow_redirects=True)

        server_names = page.css("select.mirror option::text").getall()
        server_values = page.css("select.mirror option::attr(value)").getall()

        servers = []
        for name, val in zip(server_names, server_values):
            if val:
                try:
                    decoded = base64.b64decode(val).decode("utf-8")
                    src_match = re.search(r'src="([^"]+)"', decoded)
                    if src_match:
                        video_url = src_match.group(1)
                        if video_url.startswith("//"):
                            video_url = "https:" + video_url

                        if "dailymotion.com" in video_url:
                            if "video=" in video_url:
                                v_id = video_url.split("video=")[1].split("&")[0]
                                video_url = f"https://www.dailymotion.com/video/{v_id}"

                        servers.append(
                            {"name": name.strip(), "value": video_url, "type": "stream"}
                        )
                except Exception:
                    servers.append({"name": name.strip(), "value": val, "type": "stream"})

        other_iframes = page.css(
            ".player-embed iframe::attr(src), #player_embed iframe::attr(src), .video-content iframe::attr(src)"
        ).getall()
        for src in other_iframes:
            if src and not any(s["value"] == src for s in servers):
                if "google.com" not in src:
                    if src.startswith("//"):
                        src = "https:" + src
                    servers.append(
                        {"name": "Direct Player", "value": src, "type": "stream"}
                    )

        return servers
