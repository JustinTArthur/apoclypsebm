import http.client
import socket
from base64 import b64encode
from binascii import hexlify, unhexlify
from json import dumps, loads
from struct import pack
from threading import Event, Thread
from time import monotonic, sleep
from urllib.parse import urlsplit

import socks

from apoclypsebm.bitcoin import tx_make_generation, tx_merkle_root, var_int
from apoclypsebm.log import say_exception, say_line
from apoclypsebm.util import chunks
from apoclypsebm.work_sources.base import Source

gbt_count = 0


class NotAuthorized(Exception):
    pass


class RPCError(Exception):
    pass


class GetblocktemplateSource(Source):
    def __init__(self, switch):
        super().__init__(switch)

        self.connection = self.lp_connection = None
        self.long_poll_timeout = 3600
        self.max_redirects = 3

        self.headers = {'User-Agent': self.switch.user_agent,
                        'Authorization': 'Basic ' + b64encode(
                            b'%b:%b' % (self.server().user_bytes, self.server().pwd_bytes)).decode('ascii'),
                        'X-Mining-Extensions': 'hostlist midstate rollntime'}
        self.long_poll_url = ''

        self.long_poll_active = False
        self.long_poll_last_host = None

        self.authorization_failed = False

    def loop(self):
        if self.authorization_failed:
            return
        super().loop()
        long_poll_id_available = Event()
        thread = Thread(
            target=self.long_poll_thread,
            args=(long_poll_id_available,),
            daemon=True
        )
        thread.start()

        while True:
            if self.should_stop:
                return

            if self.check_failback():
                return True

            try:
                with self.switch.lock:
                    miner = self.switch.updatable_miner()
                    while miner:
                        template = self.getblocktemplate()
                        if template:
                            work = self.work_from_template(template)
                            self.queue_work(work, miner)
                            miner = self.switch.updatable_miner()

                            if 'longpollid' in template:
                                self.long_poll_id = template['longpollid']
                                self.long_poll_url = template.get('longpolluri', '')
                                long_poll_id_available.set()
                            self.switch.update_time = ('time' in template.get('mutable', ()))


                self.process_result_queue()
                sleep(1)
            except Exception:
                say_exception("Unexpected error:")
                break

    def ensure_connected(self, connection, proto, host):
        if connection != None and connection.sock != None:
            return connection, False

        if proto == 'https':
            connector = http.client.HTTPSConnection
        else:
            connector = http.client.HTTPConnection

        if not self.options.proxy:
            return connector(host), True

        host, port = host.split(':')
        connection = connector(host)
        connection.sock = socks.socksocket()
        p = self.options.proxy
        connection.sock.setproxy(p.type, p.host, p.port, True, p.user, p.pwd)
        try:
            connection.sock.connect((host, int(port)))
        except socks.Socks5AuthError:
            say_exception('Proxy error:')
            self.stop()
        return connection, True

    def request(self, connection, url, headers, data=None, timeout=0):
        result = response = None
        try:
            if data:
                connection.request('POST', url, data, headers)
            else:
                connection.request('GET', url, headers=headers)
            response = self.timeout_response(connection, timeout)
            if not response:
                return None
            if response.status == http.client.UNAUTHORIZED:
                say_line('Wrong username or password for %s',
                         self.server().name)
                self.authorization_failed = True
                raise NotAuthorized()
            r = self.max_redirects
            while response.status == http.client.TEMPORARY_REDIRECT:
                response.read()
                url = response.getheader('Location', '')
                if r == 0 or url == '': raise http.client.HTTPException(
                    'Too much or bad redirects')
                connection.request('GET', url, headers=headers)
                response = self.timeout_response(connection, timeout)
                r -= 1
            self.stratum_header = response.getheader('x-stratum', '')
            result = loads(response.read())
            if result['error']:
                say_line('server error: %s', result['error']['message'])
                raise RPCError(result['error']['message'])
            return (connection, result)
        finally:
            if not result or not response or (
                    response.version == 10 and response.getheader('connection',
                                                                  '') != 'keep-alive') or response.getheader(
                    'connection', '') == 'close':
                connection.close()
                connection = None

    def timeout_response(self, connection, timeout):
        if timeout:
            start = monotonic()
            connection.sock.settimeout(timeout)
            response = None
            while not response:
                if self.should_stop or monotonic() - start > timeout:
                    return
                try:
                    response = connection.getresponse()
                except socket.timeout:
                    pass
            connection.sock.settimeout(20)
            return response
        else:
            return connection.getresponse()

    def getblocktemplate(self, long_poll_id=None, timeout=None):
        param = {
            'capabilities': ('longpoll', 'coinbasetxn',
                             'coinbasevalue', 'workid'),
            'rules': ('segwit',)
        }

        try:
            if long_poll_id:
                param['longpollid'] = long_poll_id
                url = self.long_poll_url
                parsedUrl = urlsplit(url)
                proto = parsedUrl.scheme or self.server().proto
                if parsedUrl.netloc != '':
                    host = parsedUrl.netloc
                    url = url[url.find(host) + len(host):]
                    if url == '':
                        url = '/'
                else:
                    host = self.server().host

                if host != self.long_poll_last_host:
                    self.close_lp_connection()
                self.lp_connection, changed = self.ensure_connected(
                    self.lp_connection, proto, host)
                connection = self.lp_connection
                if changed:
                    say_line(f'LP connected to {host}')
                    self.long_poll_last_host = host

            else:
                url = '/'
                self.connection, changed = \
                    self.ensure_connected(self.connection, self.server().proto,
                                          self.server().host)
                connection = self.connection
                if changed:
                    say_line(f'Connected to {self.server().host}')

            postdata = {
                'method': 'getblocktemplate',
                'id': 'json',
                'params': (param,)
            }
            connection, result = self.request(connection, url, self.headers,
                                              dumps(postdata), timeout=timeout or 0)
            self.switch.connection_ok()

            return result['result']
        except ConnectionResetError:
            # Connection resets are normal if the server hasn't heard from us
            # in a while.
            if long_poll_id:
                self.close_lp_connection()
            else:
                self.close_connection()
        except (IOError, http.client.HTTPException, ValueError, socks.ProxyError,
                NotAuthorized, RPCError):
            self.stop()
        except Exception:
            say_exception()

    def submitblock(self, block_data, work_id=None):
        try:
            self.connection = \
                self.ensure_connected(self.connection, self.server().proto,
                                      self.server().host)[0]
            if work_id:
                params = (block_data, {'workid': work_id})
            else:
                params = (block_data,)

            postdata = {
                'method': 'submitblock',
                'id': 'json',
                'params': params
            }

            (self.connection, result) = self.request(self.connection, '/',
                                                     self.headers,
                                                     dumps(postdata))

            self.switch.connection_ok()

            return result['result']
        except (IOError, http.client.HTTPException, ValueError, socks.ProxyError,
                NotAuthorized, RPCError):
            say_exception()
            self.stop()
        except Exception:
            say_exception()

    def proposeblock(self, block_data, work_id=None):
        try:
            self.connection = \
                self.ensure_connected(self.connection, self.server().proto,
                                      self.server().host)[0]
            param = {
                'mode': 'proposal',
                'data': block_data
            }
            if work_id:
                param['workid'] = work_id

            postdata = {
                'method': 'getblocktemplate',
                'id': 'json',
                'params': (param,)
            }
            with open('last_submission.txt', 'w') as submission_file:
                submission_file.write(dumps(postdata))

            (self.connection, result) = self.request(self.connection, '/',
                                                     self.headers,
                                                     dumps(postdata))

            self.switch.connection_ok()

            reject_reason = result['result']
            say_line('proposal response: %s', reject_reason)
            return result['result']

        except (IOError, http.client.HTTPException, ValueError, socks.ProxyError,
                NotAuthorized, RPCError):
            say_exception()
            self.stop()
        except Exception:
            say_exception()

    def submittable_block_header(self, result, nonce):
        header = bytearray()
        # Un-reverse the SHA-2 message words.
        for word in chunks(result.header, 4):
            header += word[::-1]
        header += pack('>3I',
                       int(result.time), int(result.difficulty), int(nonce))
        return header

    def block_hex_from_result(self, result, nonce):
        header = self.submittable_block_header(result, nonce)

        txes = result.transactions
        block_hex = ''.join(
            [header.hex(), var_int(len(txes)).hex()] +
            [tx['data'] for tx in txes]
        )
        return block_hex

    def send_internal(self, result, nonce):
        data = self.block_hex_from_result(result, nonce)

        # If want to debug the blocks that would otherwise be submitted:
        #reject_reason = self.proposeblock(data, result.job_id)

        reject_reason = self.submitblock(data, result.job_id)

        if reject_reason is None:
            self.switch.report(result.miner, nonce, reject_reason is None)
            return True

    def long_poll_thread(self, long_poll_id_available):
        long_poll_id_available.wait()
        while True:
            if self.should_stop or self.authorization_failed:
                return

            try:
                self.long_poll_active = True
                template = self.getblocktemplate(long_poll_id=self.long_poll_id,
                                                 timeout=self.long_poll_timeout)
                self.long_poll_active = False
                if template:
                    work = self.work_from_template(template)
                    self.queue_work(work)
                    if self.options.verbose:
                        say_line('long poll: new block %s%s',
                                 (work['data'][56:64].decode('ascii'),
                                  work['data'][48:56].decode('ascii')))
                    if 'longpollid' in template:
                        self.long_poll_id = template['longpollid']
            except (IOError, http.client.HTTPException, ValueError,
                    socks.ProxyError, NotAuthorized, RPCError):
                say_exception('long poll IO error')
                self.close_lp_connection()
                sleep(.5)
            except Exception:
                say_exception()

    def stop(self):
        self.should_stop = True
        self.close_lp_connection()
        self.close_connection()

    def close_connection(self):
        if self.connection:
            self.connection.close()
            self.connection = None

    def close_lp_connection(self):
        if self.lp_connection:
            self.lp_connection.close()
            self.lp_connection = None

    def workable_block_header(self, template):
        """Takes a block template and creates a block header from it that
        is pre-processed into the SHA-256 message format.
        """
        gen_tx, gen_tx_hash, _gen_tx_full_hash = self.generation_tx_for_template(template)
        tx_hashes = (
            [gen_tx_hash]
            + [unhexlify(tx['txid'])[::-1] for tx in
               template['transactions']]
        )
        merkle_root = tx_merkle_root(tx_hashes)
        merkle_root_words = bytearray()
        for word in chunks(merkle_root, 4):
            merkle_root_words += word[::-1]

        prev_block_hash_words = bytearray()
        for word in chunks(unhexlify(template['previousblockhash']), 4):
            # Prepend because template items are in RPC byte order.
            prev_block_hash_words[0:0] = word

        header_words = b''.join((
            # Version
            pack(">L", template['version']),
            # Previous Block Hash
            prev_block_hash_words,
            # Merkle Root Hash
            merkle_root_words,
            # Time
            pack(">L", template['curtime']),
            # Target Bits
            unhexlify(template['bits']),
            # Nonce
            pack(">L", 0)  # Will be replaced by nonce as iterated.
        ))
        return header_words, gen_tx

    def generation_tx_for_template(self, template):
        template_tx = template.get('coinbasetxn')
        # In segwit mode, we need another merkle root that has hashed witness
        # portions of txes:
        witness_commitment = unhexlify(template['default_witness_commitment'])
        # TODO: use the 'hash' attrs if this is missing
        coinbase_msg = self.options.coinbase_msg.encode('utf-8')
        if template_tx:
            if self.options.address:
                if 'coinbase' in template.get('mutable', ('coinbase',)):
                    return tx_make_generation(coinbase_msg, self.options.address,
                                              template['coinbasevalue'],
                                              template['height'],
                                              witness_commitment=witness_commitment)
                else:
                    say_line(
                        f'Warning: address {self.options.address} ignored, not allowed by work source.')
        else:
            if self.options.address:
                return tx_make_generation(coinbase_msg, self.options.address,
                                          template['coinbasevalue'],
                                          template['height'],
                                          witness_commitment=witness_commitment)
            else:
                raise Exception('Address not supplied by user and no coinbase tx supplied by work source.')

        return (
            unhexlify(template_tx['data']),
            unhexlify(template_tx['txid']),
            unhexlify(template_tx['hash']),
        )

    def work_from_template(self, template):
        if not template:
            return None
        workable_header, coinbase_tx = self.workable_block_header(template)
        work = {
            'data': hexlify(workable_header),
            'target': template['target'],
        }
        if 'workid' in template:
            work['job_id'] = template['workid']
        work['transactions'] = [{'data': coinbase_tx.hex()}] + template['transactions']
        return work

    def queue_work(self, work, miner=None):
        if work:
            if not 'target' in work:
                work['target'] = ('000000000000'
                                  '000000000000'
                                  '000000000000'
                                  '000000000000'
                                  '0000'
                                  'ffff00000000')

            self.switch.queue_work(self, block_header=work['data'],
                                   target=work['target'],
                                   job_id=work.get('job_id'),
                                   miner=miner, transactions=work['transactions'])

    def detect_stratum(self):
        template = self.getblocktemplate()
        if self.authorization_failed:
            return False

        if template:
            if self.stratum_header:
                host = self.stratum_header
                proto = host.find('://')
                if proto != -1:
                    host = self.stratum_header[proto + 3:]
                # this doesn't work in windows/python 2.6
                # host = urlparse.urlparse(self.stratum_header).netloc
                say_line('diverted to stratum on %s', host)
                return host
            else:
                say_line('using getblocktemplate JSON-RPC (no stratum header)')
                work = self.work_from_template(template)
                self.queue_work(work)
                return False

        say_line('no response to getblocktemplate, using as stratum')
        return self.server().host
