#!/usr/bin/env python3
"""Ingest Riley & Coe episodes from BBC Sounds with diagnostics and Playwright rendering when needed.
Saves raw HTML and application/ld+json blocks for inspection and writes extracted tracklists to outputs/bbc_tracks.json
"""
import os
import re
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime

DIAG_DIR = 'diagnostics/raw'
OUT_DIR = 'outputs'
BBC_PROGRAMME = os.environ.get('BBC_PROGRAMME', 'https://www.bbc.co.uk/programmes/b00cfv7b')
MAX_EPISODES = 10

os.makedirs(DIAG_DIR, exist_ok=True)
os.makedirs(OUT_DIR, exist_ok=True)


def save(path, content):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)


def fetch_url(url):
    try:
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        print(f"Failed to fetch {url}: {e}")
        return None


def extract_json_ld(html):
    soup = BeautifulSoup(html, 'html.parser')
    jsonld = []
    for tag in soup.find_all('script', type='application/ld+json'):
        try:
            data = json.loads(tag.string)
            jsonld.append(data)
        except Exception:
            # sometimes JS comments or non-JSON; skip
            continue
    return jsonld


def parse_tracklist_from_html(html):
    soup = BeautifulSoup(html, 'html.parser')
    # Look for ordered/ul lists that might be tracklists
    candidates = []
    for sel in ['ol.tracklist', 'ul.tracklist', 'ol', 'ul', 'div.tracklist', 'section.tracklist']:
        for el in soup.select(sel):
            items = [li.get_text(separator=' ', strip=True) for li in el.find_all('li')]
            if len(items) >= 3:
                candidates.append(items)
    # Heuristic: return the longest candidate
    if candidates:
        candidates.sort(key=len, reverse=True)
        return candidates[0]
    # Fallback: look for numbered lines in paragraphs
    text = soup.get_text('\n')
    numbered = re.findall(r"^\s*\d+[\).\-]\s*(.+)$", text, flags=re.M)
    if numbered:
        return [s.strip() for s in numbered]
    return []


def render_with_playwright(url):
    # Use Playwright to render page and expand 'Show more' if present.
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
            # try to click any "Show more"/"More" buttons
            for txt in ['Show more', 'Show More', 'More', 'Show full', 'Show all']:
                try:
                    btn = page.query_selector(f"button:has-text('{txt}')")
                    if btn:
                        btn.click()
                except Exception:
                    pass
            # Wait a moment for dynamic content
            page.wait_for_timeout(800)
            html = page.content()
            browser.close()
            return html
    except Exception as e:
        print('Playwright render failed for', url, e)
        return None


def collect_bbc():
    print('Collecting BBC programme pages from', BBC_PROGRAMME)
    pg = fetch_url(BBC_PROGRAMME)
    if not pg:
        print('Failed to fetch programme page')
        return []
    soup = BeautifulSoup(pg, 'html.parser')
    # Find episode links (href containing /programmes/ and a date-like context)
    anchors = []
    for a in soup.find_all('a', href=True):
        href = a['href']
        if '/programmes/' in href and 'episodes' in href or re.search(r'/programmes/[a-z0-9]+/episodes', href):
            full = href if href.startswith('http') else 'https://www.bbc.co.uk' + href
            anchors.append(full)
    # dedupe preserving order
    seen = set()
    episodes = []
    for u in anchors:
        if u in seen:
            continue
        seen.add(u)
        episodes.append(u)
        if len(episodes) >= MAX_EPISODES:
            break
    results = []
    for idx, ep in enumerate(episodes, 1):
        print(f'Processing episode {idx}/{len(episodes)}: {ep}')
        html = fetch_url(ep)
        if html:
            name = f'bbc_ep_{idx}.html'
            save(os.path.join(DIAG_DIR, name), html)
            jsonld = extract_json_ld(html)
            if jsonld:
                save(os.path.join(DIAG_DIR, f'bbc_ep_{idx}_jsonld.json'), json.dumps(jsonld, indent=2))
            tracks = []
            # Try JSON-LD
            for entry in jsonld:
                # many schemas use "track" or "trackList"
                if isinstance(entry, dict):
                    for key in ('track', 'trackList', 'tracks', 'hasPart'):
                        if key in entry:
                            candidate = entry[key]
                            # candidate can be list of objects or strings
                            if isinstance(candidate, list):
                                for it in candidate:
                                    if isinstance(it, dict):
                                        t = it.get('name') or it.get('headline') or it.get('item')
                                        if t:
                                            tracks.append(t)
                                    elif isinstance(it, str):
                                        tracks.append(it)
            if not tracks:
                # Try static HTML parsing
                tracks = parse_tracklist_from_html(html)
            if not tracks:
                # Render with Playwright as last resort
                print('No tracks found in static HTML/JSON-LD, trying Playwright render')
                rendered = render_with_playwright(ep)
                if rendered:
                    save(os.path.join(DIAG_DIR, f'bbc_ep_{idx}_rendered.html'), rendered)
                    tracks = parse_tracklist_from_html(rendered)
            status = 'complete' if tracks else 'failed'
            results.append({'url': ep, 'tracks': tracks, 'status': status})
        else:
            results.append({'url': ep, 'tracks': [], 'status': 'failed'})
    out_path = os.path.join(OUT_DIR, 'bbc_tracks.json')
    save(out_path, json.dumps(results, indent=2, ensure_ascii=False))
    print('Saved BBC tracks to', out_path)
    return results


if __name__ == '__main__':
    out = collect_bbc()
    print('BBC collection complete. Episodes:', len(out))
