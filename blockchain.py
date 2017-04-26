# imports
import io
import urlfetch
import urllib
from random import random
import binascii
import json

# local imports
from pycoin.encoding import btc2satoshi, satoshi2btc, wif_to_secret_exponent, bitcoin_address_to_hash160_sec
from pycoin.serialize import b2h
from pycoin.services import blockchain_info
from pycoin.tx.UnsignedTx import UnsignedTxOut
from pycoin.tx import UnsignedTx, SecretExponentSolver, TxOut
from secrets import *
from pycoin.tx.script import tools

# constants
MIN_FEE = btc2satoshi(0.00001)  # 1000
TX_FEES = btc2satoshi(0.00038508)
OP_RETURN_MAX_DATA = 40
# POE_MARKER_BYTES = 'DOCPROOF'
# BASE_BLOCKCHAIN_URL = 'https://blockchain.info'
PUSH_URL_1 = 'http://blockchain.info/pushtx' # blockchain has buggy push
PUSH_URL_2 = 'https://insight.bitpay.com/api/tx/send'
PUSH_URL_3 = 'http://btc.blockr.io/api/v1/tx/push'


def construct_data_tx(data, _from, _to):
    # inputs
    coins_from = blockchain_info.coin_sources_for_address(_from)
    if len(coins_from) < 1:
        return "No free outputs to spend"
    max_coin_value, _, max_idx, max_h, max_script = max((tx_out.coin_value, random(), idx, h, tx_out.script)
                                                        for h, idx, tx_out in coins_from)
    unsigned_txs_out = [UnsignedTxOut(max_h, max_idx, max_coin_value, max_script)]

    # # outputs
    # if max_coin_value > TX_FEES:
    #     return 'max output %d greater than recommended value, too big.' % max_coin_value
    if max_coin_value < MIN_FEE:
        return 'max output %d smaller than threshold, too small.' % max_coin_value
    data_text = ' OP_RETURN %s' % data.encode('hex')
    data_bin = tools.compile(data_text)
    new_txs_out = [TxOut(0, data_bin)]

    # script_text = "OP_DUP OP_HASH160 %s OP_EQUALVERIFY OP_CHECKSIG" %(b2h(bitcoin_address_to_hash160_sec(_to)))
    # script_bin = tools.compile(script_text)
    # if max_coin_value >= TX_FEES:
    #     coin_value = max_coin_value-TX_FEES
    # else:
    #     coin_value = max_coin_value - MIN_FEE
    # new_txs_out.append(TxOut(coin_value, script_bin))
    # print "sending %d satoshis to %s" %((coin_value), _to)

    version = 1
    lock_time = 0
    unsigned_tx = UnsignedTx(version, unsigned_txs_out, new_txs_out, lock_time)
    return unsigned_tx


def tx2hex(tx):
    s = io.BytesIO()
    tx.stream(s)
    tx_bytes = s.getvalue()
    tx_hex = binascii.hexlify(tx_bytes).decode('utf8')
    return tx_hex


def pushtxn(raw_tx):
    '''Insight send raw tx API'''
    data = urllib.urlencode(dict(tx=raw_tx)).encode("utf8")
    response = urlfetch.post(PUSH_URL_1, data=data)
    if response.status_code == 200:
        j = json.loads(response.content)
        txid = j.get('txid')
        return txid, raw_tx
    else:
        msg = 'Error accessing API:' + str(response.status) + " " + str(response.content)
        # logging.error(msg)
        return None, msg


def publish_data(data):
    # data = POE_MARKER_BYTES + data
    if len(data) > OP_RETURN_MAX_DATA:
        return None, 'data too long for OP_RETURN: %s' % (data.encode('hex'))

    secret_exponent = wif_to_secret_exponent(PRIVATE_KEY_1)
    _from = ADDRESS_1
    _to = ADDRESS_2
    unsigned_tx = construct_data_tx(data, _from, _to)
    if type(unsigned_tx) == str:  # error
        return (None, unsigned_tx)
    signed_tx = unsigned_tx.sign(SecretExponentSolver([secret_exponent]))
    raw_tx = tx2hex(signed_tx)
    txid, message = pushtxn(raw_tx)
    return txid, message, raw_tx

