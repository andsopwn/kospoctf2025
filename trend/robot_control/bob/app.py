import socket
import json
import hashlib
import random
import time
import os
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from Crypto.Util.number import long_to_bytes, bytes_to_long
from ecdsa.ecdsa import generator_256, curve_256, Public_key, Signature
from ecdsa.ellipticcurve import Point as eccPoint
from secret import FLAG
from util import *

ALICE_PUB_HOST = os.getenv('ALICE_PUB_HOST', 'localhost')
ALICE_PUB_PORT = 10002

curve = curve_256
generator = generator_256

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
    
    def get_shared_key(self, alice_public_point):
        shared_point = double_and_add(alice_public_point, self.secret)
        shared_x = shared_point.x
        key = hashlib.sha256(long_to_bytes(shared_x)).digest()
        return key[:16]
    
    def get_public_xy(self):
        return (self.public_point.x, self.public_point.y)


class BobServer:
    def __init__(self, host='0.0.0.0', port=8888, flag=FLAG):
        self.host = host
        self.port = port
        self.flag = flag

    def run(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((self.host, self.port))
            s.listen(5)
            print(f"[*] Bob Listening... {self.port}")
            while True:
                conn, addr = s.accept()
                time.sleep(2)
                self.alice_pubkey = self.request_alice_pubkey()
                print(self.alice_pubkey)
                print(f"[*] Connect : {addr}")
                with conn:
                    try:
                        self.handle_client(conn)
                    except Exception as e:
                        print(f"Error : {e}")
                        conn.close()

    def handle_client(self, conn):
        try:
            self.key_manager = ECCKeyManager()
            session_key = self.exchange_ecdh_pubkeys(conn)

            if self.alice_pubkey is None:
                response = {"status": "error", "msg": "No Alice public key"}
            else:
                alice_pub_x = int(self.alice_pubkey['x'])
                alice_pub_y = int(self.alice_pubkey['y'])
                alice_pub_key = Public_key(generator, eccPoint(curve, alice_pub_x, alice_pub_y))

            while True:
                alice_data = json.loads(conn.recv(4096).decode())
                ciphertext = alice_data['cipher']
                iv = alice_data['iv']
                sig_r = int(alice_data['sig_r'])
                sig_s = int(alice_data['sig_s'])

                ciphertext = bytes.fromhex(ciphertext)
                iv = bytes.fromhex(iv)

                cipher = AES.new(session_key, AES.MODE_CBC, iv)
                command = unpad(cipher.decrypt(ciphertext), 16)
                command = json.loads(command.decode())    

                bob_iv = b''.join([random.getrandbits(32).to_bytes(4, 'big') for i in range(4)])
                if self.verify_ecdsa_signature(alice_pub_key, ciphertext, sig_r, sig_s):
                    if command.get('action') == 'connect':
                        response = {'status': 'ok', 'msg': 'Connect Success'}
                    elif command.get('action') == 'check':
                        response = {'status': 'ok', 'msg': 'Connecting'}
                    elif command.get('action') == 'get public key':
                        response = {'status': 'ok', 'msg': 'Bob\'s Public key', 'x': self.key_manager.get_public_xy()[0], 'y': self.key_manager.get_public_xy()[1]}
                    elif command.get('action') == 'build 1':
                        response = {'status': 'ok', 'msg': 'build line 1 success', 'cipher': ciphertext.hex(), 'iv': bob_iv.hex(),'sig_r': hex(sig_r), 'sig_s': hex(sig_s)}
                    elif command.get('action') == 'build 2':
                        response = {'status': 'ok', 'msg': 'build line 2 success', 'cipher': ciphertext.hex(), 'iv': bob_iv.hex(), 'sig_r': hex(sig_r), 'sig_s': hex(sig_s)}
                    elif command.get('action') == 'admin_login':
                        response = {'status': 'ok', 'msg': f'Hello, admin! {self.flag}'}
                    else:
                        response = {'status': 'error', 'msg': 'Unknown command'}
                else:
                    response = {'status': 'error', 'msg': 'Signature verification failed'}

                self.send_encrypted_response(conn, session_key, response, bob_iv)
        except Exception as e:
            print(f'[!] Error : {e}')
            try:
                response = {'status': 'error', 'msg': f'{e}'}
                self.send_encrypted_response(conn, session_key, response, bob_iv)
                conn.close()
            except:
                pass

    def exchange_ecdh_pubkeys(self, conn):
        alice_pub = conn.recv(4096)
        alice_pub = json.loads(alice_pub.decode())
        alice_pub_x = int(alice_pub['pubx'])
        alice_pub_y = int(alice_pub['puby'])
        alice_public = Point(alice_pub_x, alice_pub_y)

        bob_pubx, bob_puby = self.key_manager.get_public_xy()
        bob_pub = {'pubx': int(bob_pubx), 'puby': int(bob_puby)}
        conn.sendall(json.dumps(bob_pub).encode())
        session_key = self.key_manager.get_shared_key(alice_public)
        return session_key

    def request_alice_pubkey(self):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((ALICE_PUB_HOST, ALICE_PUB_PORT))
                alice_pub = s.recv(4096)
                alice_pub = json.loads(alice_pub.decode())

                if 'x' in alice_pub and 'y' in alice_pub:
                    return alice_pub
                else:
                    return None
        except Exception as e:
            print(f'Public key request failed : {e}')
            return None

    def verify_ecdsa_signature(self, pub_key, cipher, r, s):
        signed_data = cipher.hex()
        hash_msg = bytes_to_long(hashlib.sha256(signed_data.encode()).digest())
        sig = Signature(r, s)
        if pub_key.verifies(hash_msg, sig):
            print('signature verified')
            return True
        else:
            print('signature not valid')
            return False

    def send_encrypted_response(self, conn, session_key, response_dict, iv):
        response = json.dumps(response_dict).encode()
        cipher = AES.new(session_key, AES.MODE_CBC, iv)
        ciphertext = cipher.encrypt(pad(response, 16))
        resp_json = {'cipher': ciphertext.hex(), 'iv': iv.hex()}
        conn.sendall(json.dumps(resp_json).encode())

if __name__ == '__main__':
    server = BobServer()
    server.run()