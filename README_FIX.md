# How to run (Python 3)

    pip install -r requirements.txt
    python final.py

Tkinter ships with Python on Windows/macOS. On Ubuntu/Debian: `sudo apt install python3-tk`

Results are written to the `output/` folder next to final.py:
- `<yourimage>.crypt`  -> the AES-encrypted file (select this when decrypting)
- `visual_encrypt.png`, `2-share_encrypt.png`, `secret.png` -> visual encryption stages
- `visual_decrypt.png` -> your recovered original image
