"""Compile .po to .mo using Python's built-in msgfmt module."""
import sys
import os

# Find Python's Tools/i18n/msgfmt.py
python_path = os.path.dirname(sys.executable)
# Try using the polib approach or manual binary write

import struct
import re

def compile_po(po_path, mo_path):
    messages = {}
    current_msgid = []
    current_msgstr = []
    in_msgid = False
    in_msgstr = False

    with open(po_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                if in_msgstr and current_msgid is not None:
                    mid = ''.join(current_msgid)
                    mstr = ''.join(current_msgstr)
                    if mid or mstr:
                        messages[mid] = mstr
                    current_msgid = []
                    current_msgstr = []
                    in_msgid = False
                    in_msgstr = False
                continue

            if line.startswith('msgid '):
                if in_msgstr and current_msgid is not None:
                    mid = ''.join(current_msgid)
                    mstr = ''.join(current_msgstr)
                    messages[mid] = mstr
                current_msgid = []
                current_msgstr = []
                in_msgid = True
                in_msgstr = False
                val = line[6:].strip()
                if val.startswith('"') and val.endswith('"'):
                    current_msgid.append(val[1:-1])
            elif line.startswith('msgstr '):
                in_msgid = False
                in_msgstr = True
                val = line[7:].strip()
                if val.startswith('"') and val.endswith('"'):
                    current_msgstr.append(val[1:-1])
            elif line.startswith('"') and line.endswith('"'):
                val = line[1:-1]
                if in_msgstr:
                    current_msgstr.append(val)
                elif in_msgid:
                    current_msgid.append(val)

    # Don't forget the last entry
    if in_msgstr:
        mid = ''.join(current_msgid)
        mstr = ''.join(current_msgstr)
        messages[mid] = mstr

    # Build .mo binary
    keys = sorted(messages.keys())
    offsets = []
    ids = b''
    strs = b''

    for key in keys:
        id_bytes = key.encode('utf-8')
        str_bytes = messages[key].encode('utf-8')
        offsets.append((len(ids), len(id_bytes), len(strs), len(str_bytes)))
        ids += id_bytes + b'\x00'
        strs += str_bytes + b'\x00'

    n = len(keys)
    # Header: magic, revision, nstrings, offset_orig, offset_trans, size_hash, offset_hash
    keystart = 28  # 7 * 4
    valuestart = keystart + n * 8

    output = struct.pack(
        'Iiiiiii',
        0x950412de,  # magic
        0,           # revision
        n,           # number of strings
        keystart,    # offset of table with original strings
        valuestart,  # offset of table with translation strings
        0,           # size of hashing table
        0,           # offset of hashing table
    )

    ids_start = keystart + n * 16
    strs_start = ids_start + len(ids)

    for (io, il, so, sl) in offsets:
        output += struct.pack('ii', il, ids_start + io)

    for (io, il, so, sl) in offsets:
        output += struct.pack('ii', sl, strs_start + so)

    output += ids
    output += strs

    with open(mo_path, 'wb') as f:
        f.write(output)

    print(f'Compiled {n} messages to {mo_path}')

if __name__ == '__main__':
    base = os.path.dirname(os.path.abspath(__file__))
    po = os.path.join(base, 'locale', 'hi', 'LC_MESSAGES', 'django.po')
    mo = os.path.join(base, 'locale', 'hi', 'LC_MESSAGES', 'django.mo')
    compile_po(po, mo)
