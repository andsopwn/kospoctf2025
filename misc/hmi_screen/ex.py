from PIL import Image
import re
img = Image.open('chall.png').convert('RGB')
w, h = img.size
px = img.load()

g_bits, b_bits = [], []
for y in range(h):
    for x in range(w):
        r, g, b = px[x, y]
        g_bits.append(g & 1)
        b_bits.append(b & 1)

def bits_to_bytes(bits):
    out, acc, n = bytearray(), 0, 0
    for bit in bits:
        acc = (acc << 1) | (bit & 1)
        n += 1
        if n == 8:
            out.append(acc)
            acc = 0
            n = 0
    return bytes(out)

g = bits_to_bytes(g_bits)
b = bits_to_bytes(b_bits)
x = bytes(a ^ c for a, c in zip(g, b))
m = re.search(rb'flag\{[^}]+\}', x, re.I)
if m:
    print(m.group(0).decode())
