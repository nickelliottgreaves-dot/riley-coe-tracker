#!/usr/bin/env python3
"""Collect Riley & Coe tracklists from Mixcloud (The 6 Music Archive).
Uses Playwright to render Mixcloud pages since they often use dynamic loading.
"""
import os
import json
from bs4 import BeautifulSoup
import requests

CHANNEL = os.environ.get('MIXCLOUD_CHANNEL', 'https://www.mixcloud.com/SixMusicAlternative/')
DIAG_DIR = 'diagnostics/raw'
OUT_DIR = 'outputs'
os.makedirs(DIAG_DIR, exist_ok=True)
os.makedirs(OUT_DIR, exist_ok=True)


def render_with_playwright(url):
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:
        print('Playwright not available:', e)
        return None
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, timeout=30000)
            page.wait_for_timeout(1000)
            html = page.content()
            browser.close()
            return html
    except Exception as e:
        print('Playwright render failed for', url, e)
        return None


def find_upload_links(channel_html):
    soup = BeautifulSoup(channel_html, 'html.parser')
    links = []
    for a in soup.find_all('a', href=True):
        href = a['href']
        if href.startswith('/'):  # internal Mixcloud link
            if href.count('/') >= 2:
                full = 'https://www.mixcloud.com' + href
                links.append(full)
    # dedupe
    seen = set()
    out = []
    for l in links:
        if l in seen:
            continue
        seen.add(l)
        out.append(l)
    return out


def parse_mixcloud_tracklist(html):
    soup = BeautifulSoup(html, 'html.parser')
    # Mixcloud often puts tracklist as numbered list or paragraphs with timestamps
    items = []
    for sel in ['ol', 'ul']:
        for el in soup.select(sel):
            li = el.find_all('li')
            if li and len(li) >= 1:
                items = [x.get_text(' ', strip=True) for x in li]
                if items:
                    return items
    # Fallback: look for lines with timestamps like 00:12 Artist - Title
    text = soup.get_text('\n')
    import re
    lines = []
    for line in text.splitlines():
        if re.search(r"\d{1,2}:\d{2}", line):
            lines.append(line.strip())
    return lines


def collect_mixcloud():
    print('Rendering Mixcloud channel:', CHANNEL)
    ch_html = render_with_playwright(CHANNEL)
    if not ch_html:
        print('Failed to render channel page')
        return []
    save_path = os.path.join(DIAG_DIR, 'mixcloud_channel.html')
    with open(save_path, 'w', encoding='utf-8') as f:
        f.write(ch_html)
    links = find_upload_links(ch_html)
    results = []
    for idx, link in enumerate(links[:20], 1):
        print('Visiting', link)
        html = render_with_playwright(link)
        if not html:
            continue
        savef = os.path.join(DIAG_DIR, f'mixcloud_ep_{idx}.html')
        with open(savef, 'w', encoding='utf-8') as f:
            f.write(html)
        tracks = parse_mixcloud_tracklist(html)
        status = 'complete' if tracks else 'failed'
        results.append({'url': link, 'tracks': tracks, 'status': status})
    out_path = os.path.join(OUT_DIR, 'mixcloud_tracks.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print('Saved Mixcloud tracks to', out_path)
    return results


if __name__ == '__main__':
    collect_mixcloud()
