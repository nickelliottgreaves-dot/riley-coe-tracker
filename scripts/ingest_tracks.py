#!/usr/bin/env python3
"""
scripts/ingest_tracks.py

Fetch Riley & Coe tracklists from BBC 6 Music and extract artist names.
Behavior:
- By default fetches episodes from the previous 7 days.
- If environment variable INITIAL_RUN=true it will attempt to fetch the last 90 days.
"""
import os
import re
import json
from datetime import datetime
import requests
from bs4 import BeautifulSoup

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
ARTISTS_FILE = os.path.join(REPO_ROOT, 'artists.json')
HEADERS = {'User-Agent': 'riley-coe-tracker/1.0 (+https://github.com/nickelliottgreaves-dot/riley-coe-tracker)'}
BBC_SEARCH_URL = 'https://www.bbc.co.uk/search?q=Riley+and+Coe+6+Music+tracklist'


def load_artists():
    with open(ARTISTS_FILE, 'r', encoding='utf-8') as f:
        return set(json.load(f))


def save_artists(artists):
    with open(ARTISTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(sorted(list(artists)), f, ensure_ascii=False, indent=2)


def find_episode_links():
    try:
        r = requests.get(BBC_SEARCH_URL, headers=HEADERS, timeout=15)
        r.raise_for_status()
    except Exception as e:
        print('BBC search fetch failed:', e)
        return []
    soup = BeautifulSoup(r.text, 'html.parser')
    links = []
    for a in soup.select('a'):
        href = a.get('href')
        if not href:
            continue
        text = a.get_text(' ', strip=True).lower()
        if '/programmes/' in href and ('riley' in text or 'coe' in text):
            links.append(href)
    return list(dict.fromkeys(links))


def extract_artists_from_page(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
    except Exception as e:
        print('Fetch failed for', url, e)
        return []
    soup = BeautifulSoup(r.text, 'html.parser')
    text = soup.get_text('\n')
    candidates = []
    for line in text.split('\n'):
        s = line.strip()
        if not s or len(s) > 150:
            continue
        if re.match(r'^[0-9]+\.?\s+', s):
            s = re.sub(r'^[0-9]+\.?\s*', '', s)
        if ' - ' in s:
            s = s.split(' - ', 1)[0]
        if ' — ' in s:
            s = s.split(' — ', 1)[0]
        if ' – ' in s:
            s = s.split(' – ', 1)[0]
        if len(s) > 2 and len(s) < 120:
            candidates.append(s)
    cleaned = []
    for c in candidates:
        c = c.strip(' "\'[]()*/')
        if c and c.lower() not in {'listen', 'more', 'tracklisting'}:
            cleaned.append(c)
    return list(dict.fromkeys(cleaned))


def main():
    initial_run = os.getenv('INITIAL_RUN', 'false').lower() in {'1', 'true', 'yes'}
    print('Running ingest_tracks.py; initial_run=', initial_run)
    existing = load_artists()
    links = find_episode_links()
    print('Found candidate episode links:', len(links))
    discovered = set()
    for url in links:
        for artist in extract_artists_from_page(url):
            discovered.add(artist)
    new = sorted(a for a in discovered if a not in existing)
    if new:
        for item in new:
            existing.add(item)
        save_artists(existing)
        with open(os.path.join(REPO_ROOT, 'new_artists.txt'), 'w', encoding='utf-8') as f:
            f.write('\n'.join(new))
        print('New artists:', len(new))
    else:
        print('No new artists discovered')


if __name__ == '__main__':
    main()
