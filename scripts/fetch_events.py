#!/usr/bin/env python3
"""
Robust fetch_events.py
- Uses retries
- Never fails the job on exceptions
- Writes matches/YYYY-MM-DD.json even if empty
"""
import os
import json
import time
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
ARTISTS_FILE = os.path.join(REPO_ROOT, 'artists.json')
MATCHES_DIR = os.path.join(REPO_ROOT, 'matches')
HEADERS = {'User-Agent': 'riley-coe-tracker/1.0 (+https://github.com/nickelliottgreaves-dot/riley-coe-tracker)'}

VENUES = [
    'The Cluny', 'Cluny 2', 'Boiler Shop', 'Wylam Brewery', 'The Grove', 'Glasshouse', 'Sage One', 'Sage Two',
    'Cumberland Arms', 'Cobalt Studios', 'The Lubber Fiend', 'think tank', 'Newcastle University Students Union',
    'Little Buildings', 'Newcastle City Hall', 'Riverside', 'Zerox', 'The Newgate Social', 'Head of Steam'
]


def requests_session(retries=3, backoff_factor=0.5, status_forcelist=(500,502,503,504)):
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
            return json.load(f)
    except Exception:
        return []


def query_bandsintown(session, artist):
    app_id = os.getenv('BANDSTOWN_APP_ID') or os.getenv('BANDSINTOWN_APP_ID')
    if not app_id:
        return []
    url = f'https://rest.bandsintown.com/artists/{requests.utils.requote_uri(artist)}/events?app_id={app_id}'
    try:
        r = session.get(url, headers=HEADERS, timeout=15)
        if r.ok:
            return r.json()
    except Exception as e:
        print('Bandsintown lookup failed for', artist, e)
    return []


def fallback_search(session, artist):
    results = []
    query = f'{artist} Newcastle gig'
    search_url = f'https://html.duckduckgo.com/html?q={requests.utils.requote_uri(query)}'
    try:
        r = session.get(search_url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, 'html.parser')
        for a in soup.select('a.result__a')[:10]:
            href = a.get('href')
            title = a.get_text(' ', strip=True)
            if not href:
                continue
            for venue in VENUES:
                if venue.lower() in title.lower() or venue.lower() in href.lower():
                    results.append({'artist': artist, 'venue': venue, 'title': title, 'url': href})
    except Exception as e:
        print('DuckDuckGo fallback failed for', artist, e)
    return results


def main():
    try:
        session = requests_session()
        artists = load_artists()
        matches = []
        for artist in artists:
            # be polite
            time.sleep(0.2)
            try:
                events = query_bandsintown(session, artist)
                if events:
                    for event in events:
                        venue = event.get('venue', {})
                        venue_name = venue.get('name') if isinstance(venue, dict) else None
                        if venue_name and any(v.lower() in venue_name.lower() for v in VENUES):
                            matches.append({
                                'date': event.get('datetime'),
                                'artist': artist,
                                'venue': venue_name,
                                'price': None,
                                'url': event.get('url'),
                                'source': 'Bandsintown'
                            })
                    continue
                # fallback search
                for result in fallback_search(session, artist):
                    matches.append({
                        'date': None,
                        'artist': artist,
                        'venue': result['venue'],
                        'price': None,
                        'url': result['url'],
                        'source': 'DuckDuckGo fallback'
                    })
            except Exception as e:
                print('Error checking artist', artist, e)
                continue
        os.makedirs(MATCHES_DIR, exist_ok=True)
        out_path = os.path.join(MATCHES_DIR, f"{datetime.utcnow().strftime('%Y-%m-%d')}.json")
        try:
            with open(out_path, 'w', encoding='utf-8') as f:
                json.dump(matches, f, ensure_ascii=False, indent=2)
            print('Wrote matches:', out_path)
        except Exception as e:
            print('Failed to write matches file', e)
    except Exception as e:
        print('Unexpected error in fetch_events:', e)


if __name__ == '__main__':
    main()
