from bs4 import BeautifulSoup
import asyncio
import json
from playwright.async_api import async_playwright
import re

def load_name_mappings(json_path="FSTV_mapping.json"):
    # Load the JSON mapping, keys as-is (case sensitive)
    with open(json_path, "r", encoding="utf-8") as f:
        mappings = json.load(f)
    # Normalize mapping keys to lowercase and strip spaces for matching
    normalized_map = {}
    for k, v in mappings.items():
        norm_key = re.sub(r'\s+', ' ', k.strip().lower())
        normalized_map[norm_key] = v.strip()
    return normalized_map

def normalize_channel_name(name: str) -> str:
    # Normalize channel name scraped from HTML the same way
    return re.sub(r'\s+', ' ', name.strip().lower())

async def fetch_fstv_html():
    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        print("🌐 Visiting FSTV...")
        await page.goto("https://fstv.us/live-tv.html?timezone=America%2FDenver", timeout=60000)
        await page.wait_for_load_state("networkidle")

        html = await page.content()
        await browser.close()
        return html

def build_playlist_from_html(html, name_map):
    soup = BeautifulSoup(html, "html.parser")
    channels = []

    for div in soup.find_all("div", class_="item-channel"):
        url = div.get("data-link")
        logo = div.get("data-logo")
        name = div.get("title")

        if not (url and name):
            continue

        normalized_name = normalize_channel_name(name)
        new_name = name_map.get(normalized_name, name.strip())  # fallback to original

        channels.append({"url": url, "logo": logo, "name": new_name})

    playlist_lines = ['#EXTM3U\n']
    for ch in channels:
        playlist_lines.append(
            f'#EXTINF:-1 tvg-logo="{ch["logo"]}" group-title="FSTV",{ch["name"]}\n'
        )
        playlist_lines.append(ch["url"] + "\n")

    return playlist_lines

async def main():
    name_map = load_name_mappings()
    html = await fetch_fstv_html()
    playlist_lines = build_playlist_from_html(html, name_map)

    with open("FSTV24.m3u8", "w", encoding="utf-8") as f:
        f.writelines(playlist_lines)

    print(f"✅ Generated playlist with {len(playlist_lines)//2} channels in FSTV24.m3u8")

if __name__ == "__main__":
    asyncio.run(main())
