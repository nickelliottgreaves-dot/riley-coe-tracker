#!/usr/bin/env python3
"""
Robust ingest_tracks.py
- Uses requests with retry/backoff
- Defensive parsing
- Never raises uncaught exceptions (prints errors and exits 0)
"""
import os
import re
import json
import time
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
ARTISTS_FILE = os.path.join(REPO_ROOT, 'artists.json')
HEADERS = {'User-Agent': 'riley-coe-tracker/1.0 (+https://github.com/nickelliottgreaves-dot/riley-coe-tracker)'}
BBC_SEARCH_URL = 'https://www.bbc.co.uk/search?q=Riley+and+Coe+6+Music+tracklist'


def requests_session(retries=3, backoff_factor=0.5, status_forcelist=(500, 502, 503, 504)):
    s = requests.Session()
    retry = Retry(total=retries, read=retries, connect=retries, backoff_factor=backoff_factor,
                  status_forcelist=status_forcelist, allowed_methods=frozenset(['GET', 'POST']))
    adapter = HTTPAdapter(max_retries=retry)
    s.mount('https://', adapter)
    s.mount('http://', adapter)
    return s


def load_artists():
    try:
        with open(ARTISTS_FILE, 'r', encoding='utf-8') as f:
            return set(json.load(f))
    except Exception:
        return set()


def save_artists(artists):
    try:
        with open(ARTISTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(sorted(list(artists)), f, ensure_ascii=False, indent=2)
    except Exception as e:
        print('Failed to save artists.json:', e)


def find_episode_links(session):
    try:
        r = session.get(BBC_SEARCH_URL, headers=HEADERS, timeout=15)
        r.raise_for_status()
    except Exception as e:
        print('BBC search fetch failed:', e)
        return []
    soup = BeautifulSoup(r.text, 'html.parser')
    links = []
    for a in soup.find_all('a', href=True):
        href = a['href']
        text = a.get_text(' ', strip=True).lower()
        try:
            if '/programmes/' in href and ('riley' in text or 'coe' in text):
                links.append(href)
        except Exception:
            continue
    return list(dict.fromkeys(links))


def extract_artists_from_page(session, url):
    try:
        r = session.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
    except Exception as e:
        print('Fetch failed for', url, e)
        return []
    try:
        soup = BeautifulSoup(r.text, 'html.parser')
        # Try to find structured tracklist (ol/ul with class or id)
        candidates = []
        for selector in ['ol.tracklist', 'ul.tracklist', 'section.tracklist', 'div.tracklist', 'div.programme__body']:
            for node in soup.select(selector):
                text = node.get_text('\n')
                for line in text.split('\n'):
                    s = line.strip()
                    if not s:
                        continue
                    candidates.append(s)
        # Fallback: full page text
        if not candidates:
            text = soup.get_text('\n')
            candidates = [line.strip() for line in text.split('\n') if line.strip()]

        parsed = []
        for line in candidates:
            s = line
            # strip leading numbers
            s = re.sub(r'^\s*[0-9]+\.?\s*', '', s)
            # split on dash or long dash
            s = re.split(r'\s[\-\u2013\u2014:\/]\s', s)[0]
            s = s.strip(' "\'[]()*/')
            if 2 < len(s) < 120 and not s.lower().startswith(('listen', 'more', 'tracklisting', 'full tracklist')):
                parsed.append(s)
        # dedupe preserving order
        seen = set()
        out = []
        for p in parsed:
            if p not in seen:
                seen.add(p)
                out.append(p)
        return out
    except Exception as e:
        print('Error parsing', url, e)
        return []


def main():
    try:
        initial_run = os.getenv('INITIAL_RUN', 'false').lower() in {'1', 'true', 'yes'}
        print('Running ingest_tracks.py; initial_run=', initial_run)
        session = requests_session()
        existing = load_artists()
        links = find_episode_links(session)
        print('Found candidate episode links:', len(links))
        discovered = []
        for url in links:
            try:
                artists = extract_artists_from_page(session, url)
                for a in artists:
                    discovered.append(a)
                # be polite
                time.sleep(0.5)
            except Exception as e:
                print('Error processing', url, e)
                continue
        discovered_set = set(discovered)
        new = sorted(a for a in discovered_set if a not in existing)
        if new:
            for item in new:
                existing.add(item)
            save_artists(existing)
            try:
                with open(os.path.join(REPO_ROOT, 'new_artists.txt'), 'w', encoding='utf-8') as f:
                    f.write('\n'.join(new))
            except Exception as e:
                print('Failed to write new_artists.txt', e)
            print('New artists:', len(new))
        else:
            print('No new artists discovered')
    except Exception as e:
        print('Unexpected error in ingest_tracks:', e)


if __name__ == '__main__':
    main()
