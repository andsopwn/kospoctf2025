#!/usr/bin/env python3
"""
Decode a flag from Saleae Logic export of an 8‑channel digital capture
where channels 0..6 drive a 7‑segment display (active‑low) and each
"burst" of quick transitions corresponds to one digit. The digits spell
hex, which in turn decodes to ASCII and (likely) a CTF flag.

Input:  digital.csv  (Saleae CSV: columns = Time [s], Channel 0..7)
Output: prints decoded characters and best flag guess; writes /mnt/data/decoded.txt

Usage:
    python decode_7seg_flag.py [--csv PATH] [--gap 0.01]

Notes:
- Channel mapping assumed: Channel 0..6 -> segments a..g (active‑low).
- If your wiring differs, add a PERM tuple to remap channels.
- We use majority vote within each burst (more robust than last sample).
"""

import argparse
import pandas as pd
import numpy as np
import re
from pathlib import Path

SEGMENTS = list('abcdefg')
# Canonical 7‑seg glyphs (hex digits + a few letters) as sets of segments that are ON
SEG_CHARS = {
    '0': set('abcdef'),
    '1': set('bc'),
    '2': set('abged'),
    '3': set('abgcd'),
    '4': set('fgbc'),
    '5': set('afgcd'),
    '6': set('afgcde'),
    '7': set('abc'),
    '8': set('abcdefg'),
    '9': set('abcfgd'),
    'A': set('abcefg'),
    'b': set('fgcde'),
    'C': set('afed'),
    'c': set('ged'),
    'd': set('gbcde'),
    'E': set('afged'),
    'F': set('afge'),
    '-': set('g'),
    ' ': set(),
}

# Prefer to decode to these characters when multiple glyphs share the same segments
PREF_ORDER = ['0','1','2','3','4','5','6','7','8','9','A','E','F','C','d','b','c','-',' ']
SEG_TO_CHAR = {frozenset(SEG_CHARS[ch]): ch for ch in PREF_ORDER}


def group_indices(times: np.ndarray, gap_threshold: float) -> list[tuple[int,int]]:
    gaps = np.diff(times)
    groups = []
    start = 0
    for i, g in enumerate(gaps, start=1):
        if g > gap_threshold:
            groups.append((start, i-1))
            start = i
    groups.append((start, len(times)-1))
    return groups


def decode_group_majority(df: pd.DataFrame, s: int, e: int, perm: tuple[int,...]) -> str:
    """Majority vote per channel within [s,e], active‑low, then map to glyph."""
    sub = df.iloc[s:e+1]
    on_bits = []  # 1 = segment ON
    for ch in range(7):
        vals = sub[f'Channel {ch}'].to_numpy()
        ones = int(vals.sum())
        zeros = len(vals) - ones
        bit = 1 if ones > zeros else 0 if zeros > ones else int(vals[-1])
        on_bits.append(1 - bit)  # active‑low
    # Apply channel->segment permutation
    on_segs = {SEGMENTS[perm[i]] for i, v in enumerate(on_bits) if v == 1}
    return SEG_TO_CHAR.get(frozenset(on_segs), '?')


def clean_hex(s: str) -> str:
    s = ''.join(ch for ch in s if ch in '0123456789ABCDEFabcdef')
    if len(s) % 2 == 1:
        # Heuristic: drop first nibble if odd
        s = s[1:]
    return s


def try_decode(csv_path: Path, gap: float, perm: tuple[int,...]) -> dict:
    df = pd.read_csv(csv_path)
    times = df['Time [s]'].to_numpy()
    groups = group_indices(times, gap)

    chars = [decode_group_majority(df, s, e, perm) for s, e in groups]
    text = ''.join(chars)

    hex_str = clean_hex(text)
    bytes_raw = bytes.fromhex(hex_str) if hex_str else b''
    ascii_txt = bytes_raw.decode('ascii', errors='replace')

    # Flag candidates
    candidates = re.findall(r'(?i)(?:flag|ctf)\{[ -~]{0,80}?\}', ascii_txt)

    # Save
    out = {
        'num_groups': len(groups),
        'decoded_7seg': text,
        'hex_str': hex_str,
        'ascii_from_hex': ascii_txt,
        'flag_candidates': candidates,
    }
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--csv', default='digital.csv', help='Path to Saleae digital CSV export')
    p.add_argument('--gap', type=float, default=0.01, help='Gap (seconds) separating bursts; default=0.01')
    p.add_argument('--perm', default='0,1,2,3,4,5,6', help='Permutation mapping Channel 0..6 -> segments a..g (comma‑sep indices)')
    args = p.parse_args()

    perm = tuple(int(x) for x in args.perm.split(','))
    assert len(perm) == 7 and sorted(perm) == list(range(7)), 'perm must be a permutation of 0..6'

    res = try_decode(Path(args.csv), args.gap, perm)

    print('[*] Groups           :', res['num_groups'])
    print('[*] 7‑seg decoded    :', res['decoded_7seg'])
    print('[*] As hex           :', res['hex_str'])
    print('[*] Hex->ASCII       :', res['ascii_from_hex'])
    if res['flag_candidates']:
        print('[*] Flag candidate(s):', res['flag_candidates'])
    else:
        print('[!] No {flag,ctf}{...} found yet. Inspect ascii_from_hex above.')

    out_path = Path('decoded.txt')
    out_path.write_text(
        '\n'.join([
            f"7‑seg decoded: {res['decoded_7seg']}",
            f"Hex:           {res['hex_str']}",
            f"ASCII:         {res['ascii_from_hex']}",
            f"Flags:         {res['flag_candidates']}",
        ]),
        encoding='utf-8')
    print(f'[*] Wrote {out_path}')


if __name__ == '__main__':
    main()
