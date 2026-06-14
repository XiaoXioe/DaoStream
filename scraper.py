from scrapling import Fetcher
import json

def scrape_anichin():
    url = "https://anichin.moe"
    print(f"Fetching {url}...")
    
    # Using Fetcher to get the page
    fetcher = Fetcher()
    page = fetcher.get(url)
    
    # Extracting Donghua Baru section
    # Based on the HTML we saw:
    # <div class="section"><div class="releases"><h3>Donghua Baru</h3></div>...<div class='serieslist'><ul>...
    
    results = []
    
    # We can use CSS selectors or XPath. Scrapling's Fetcher returns an object that supports both.
    # Looking at the HTML structure again:
    # The "Donghua Baru" section seems to be identified by the <h3>Donghua Baru</h3>
    
    # Let's try to find the list items in the section following "Donghua Baru"
    # Or more simply, just find all items in the serieslist
    items = page.css('.section .serieslist ul li')
    
    for item in items:
        title_element = item.css('h4 a')
        if title_element:
            title = title_element.css('::text').get('').strip()
            link = title_element.css('::attr(href)').get()
            
            # Extract genres
            genres = item.css('span a[rel="tag"]::text').getall()
            
            # Extract image
            img_url = item.css('img::attr(src)').get()
            
            results.append({
                "title": title,
                "link": link,
                "genres": genres,
                "image": img_url
            })
    
    return results

if __name__ == "__main__":
    data = scrape_anichin()
    print(f"Found {len(data)} items.")
    print(json.dumps(data[:5], indent=2))
    
    # Save to file
    with open("anichin_latest.json", "w") as f:
        json.dump(data, f, indent=2)
    print("Results saved to anichin_latest.json")
