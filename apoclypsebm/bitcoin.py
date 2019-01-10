"""
Bitcoin Network and Consensus Rules Code
Derived from BIP reference code and the Electrum project.

https://github.com/bitcoin/bips (various licenses)
https://github.com/spesmilo/electrum (MIT license)
https://github.com/vsergeev/ntgbtminer (MIT license)
"""
from enum import IntEnum
from hashlib import sha256

BASE_58_CHARS = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
BECH_32_CHARS = 'qpzry9x8gf2tvdw0s3jn54khce6mua7l'


class OpCode(IntEnum):
    OP_0 = 0
    OP_1 = 81
    OP_1NEGATE = 79


class BitcoinMainnet:
    TESTNET = False
    WIF_PREFIX = 0x80
    ADDRTYPE_P2PKH = 0
    ADDRTYPE_P2SH = 5
    SEGWIT_HRP = "bc"


class BitcoinTestnet:
    TESTNET = True
    WIF_PREFIX = 0xef
    ADDRTYPE_P2PKH = 111
    ADDRTYPE_P2SH = 196
    SEGWIT_HRP = "tb"


def b58_address_to_type_and_hash160(s):
    x = 0
    s = s[::-1]
    for i in range(len(s)):
        x += (58 ** i) * BASE_58_CHARS.find(s[i])

    # Convert number to 25 bytes
    x = x.to_bytes(25, 'big', signed=False)

    # Discard 4-byte checksum at the end
    return x[0], x[1:-4]


def bech32_polymod(values):
    """Internal function that computes the Bech32 checksum."""
    generator = (0x3b6a57b2, 0x26508e6d, 0x1ea119fa, 0x3d4233dd, 0x2a1462b3)
    chk = 1
    for value in values:
        top = chk >> 25
        chk = (chk & 0x1ffffff) << 5 ^ value
        for i in range(5):
            chk ^= generator[i] if ((top >> i) & 1) else 0
    return chk


def bech32_hrp_expand(hrp):
    """Expand the HRP into values for checksum computation."""
    return [ord(x) >> 5 for x in hrp] + [0] + [ord(x) & 31 for x in hrp]


def bech32_verify_checksum(hrp, data):
    """Verify a checksum given HRP and converted data characters."""
    return bech32_polymod(bech32_hrp_expand(hrp) + data) == 1


def bech32_decode(bech):
    """Validate a Bech32 string, and determine HRP and data."""
    if ((any(ord(x) < 33 or ord(x) > 126 for x in bech)) or
            (bech.lower() != bech and bech.upper() != bech)):
        return (None, None)
    bech = bech.lower()
    pos = bech.rfind('1')
    if pos < 1 or pos + 7 > len(bech) or len(bech) > 90:
        return (None, None)
    if not all(x in BECH_32_CHARS for x in bech[pos+1:]):
        return (None, None)
    hrp = bech[:pos]
    data = [BECH_32_CHARS.find(x) for x in bech[pos+1:]]
    if not bech32_verify_checksum(hrp, data):
        return (None, None)
    return (hrp, data[:-6])


def convertbits(data, frombits, tobits, pad=True):
    """General power-of-2 base conversion."""
    acc = 0
    bits = 0
    ret = []
    maxv = (1 << tobits) - 1
    max_acc = (1 << (frombits + tobits - 1)) - 1
    for value in data:
        if value < 0 or (value >> frombits):
            return None
        acc = ((acc << frombits) | value) & max_acc
        bits += frombits
        while bits >= tobits:
            bits -= tobits
            ret.append((acc >> bits) & maxv)
    if pad:
        if bits:
            ret.append((acc << (tobits - bits)) & maxv)
    elif bits >= frombits or ((acc << (tobits - bits)) & maxv):
        return None
    return ret


def segwit_addr_decode(hrp, addr):
    """Decode a segwit address."""
    hrpgot, data = bech32_decode(addr)
    if hrpgot != hrp:
        return None, None
    decoded = convertbits(data[1:], 5, 8, False)
    if decoded is None or len(decoded) < 2 or len(decoded) > 40:
        return None, None
    if data[0] > 16:
        return None, None
    if data[0] == 0 and len(decoded) != 20 and len(decoded) != 32:
        return None, None
    return data[0], decoded


def push_script(data):
    """Returns pushed data to the script, automatically
    choosing canonical opcodes depending on the length of the data.

    Adapted from
    https://github.com/btcsuite/btcd/blob/fdc2bc867bda6b351191b5872d2da8270df00d13/txscript/scriptbuilder.go#L128
    """
    data_len = len(data)

    # "small integer" opcodes
    if data_len == 0 or data_len == 1 and data[0] == 0:
        return bytes((OpCode.OP_0,))
    elif data_len == 1 and data[0] <= 16:
        return bytes((OpCode.OP_1 - 1 + data[0],))
    elif data_len == 1 and data[0] == 0x81:
        return bytes((OpCode.OP_1NEGATE,))

    return op_push(data_len) + data


def address_to_script(addr, *, net=None):
    if net is None:
        net = BitcoinMainnet
    witver, witprog = segwit_addr_decode(net.SEGWIT_HRP, addr)
    if witprog is not None:
        if not (0 <= witver <= 16):
            raise Exception('impossible witness version: {}'.format(witver))
        OP_n = witver + 0x50 if witver > 0 else 0
        script = (bytes((OP_n,)) + push_script(bytes(witprog)))
        return script
    addrtype, hash_160 = b58_address_to_type_and_hash160(addr)
    if addrtype == net.ADDRTYPE_P2PKH:
        script = (b'\x76\xa9' +  # op_dup, op_hash_160
                  push_script(hash_160) +
                  b'\x88\xac')                  # op_equalverify, op_checksig
    elif addrtype == net.ADDRTYPE_P2SH:
        script = (b'\xa9' +  # op_hash_160
                  push_script(hash_160) +
                  b'\x87')                      # op_equal
    else:
        raise Exception('unknown address type: {}'.format(addrtype))
    return script


def encode_coinbase_height(n):
    encoded = n.to_bytes((n.bit_length() + 8) // 8, 'little', signed=True)
    return len(encoded).to_bytes(1, 'little') + encoded


def op_push(i: int) -> bytes:
    if i < 0x4c:  # OP_PUSHDATA1
        return i.to_bytes(1, 'little', signed=True)
    elif i <= 0xff:
        return b'\x4c' + i.to_bytes(1, 'little', signed=True)
    elif i <= 0xffff:
        return b'\x4d' + i.to_bytes(2, 'little', signed=True)
    else:
        return b'\x4e' + i.to_bytes(4, 'little', signed=True)


def var_int(i: int) -> bytes:
    # https://en.bitcoin.it/wiki/Protocol_specification#Variable_length_integer
    if i < 0xfd:
        val = i.to_bytes(1, 'little', signed=False)
    elif i <= 0xffff:
        val = b'\xfd' + i.to_bytes(2, 'little', signed=False)
    elif i <= 0xffffffff:
        val = b'\xfe' + i.to_bytes(4, 'little', signed=False)
    else:
        val = b'\xff' + i.to_bytes(8, 'little', signed=False)

    return val


def tx_make_generation(coinbase_data, address, value, height, witness_commitment=None):
    # See https://en.bitcoin.it/wiki/Transaction

    coinbase_script = encode_coinbase_height(height) + coinbase_data
    pubkey_script = address_to_script(address)

    outputs = [
        b"".join((
            # output[0] value (little endian)
            value.to_bytes(8, 'little', signed=True),
            # output[0] script len
            var_int(len(pubkey_script)),
            # output[0] script
            pubkey_script
        )),
    ]
    if witness_commitment:
        outputs.append(
            b''.join((
                # value (0 satoshis)
                b'\x00\x00\x00\x00\x00\x00\x00\x00',
                # script len
                var_int(len(witness_commitment)),
                # script
                witness_commitment
            ))
        )
        tx = b"".join((
            # Version
            b"\x01\x00\x00\x00"
            # Marker
            b"\x00"
            # Flag
            b"\x01"
            # in-count
            b"\x01"
            # input[0] (coinbase) prev hash
            b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
            b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
            # input[0] (coinbase) prev seqnum
            b"\xff\xff\xff\xff",
            # input[0] (coinbase) script len
            var_int(len(coinbase_script)),
            # input[0] (coinbase) script
            coinbase_script,
            # input[0] (coinbase) seqnum
            b"\xff\xff\xff\xff",
            # outputs count
            var_int(len(outputs)),
            # outputs
            b''.join(outputs),
            # input[0] (coinbase) witness stack count
            var_int(1),
            # input[0] (coinbase) witness stack[0] (witness reserved value) length
            var_int(32),
            # input[0] (coinbase) witness stack[0] (witness reserved value)
            b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
            b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
            # lock-time
            b"\x00\x00\x00\x00"
        ))
        consensus_serialized_tx = b"".join((
            # version
            b"\x01\x00\x00\x00"
            # inputs count
            b"\x01"
            # input[0] prev hash
            b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
            b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
            # input[0] prev seqnum
            b"\xff\xff\xff\xff",
            # input[0] script len
            var_int(len(coinbase_script)),
            # input[0] script
            coinbase_script,
            # input[0] seqnum
            b"\xff\xff\xff\xff",
            # outputs count
            var_int(len(outputs)),
            # outputs
            b''.join(outputs),
            # lock-time
            b"\x00\x00\x00\x00"
        ))
        full_hash = sha256(sha256(tx).digest()).digest()
        consensus_hash = sha256(sha256(consensus_serialized_tx).digest()).digest()
    else:
        tx = b"".join((
            # version
            b"\x01\x00\x00\x00",
            # inputs count
            b"\x01",
            # input[0] (coinbase) prev hash
            bytes((0,) * 32),
            # input[0] (coinbase) prev seqnum
            b"\xff\xff\xff\xff",
            # input[0] (coinbase)  script len
            var_int(len(coinbase_script)),
            # input[0] (coinbase) script
            coinbase_script,
            # input[0] (coinbase) seqnum
            b"\xff\xff\xff\xff",
            # outputs count
            var_int(len(outputs)),
            # outputs
            b''.join(outputs),
            # lock-time
            b"\x00\x00\x00\x00"
        ))
        full_hash = consensus_hash = sha256(sha256(tx).digest()).digest()

    return tx, consensus_hash, full_hash


def tx_merkle_root(tx_hashes):
    """Compute the Merkle Root of a sequence of tx hashes
    Returns a SHA256 double hash digest in internal byte order

    :param tx_hashes: sequence of transaction hash digests in internal byte order

    """
    tx_hashes = list(tx_hashes)

    # Iteratively compute the merkle root hash
    while len(tx_hashes) > 1:
        # Duplicate last hash if list has odd length
        if len(tx_hashes) % 2 != 0:
            tx_hashes.append(tx_hashes[-1])

        # Hash the concatenation of every pair of hashes
        pop_hash = tx_hashes.pop
        tx_hashes_new = [
            sha256(sha256(pop_hash(0) + pop_hash(0)).digest()).digest()
            for _ in range(len(tx_hashes) // 2)
        ]
        tx_hashes = tx_hashes_new

    return tx_hashes[0]