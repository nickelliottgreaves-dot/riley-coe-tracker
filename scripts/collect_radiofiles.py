#!/usr/bin/env python3
"""Collect Riley & Coe tracklists from RadioFiles (radiofiles.io)."""
import os
import json
import requests
from bs4 import BeautifulSoup

BASE = 'https://radiofiles.io/show/riley-coe'
DIAG_DIR = 'diagnostics/raw'
OUT_DIR = 'outputs'

os.makedirs(DIAG_DIR, exist_ok=True)
os.makedirs(OUT_DIR, exist_ok=True)


def fetch_url(url):
    try:
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        return r.text
    except Exception as e:
        print('Failed to fetch', url, e)
        return None


def parse_episode_page(html):
    soup = BeautifulSoup(html, 'html.parser')
    # RadioFiles often has a list of tracks in ordered lists
    ol = soup.find('ol')
    if ol:
        items = [li.get_text(' ', strip=True) for li in ol.find_all('li')]
        if len(items) >= 1:
            return items
    # Fallback: look for lines with numbers
    text = soup.get_text('\n')
    import re
    numbered = re.findall(r"^\s*\d+[\).\-]\s*(.+)$", text, flags=re.M)
    return [s.strip() for s in numbered]


def collect_radiofiles():
    print('Collecting RadioFiles page', BASE)
    pg = fetch_url(BASE)
    if not pg:
        print('Failed to fetch RadioFiles base page')
        return []
    soup = BeautifulSoup(pg, 'html.parser')
    ep_links = []
    for a in soup.find_all('a', href=True):
        href = a['href']
        if '/episode/' in href or '/riley-coe/' in href:
            full = href if href.startswith('http') else 'https://radiofiles.io' + href
            ep_links.append(full)
    # dedupe
    seen = set()
    episodes = []
    for u in ep_links:
        if u in seen:
            continue
        seen.add(u)
        episodes.append(u)
    results = []
    for idx, ep in enumerate(episodes[:20], 1):
        print('Processing', ep)
        html = fetch_url(ep)
        if html:
            fname = os.path.join(DIAG_DIR, f'radiofiles_ep_{idx}.html')
            with open(fname, 'w', encoding='utf-8') as f:
                f.write(html)
            tracks = parse_episode_page(html)
            status = 'complete' if tracks else 'failed'
            results.append({'url': ep, 'tracks': tracks, 'status': status})
    out_path = os.path.join(OUT_DIR, 'radiofiles_tracks.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print('Saved RadioFiles tracks to', out_path)
    return results


if __name__ == '__main__':
    collect_radiofiles()
