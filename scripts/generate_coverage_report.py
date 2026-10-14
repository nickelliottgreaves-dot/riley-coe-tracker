#!/usr/bin/env python3
"""Generate a simple coverage report from the outputs produced by collectors."""
import os
import json
from datetime import datetime

OUT_DIR = 'outputs'
REPORTS = 'reports'
os.makedirs(REPORTS, exist_ok=True)


def load_json(name):
    p = os.path.join(OUT_DIR, name)
    if os.path.exists(p):
        with open(p, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


def summarize():
    bbc = load_json('bbc_tracks.json')
    rf = load_json('radiofiles_tracks.json')
    mc = load_json('mixcloud_tracks.json')
    now = datetime.utcnow().date().isoformat()
    report = []
    report.append(f'# Riley & Coe coverage report ({now})')
    report.append('')
    report.append(f'* BBC episodes processed: {len(bbc)}')
    report.append(f'* RadioFiles episodes processed: {len(rf)}')
    report.append(f'* Mixcloud uploads processed: {len(mc)}')
    report.append('')
    def count_tracks(listing):
        c = 0
        for e in listing:
            if e.get('tracks'):
                c += len(e.get('tracks', []))
        return c
    report.append(f'* BBC tracks extracted: {count_tracks(bbc)}')
    report.append(f'* RadioFiles tracks extracted: {count_tracks(rf)}')
    report.append(f'* Mixcloud tracks extracted: {count_tracks(mc)}')
    report.append('')
    # New artists candidates (placeholder)
    report.append('## New artist candidates')
    report.append('See outputs/new_artists_candidates.json if present.')
    md = '\n'.join(report)
    outp = os.path.join(REPORTS, f'coverage_{now}.md')
    with open(outp, 'w', encoding='utf-8') as f:
        f.write(md)
    print('Wrote report to', outp)


if __name__ == '__main__':
    summarize()
