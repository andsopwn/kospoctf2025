import socket
import json
import hashlib
import random
import os
import time
import threading
from Crypto.Util.number import bytes_to_long, long_to_bytes
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from ecdsa.ecdsa import Public_key, Private_key, Signature, generator_256, curve_256
from util import *

BANNER = """
  _____       _           _      _____            _             _    _____           _                 
 |  __ \\     | |         | |    / ____|          | |           | |  / ____|         | |                
 | |__) |___ | |__   ___ | |_  | |     ___  _ __ | |_ _ __ ___ | | | (___  _   _ ___| |_ ___ _ __ ___  
 |  _  // _ \\| '_ \\ / _ \\| __| | |    / _ \\| '_ \\| __| '__/ _ \\| |  \\___ \\| | | / __| __/ _ \\ '_ ` _ \\ 
 | | \\ \\ (_) | |_) | (_) | |_  | |___| (_) | | | | |_| | | (_) | |  ____) | |_| \\__ \\ ||  __/ | | | | |
 |_|  \\_\\___/|_.__/ \\___/ \\__|  \\_____\\___/|_| |_|\\__|_|  \\___/|_| |_____/ \\__, |___/\\__\\___|_| |_| |_|
                                                                            __/ |                      
                                                                           |___/                       
Select Mode
1. Connect Robot
2. Check Status
3. get public key
4. Send Command
5. Help
x. Exit
"""
BOB_HOST = os.getenv('BOB_HOST', 'localhost')
BOB_PORT = 8888
PUBKEY_SERVER_PORT = 10002

connected = False

curve = curve_256
generator = generator_256

class ECDSA:
    def __init__(self):
        self.k = random.randrange(curve.p())
        self.secret = random.randrange(curve.p())
        self.public_key = Public_key(generator, generator * self.secret)
        self.private_key = Private_key(self.public_key, self.secret)

    def sign(self, msg):
        message = bytes_to_long(hashlib.sha256(msg.encode()).digest())
        sign_data = self.private_key.sign(message, self.k)
        return (sign_data.r, sign_data.s)
    
    def verify(self, msg, r, s):
        hash_msg = bytes_to_long(hashlib.sha256(msg.encode()).digest())
        sig = Signature(r, s)

        return self.public_key.verifies(hash_msg, sig)

class ECCKeyManager:
    def __init__(self):
        self.p = p
        self.a = a
        self.b = b
        self.Gx = Gx
        self.Gy = Gy
        self.generator = Point(self.Gx, self.Gy)
        self.secret = random.randrange(10**5, 10**6)
        self.public_point = double_and_add(self.generator, self.secret)

    def get_shared_key(self, bob_public_point):
        shared_point = double_and_add(bob_public_point, self.secret)
        shared_x = shared_point.x
        key = hashlib.sha256(long_to_bytes(shared_x)).digest()
        return key[:16]
    
    def get_public_xy(self):
        return (self.public_point.x, self.public_point.y)

alice_ecdsa_global = None

def alice_pubkey_server():
    global alice_ecdsa_global
    while alice_ecdsa_global is None:
        time.sleep(0.1)
    
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        try:
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind(("0.0.0.0", PUBKEY_SERVER_PORT))
            server.listen(5)
            print(f"[Alice pubkey server] Alice Public Key Server Listening...")
            conn, addr = server.accept()
            with conn:
                try:
                    pub = alice_ecdsa_global.public_key
                    resp = {'x': int(pub.point.x()), 'y': int(pub.point.y())}
                    conn.sendall(json.dumps(resp).encode())
                    conn.close()
                except Exception as e:
                    print(f'[Alice pubkey server] Error: {e}')
        except OSError:
            print(f"[Alice pubkey server] Alice Public Key Server Listening...")

def send_command(command, session_key, alice_ecdsa, sock, r = None, s = None, user_ciphertext = None, user_iv = None):
    cmd_json = json.dumps(command)

    iv = os.urandom(16)
    cipher = AES.new(session_key, AES.MODE_CBC, iv)
    ciphertext = cipher.encrypt(pad(cmd_json.encode(), 16))

    data = ciphertext.hex()
    sig_r, sig_s = alice_ecdsa.sign(data)

    if r is None and s is None and user_ciphertext is None:
        send_data = {
            'cipher': ciphertext.hex(),
            'iv': iv.hex(),
            'sig_r': int(sig_r),
            'sig_s': int(sig_s)
        }
    else:
        send_data = {
            'cipher': user_ciphertext,
            'iv': user_iv,
            'sig_r': r,
            'sig_s': s
        }
    sock.sendall(json.dumps(send_data).encode())

    bob_response = json.loads(sock.recv(4096).decode())
    resp_cipher = bytes.fromhex(bob_response['cipher'])
    resp_iv = bytes.fromhex(bob_response['iv'])
    cipher = AES.new(session_key, AES.MODE_CBC, resp_iv)
    bob_msg = unpad(cipher.decrypt(resp_cipher), 16)
    print(f'[Bob response] : {bob_msg.decode()}')

def alice_send_command():
    global alice_ecdsa_global
    global connected
    alice_ecdh = ECCKeyManager()
    alice_ecdsa = ECDSA()
    alice_ecdsa_global = alice_ecdsa

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((BOB_HOST, BOB_PORT))

        pubx, puby = alice_ecdh.get_public_xy()
        alice_pub = {'pubx': int(pubx), 'puby': int(puby)}
        print(alice_pub)
        s.sendall(json.dumps(alice_pub).encode())

        bob_msg = s.recv(4096)
        bob_pub = json.loads(bob_msg.decode())
        bob_pub_x = int(bob_pub['pubx'])
        bob_pub_y = int(bob_pub['puby'])
        bob_pub_point = Point(bob_pub_x, bob_pub_y)
        session_key = alice_ecdh.get_shared_key(bob_pub_point)

        print(BANNER)

        while True:
            try:
                raw = input('>>> ').strip()
                mode = int(raw)

                if mode == 1:
                    command = {'action': 'connect'}
                    send_command(command, session_key, alice_ecdsa, s)
                    connected = True
                elif mode == 2:
                    if not connected:
                        print('It must be connected to a robot!')
                        continue
                    command = {'action': 'check'}
                    send_command(command, session_key, alice_ecdsa, s)
                elif mode == 3:
                    if not connected:
                        print('It must be connected to a robot!')
                        continue
                    command = {'action': 'get public key'}
                    send_command(command, session_key, alice_ecdsa, s)
                elif mode == 4:
                    if not connected:
                        print('It must be connected to a robot!')
                        continue
                    user = input('command > ')
                    command = {'action': user}

                    if user == 'admin_login':
                        ciphertext = input('ciphertext(hex) > ')
                        iv = input('iv(hex) > ')
                        sig_r = int(input('signature r > '))
                        sig_s = int(input('signature s > '))
                        send_command(command, session_key, alice_ecdsa, s, sig_r, sig_s, ciphertext, iv)
                    else:
                        send_command(command, session_key, alice_ecdsa, s)
                elif mode == 5:
                    if not connected:
                        print('It must be connected to a robot!')
                        continue
                    print('Available Command : build 1, build 2, admin_login')
                else:
                    exit(0)
            except Exception as e:
                print('Input Error')
                continue

if __name__ == '__main__':
    t = threading.Thread(target=alice_pubkey_server, daemon=True)
    t.start()
    alice_send_command()