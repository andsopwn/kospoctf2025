#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pwn import *
import json, ast, re, os, random, hashlib
from collectpns import namedtuple
from Crypto.Util.number import bytes_to_long, long_to_bytes, inverse
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

context.log_level = 'debug'

ALICE_HOST = '43.202.182.33' #CLI
ALICE_PORT = 25134
ALICE_PUB_HOST = '43.202.182.33'
ALICE_PUB_PORT = 8200

Point = namedtuple("Point", "x y")
O = 'Origin'
p_ecdh  = 71730160915158470462329350336535216937787841188608784909744826718070449141371
a_ecdh  = -3
b_ecdh  = 2
Gx_ecdh = 54984515395731302184441403870926819092614483923918408881755232544415386808176
Gy_ecdh = 14326644985312175302794771363500104250330703615035771600068616713496442645143

def inv_mod(a, m): return inverse(a % m, m)

def add_ecdh(P, Q):
    if P == O: return Q
    if Q == O: return P
    if Q.x == P.x and (Q.y + P.y) % p_ecdh == 0: return O
    if P.x == Q.x and P.y == Q.y:
        lam = (3*P.x*P.x + a_ecdh) * inv_mod(2*P.y, p_ecdh) % p_ecdh
    else:
        lam = (Q.y - P.y) * inv_mod((Q.x - P.x) % p_ecdh, p_ecdh) % p_ecdh
    Rx = (lam*lam - P.x - Q.x) % p_ecdh
    Ry = (lam*(P.x - Rx) - P.y) % p_ecdh
    return Point(Rx, Ry)

def mul_ecdh(P, k):
    R = O; Q = P
    while k > 0:
        if k & 1: R = add_ecdh(R, Q)
        Q = add_ecdh(Q, Q)
        k >>= 1
    return R

Point256 = namedtuple("Point256", "x y")
p256  = 0xffffffff00000001000000000000000000000000ffffffffffffffffffffffff
a256  = 0xffffffff00000001000000000000000000000000fffffffffffffffffffffffc
b256  = 0x5ac635d8aa3a93e7b3ebbd55769886bc651d06b0cc53b0f63bce3c3e27d2604b
Gx256 = 0x6b17d1f2e12c4247f8bce6e563a440f277037d812deb33a0f4a13945d898c296
Gy256 = 0x4fe342e2fe1a7f9b8ee7eb4a7c0f9e162bce33576b315ececbb6406837bf51f5
n256  = 0xffffffff00000000ffffffffffffffffbce6faada7179e84f3b9cac2fc632551

def add_p256(P, Q):
    if P is None: return Q
    if Q is None: return P
    if P.x == Q.x and (P.y + Q.y) % p256 == 0: return None
    if P.x == Q.x and P.y == Q.y:
        lam = (3*P.x*P.x + a256) * inv_mod(2*P.y, p256) % p256
    else:
        lam = (Q.y - P.y) * inv_mod((Q.x - P.x) % p256, p256) % p256
    Rx = (lam*lam - P.x - Q.x) % p256
    Ry = (lam*(P.x - Rx) - P.y) % p256
    return Point256(Rx, Ry)

def mul_p256(P, k):
    R = None; Q = P
    while k > 0:
        if k & 1: R = add_p256(R, Q)
        Q = add_p256(Q, Q)
        k >>= 1
    return R

def parse_first_dict(s: bytes):
    t = s.decode(errors='ignore')
    m = re.search(r'(\{.*\})', t, re.DOTALL)
    if not m: return None
    frag = m.group(1)
    try: return json.loads(frag)
    except: return ast.literal_eval(frag)

def parse_bob_json_from_cli(blob: bytes):
    t = blob.decode(errors='ignore')
    m = re.search(r'\{.*\}', t, re.DOTALL)
    if not m: return None
    frag = m.group(0)
    try: return json.loads(frag)
    except: return ast.literal_eval(frag)

def h_hex(s: str) -> int:
    return bytes_to_long(hashlib.sha256(s.encode()).digest())

def recv_prompt(p):
    return p.recvuntil(b'>>> ', timeout=5)

def recover_k_d_p256(e1, e2, s1, s2, r):
    num = (e1 - e2) % n256
    den = (s1 - s2) % n256
    k = (num * inv_mod(den, n256)) % n256
    d = ((s1 * k - e1) * inv_mod(r % n256, n256)) % n256
    return int(k), int(d)

def sign_with_k_p256(e, d, k):
    R = mul_p256(Point256(Gx256, Gy256), k % n256)
    r = (R.x % n256)
    s = (inv_mod(k, n256) * ((e % n256) + (d * r) % n256)) % n256
    return int(r), int(s)

def main():
    try:
        r = remote(ALICE_PUB_HOST, ALICE_PUB_PORT, timeout=2)
        r.recvrepeat(timeout=0.5); r.close()
    except:
        pass

    p = remote(ALICE_HOST, ALICE_PORT)
    banner = p.recvrepeat(timeout=2)
    alice_pub = parse_first_dict(banner)
    if not alice_pub:
        p.recvuntil(b'\n', timeout=1)
        more = p.recvrepeat(timeout=1)
        alice_pub = parse_first_dict(more)
    Ax, Ay = int(alice_pub['pubx']), int(alice_pub['puby'])
    Apoint = Point(Ax, Ay)

    recv_prompt(p)

    p.sendline(b'1')
    p.recvrepeat(timeout=1.0)
    recv_prompt(p)

    p.sendline(b'3')
    data = p.recvrepeat(timeout=1.5)
    bj = parse_bob_json_from_cli(data)
    Bx, By = int(bj['x']), int(bj['y'])
    Bpoint = Point(Bx, By)
    recv_prompt(p)

    p.sendline(b'4'); p.recvuntil(b'command > ', timeout=2); p.sendline(b'build 1')
    d1 = p.recvrepeat(timeout=1.5)
    j1 = parse_bob_json_from_cli(d1); assert j1 and j1.get('status') == 'ok'
    c1_hex = j1['cipher']
    r1 = int(j1['sig_r'], 16) if isinstance(j1['sig_r'], str) and j1['sig_r'].startswith('0x') else int(j1['sig_r'])
    s1 = int(j1['sig_s'], 16) if isinstance(j1['sig_s'], str) and j1['sig_s'].startswith('0x') else int(j1['sig_s'])
    e1 = h_hex(c1_hex)
    recv_prompt(p)

    p.sendline(b'4'); p.recvuntil(b'command > ', timeout=2); p.sendline(b'build 2')
    d2 = p.recvrepeat(timeout=1.5)
    j2 = parse_bob_json_from_cli(d2); assert j2 and j2.get('status') == 'ok'
    c2_hex = j2['cipher']
    r2 = int(j2['sig_r'], 16) if isinstance(j2['sig_r'], str) and j2['sig_r'].startswith('0x') else int(j2['sig_r'])
    s2 = int(j2['sig_s'], 16) if isinstance(j2['sig_s'], str) and j2['sig_s'].startswith('0x') else int(j2['sig_s'])
    e2 = h_hex(c2_hex)
    recv_prompt(p)

    assert r1 == r2
    r_val = r1 % n256
    k, d = recover_k_d_p256(e1, e2, s1 % n256, s2 % n256, r_val)
    log.success(f"k = {k}")
    log.success(f"d = {d}")

    G_ecdh = Point(Gx_ecdh, Gy_ecdh)
    sA = None
    for t in range(100000, 1000000):
        if mul_ecdh(G_ecdh, t) == Apoint:
            sA = t; break
    assert sA is not None
    log.success(f"Alice ECDH secret sA = {sA}")

    shared = mul_ecdh(Bpoint, sA)
    K = hashlib.sha256(long_to_bytes(shared.x)).digest()[:16]
    log.success(f"sesspn key K = {K.hex()}")

    iv_admin = os.urandom(16)
    pt = json.dumps({'actpn': 'admin_login'}).encode()
    c_admin = AES.new(K, AES.MODE_CBC, iv_admin).encrypt(pad(pt, 16))
    c_admin_hex = c_admin.hex()
    e_admin = h_hex(c_admin_hex)
    k2 = random.randrange(1, n256-1)
    r_admin, s_admin = sign_with_k_p256(e_admin, d, k2)

    p.sendline(b'4'); p.recvuntil(b'command > ', timeout=2); p.sendline(b'admin_login')
    p.recvuntil(b'ciphertext(hex) > ', timeout=2); p.sendline(c_admin_hex.encode())
    p.recvuntil(b'iv(hex) > ', timeout=2);        p.sendline(iv_admin.hex().encode())
    p.recvuntil(b'signature r > ', timeout=2);    p.sendline(str(r_admin).encode())
    p.recvuntil(b'signature s > ', timeout=2);    p.sendline(str(s_admin).encode())

    final = p.recvrepeat(timeout=3)
    print(final.decode(errors='ignore'))
    p.close()

if __name__ == '__main__':
    main()
