#!/usr/bin/env python3
"""
Image Encryption and Decryption using AES (Python 3 version)

Pipeline
  Encrypt:  image -> AES-256-CBC -> "visual" cipher image -> 2-share visual cryptography
  Decrypt:  2-share recombination (demo) + AES decryption of the .crypt file -> original image
"""
import os
import hashlib
import binascii
import numpy as np
from PIL import Image
from Crypto.Cipher import AES

import tkinter as tk
from tkinter import filedialog, messagebox

# All generated files go here (next to this script), no matter where you run it from.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

IV = b"This is an IV456"  # kept from the original project (16 bytes)


def out(name):
    return os.path.join(OUTPUT_DIR, name)


# ----------------- Functions for 2-share encryption ---------------------#
def generate_secret(size):
    """Random 'key share' image, twice the width/height of the message."""
    width, height = size
    base = np.random.randint(0, 255, size=(height, width, 3), dtype=np.uint8)
    inv = 255 - base
    secret = np.zeros((height * 2, width * 2, 3), dtype=np.uint8)
    secret[0::2, 0::2] = base
    secret[0::2, 1::2] = inv
    secret[1::2, 0::2] = inv
    secret[1::2, 1::2] = base
    return Image.fromarray(secret, "RGB")


def generate_ciphered_image(secret_image, prepared_image):
    width, height = prepared_image.size
    sec = np.asarray(secret_image, dtype=np.uint16)[0::2, 0::2]
    msg = np.asarray(prepared_image, dtype=np.uint16)
    base = ((msg + sec) % 256).astype(np.uint8)
    inv = 255 - base
    ciphered = np.zeros((height * 2, width * 2, 3), dtype=np.uint8)
    ciphered[0::2, 0::2] = base
    ciphered[0::2, 1::2] = inv
    ciphered[1::2, 0::2] = inv
    ciphered[1::2, 1::2] = base
    return Image.fromarray(ciphered, "RGB")


def generate_image_back(secret_image, ciphered_image):
    sec = np.asarray(secret_image.convert("RGB"), dtype=np.int16)[0::2, 0::2]
    cip = np.asarray(ciphered_image.convert("RGB"), dtype=np.int16)[0::2, 0::2]
    plain = ((cip - sec) % 256).astype(np.uint8)
    return Image.fromarray(plain, "RGB")


def level_one_encrypt(image_path):
    message_image = Image.open(image_path).convert("RGB")
    secret_image = generate_secret(message_image.size)
    secret_image.save(out("secret.png"))                  # PNG = lossless
    ciphered_image = generate_ciphered_image(secret_image, message_image)
    ciphered_image.save(out("2-share_encrypt.png"))


# -------------------- Construct the visual encrypted image ----------------#
def construct_enc_image(ciphertext, relength, width, height):
    hex_text = binascii.hexlify(ciphertext).decode("ascii")

    # replace hex letters with numbers so the text can be read as pixel values
    reps = {chr(ord("a") + i): str(i + 1) for i in range(26)}
    digits = hex_text.translate(str.maketrans(reps))

    step = 3
    chunks = [digits[i:i + step] for i in range(0, len(digits), step)]
    if int(chunks[-1]) < 100:
        chunks[-1] += "1"
    while len(chunks) % 3 != 0:
        chunks.append("101")

    pixels = [
        (min(int(chunks[i]), 255), min(int(chunks[i + 1]), 255), min(int(chunks[i + 2]), 255))
        for i in range(0, len(chunks), step)
    ]
    pixels = pixels[:relength]

    enc = Image.new("RGB", (width, height))
    enc.putdata(pixels)
    enc.save(out("visual_encrypt.png"))


# ------------------------- Encryption -------------------------#
def encrypt(image_path, password):
    im = Image.open(image_path).convert("RGB")      # handles PNG/RGBA/grayscale too
    width, height = im.size
    arr = np.asarray(im, dtype=np.int32)

    # every channel value + 100 so each one is exactly 3 digits
    plaintext = "".join(map(str, (arr.reshape(-1) + 100).tolist()))
    relength = width * height

    # append dimensions for reconstruction after decryption
    plaintext += "h" + str(height) + "h" + "w" + str(width) + "w"

    # pad with "n" to a multiple of 16 (AES block size)
    plaintext += "n" * (-len(plaintext) % 16)

    cipher = AES.new(password, AES.MODE_CBC, IV)
    ciphertext = cipher.encrypt(plaintext.encode("ascii"))

    cipher_name = out(os.path.basename(image_path) + ".crypt")
    with open(cipher_name, "wb") as f:
        f.write(ciphertext)

    construct_enc_image(ciphertext, relength, width, height)
    print("Visual Encryption done.......")
    level_one_encrypt(out("visual_encrypt.png"))
    print("2-Share Encryption done.......")
    return cipher_name


# ------------------------- Decryption -------------------------#
def decrypt(cipher_path, password):
    # 2-share recombination (demonstration step)
    secret_image = Image.open(out("secret.png"))
    shared = Image.open(out("2-share_encrypt.png"))
    generate_image_back(secret_image, shared).save(out("2-share_decrypt.png"))
    print("2-share Decryption done....")

    with open(cipher_path, "rb") as f:
        ciphertext = f.read()

    cipher = AES.new(password, AES.MODE_CBC, IV)
    try:
        decrypted = cipher.decrypt(ciphertext).decode("ascii")
        decrypted = decrypted.replace("n", "")
        new_width = int(decrypted.split("w")[1])
        new_height = int(decrypted.split("h")[1])
    except (UnicodeDecodeError, ValueError, IndexError):
        raise ValueError("Decryption failed - wrong password or not a .crypt file.")

    # strip the height/width markers
    decrypted = decrypted.replace("h%dh" % new_height, "").replace("w%dw" % new_width, "")

    values = [int(decrypted[i:i + 3]) - 100 for i in range(0, len(decrypted), 3)]
    pixels = list(zip(values[0::3], values[1::3], values[2::3]))

    new_im = Image.new("RGB", (new_width, new_height))
    new_im.putdata(pixels)
    result = out("visual_decrypt.png")
    new_im.save(result)
    print("Visual Decryption done......")
    return result


# ---------------------
# GUI
# ---------------------
def make_key(text):
    return hashlib.sha256(text.encode("utf-8")).digest()


class App:
    def __init__(self, master):
        tk.Message(master, text="Image Encryption", font=("helvetica", 17, "bold"), width=200).pack()
        tk.Message(master, text="AES + 2-share visual cryptography", font=("helvetica", 10), width=250).pack()
        tk.Canvas(master, width=200, height=30).pack()

        tk.Label(master, text="Enter Encrypt/Decrypt Password:").pack()
        self.password = tk.Entry(master, show="*", width=20)
        self.password.pack()

        tk.Button(master, text="Encrypt", fg="black", command=self.on_encrypt,
                  width=25, height=5).pack(side=tk.LEFT)
        tk.Button(master, text="Decrypt", fg="black", command=self.on_decrypt,
                  width=25, height=5).pack(side=tk.RIGHT)

    def _get_password(self):
        text = self.password.get()
        if text == "":
            messagebox.showinfo("Password Alert", "Please enter a password.")
            return None
        return make_key(text)

    def on_encrypt(self):
        key = self._get_password()
        if key is None:
            return
        filename = filedialog.askopenfilename(
            title="Select an image to encrypt",
            filetypes=[("Images", "*.jpg *.jpeg *.png *.bmp"), ("All files", "*.*")])
        if not filename:
            return
        try:
            cipher_name = encrypt(filename, key)
            messagebox.showinfo("Success", "Encrypted file:\n" + cipher_name +
                                "\n\nOther outputs are in:\n" + OUTPUT_DIR)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def on_decrypt(self):
        key = self._get_password()
        if key is None:
            return
        filename = filedialog.askopenfilename(
            title="Select the .crypt file to decrypt", initialdir=OUTPUT_DIR,
            filetypes=[("Crypt files", "*.crypt"), ("All files", "*.*")])
        if not filename:
            return
        try:
            result = decrypt(filename, key)
            messagebox.showinfo("Success", "Decrypted image:\n" + result)
        except Exception as e:
            messagebox.showerror("Error", str(e))


if __name__ == "__main__":
    root = tk.Tk()
    root.wm_title("Image Encryption")
    App(root)
    root.mainloop()
