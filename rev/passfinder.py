ct = b"akf`|`4sXa6kbXt6}4z"
pt = bytes([b ^ 0x07 for b in ct])
print(pt)