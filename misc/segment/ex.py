import sys, csv, math

HEX_7SEG = {
    0: 0b0111111,
    1: 0b0000110,
    2: 0b1011011,
    3: 0b1001111,
    4: 0b1100110,
    5: 0b1101101,
    6: 0b1111101,
    7: 0b0000111,
    8: 0b1111111,
    9: 0b1101111,
    10: 0b1110111,  
    11: 0b1111100, 
    12: 0b0111001,  
    13: 0b1011110,
    14: 0b1111001,
    15: 0b1110001,
}
VALID_MASKS = set(HEX_7SEG.values())

def read_csv_last_states(path, gap_threshold=0.5):
    with open(path, newline='') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    for r in rows:
        r["time"] = float(r["Time [s]"])
        for i in range(8):
            r[f"Channel {i}"] = int(r[f"Channel {i}"])
    bursts = []
    cur = []
    prev_t = None
    for r in rows:
        t = r["time"]
        if prev_t is not None and (t - prev_t) > gap_threshold:
            if cur:
                bursts.append(cur)
                cur = []
        cur.append(r)
        prev_t = t
    if cur:
        bursts.append(cur)
    last_states = [b[-1] for b in bursts]
    return last_states

def seven_seg_mask_from_state(state, active_low=True):
    bits = [state[f"Channel {i}"] for i in range(7)]
    if active_low:
        bits = [1-b for b in bits]
    mask = 0
    for i,b in enumerate(bits):
        mask |= (b & 1) << i
    return mask

def decode_digits(last_states):
    digits = []
    for st in last_states:
        m = seven_seg_mask_from_state(st, active_low=True)
        if m in VALID_MASKS:
            val = next(k for k,v in HEX_7SEG.items() if v == m)
            digits.append(val)
        else:
            digits.append(None)
    return digits

def to_hex_string(digits):
    out = []
    for d in digits:
        if d is None:
            out.append('.')  
        else:
            out.append(hex(d)[2:].upper())
    return ''.join(out)

def compact_hex(digits):
    return ''.join(hex(d)[2:] if d is not None else '' for d in digits)

def try_hex_align(hex_str):
    """
    We observed an odd # of nibbles. Try two alignments by trimming 1 nibble
    either at start or at end, then hex-decode and measure 'english' score.
    """
    import binascii
    cands = []
    if len(hex_str) % 2 == 1:
        a = hex_str[1:]
        try:
            cands.append((a, binascii.unhexlify(a)))
        except Exception:
            pass
        b = hex_str[:-1]
        try:
            cands.append((b, binascii.unhexlify(b)))
        except Exception:
            pass
    else:
        try:
            cands.append((hex_str, bytes.fromhex(hex_str)))
        except Exception:
            pass
    def score(bs):
        s = bs.decode('utf-8', errors='ignore')
        printable = sum(1 for ch in s if 32 <= ord(ch) <= 126)/max(1,len(s))
        bonus = 0
        for tok in ["hardware","capture","logic","flag","saleae","digital","analog"]:
            if tok in s.lower():
                bonus += 0.5
        return printable + bonus, s
    scored = sorted([(score(bs)[0], hx, bs) for hx,bs in cands], reverse=True)
    return scored

def main():
    path = sys.argv[1] if len(sys.argv)>1 else "digital.csv"
    last_states = read_csv_last_states(path)
    digits = decode_digits(last_states)
    hex_full = to_hex_string(digits)
    hex_compact = compact_hex(digits)
    print("[*] 7-seg (active-low):")
    print("    ", hex_full)
    print("[*] :", hex_compact)
    scored = try_hex_align(hex_compact)
    print("[*] Alignment tries:")
    for sc, hx, bs in scored:
        try_txt = bs.decode('utf-8', errors='ignore')
        print(f"    score={sc:.3f}  hex={hx}\n      ascii={try_txt}")

    best = scored[0] if scored else None
    if best:
        _, hx, bs = best
        text = bs.decode('utf-8', errors='ignore')
        print("\n[+] ", text)
        if text.lower().startswith("flag{") and text.endswith("}"):
            flag = text
        else:
            flag = f"flag{{{text}}}"
        print("[+] FLAG =", flag)
    else: 
        pass

if __name__ == "__main__":
    main()
