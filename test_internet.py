"""Integration with the real, read-only PlayRelay; no replacement relay implementation."""
import asyncio
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import socket
import ssl
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent
RELAY = Path('D:/CODE/Mastak/alav-online-mastak-net/Services/PlayRelay/relay.py')


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@unittest.skipUnless(RELAY.is_file(), 'SKIP: real PlayRelay module missing: ' + str(RELAY))
class InternetTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # Load the actual kit, including its SDL bindings, without starting a game loop.
        self.env = patch.dict(os.environ, ALAV_SDL_DIR=str(ROOT / '.sdl'), ALAV_NET='internet',
                              ALAV_JOIN='', ALAV_ROOM='ABCDEFGH', ALAV_PRIVATE='1')
        self.env.start()
        self.addCleanup(self.env.stop)
        self.g = load_module('internet_test_alav', ROOT / 'kit/alav.py')
        registry = load_module('registry', RELAY.with_name('registry.py'))
        with patch.dict(sys.modules, registry=registry):
            relay_module = load_module('real_play_relay', RELAY)
        self.relay = relay_module.Relay(ping=.1)
        await self.relay.start('127.0.0.1', 0)
        port = self.relay.server.sockets[0].getsockname()[1]
        os.environ['ALAV_RELAY'] = '127.0.0.1:%d' % port
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.game = Path(self.tmp.name) / 'relay-test'
        self.game.mkdir()
        (self.game / 'game.json').write_text(json.dumps({'title': 'Relay Test'}))
        self.g.GAME_DIR = str(self.game)
        # Isolate LAN discovery as well as relay TCP ports from other running games.
        with socket.socket() as probe:
            probe.bind(('127.0.0.1', 0))
            self.g.NET_PORT = probe.getsockname()[1]
        self.nets = []
        self.messages = {}
        self.max_frame = 0

    async def asyncTearDown(self):
        for net in self.nets:
            net.close()
        await self.relay.close()

    def host(self, maximum=4):
        net = self.g.host('relay-test', max_players=maximum)
        self.nets.append(net)
        self.messages[net] = []
        return net

    def join(self):
        os.environ['ALAV_JOIN'] = 'relay:ABCDEFGH'
        net = self.g.Net('relay-test', False)
        self.nets.append(net)
        self.messages[net] = []
        return net

    async def until(self, condition, timeout=3):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            for net in self.nets:
                if not net._closed:
                    started = time.monotonic()
                    self.messages[net].extend(net.recv())
                    self.max_frame = max(self.max_frame, time.monotonic() - started)
            if condition():
                return
            await asyncio.sleep(.005)
        self.fail('relay condition timed out')

    async def test_messages_ids_private_room_heartbeat_and_host_close(self):
        host = self.host()
        await self.until(lambda: host._session is not None)
        session = self.relay.sessions['ABCDEFGH']
        self.assertEqual((session['slug'], session['name'], session['max'], session['private']),
                         ('relay-test', 'Relay Test', 4, True))
        first, second = self.join(), self.join()
        await self.until(lambda: len(host.peers) == 2 and first.connected and second.connected)
        self.assertEqual(set(host.peers), {1, 2})
        self.assertEqual(set(first.peers), {0})
        self.assertEqual(set(second.peers), {0})
        first.send({'guest': 1})
        second.send({'guest': 2})
        await self.until(lambda: len(self.messages[host]) == 2)
        self.assertEqual({pid for pid, _ in self.messages[host]}, {1, 2})
        for pid, message in self.messages[host]:
            host.send({'id': pid, 'echo': message}, to=pid)
        await self.until(lambda: bool(self.messages[first]) and bool(self.messages[second]))
        self.assertEqual({self.messages[n][0][1]['id'] for n in (first, second)}, {1, 2})
        # Several heartbeat periods: real relay drops hosts that do not answer PING.
        start = time.monotonic()
        await self.until(lambda: time.monotonic() - start > .5)
        self.assertIn('ABCDEFGH', self.relay.sessions)
        self.assertEqual(self.g.NET, 'internet')
        host.close()
        await self.until(lambda: not first.connected and not second.connected)
        self.assertLess(self.max_frame, .3)

    async def test_max_two_refuses_third_player(self):
        host = self.host(2)
        await self.until(lambda: host._session is not None)
        first = self.join()
        await self.until(lambda: first.connected)
        extra = self.join()
        await self.until(lambda: extra._retry > 0 and extra._relay is None)
        self.assertFalse(extra.connected)
        self.assertEqual(len(host.peers), 1)
        retry = extra._retry
        for _ in range(10):
            extra.recv()
        self.assertEqual(extra._retry, retry)

    async def test_unreachable_falls_back_quickly_and_answers_lan(self):
        with socket.socket() as probe:
            probe.bind(('127.0.0.1', 0))
            port = probe.getsockname()[1]
        os.environ['ALAV_RELAY'] = '127.0.0.1:%d' % port
        errors = io.StringIO()
        started = time.monotonic()
        with contextlib.redirect_stderr(errors):
            host = self.host()
            await self.until(lambda: not host._internet)
        self.assertLess(time.monotonic() - started, .5)
        self.assertEqual(self.g.NET, 'lan')
        self.assertEqual(len([line for line in errors.getvalue().splitlines() if line.startswith('ALAV:')]), 1)
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
            probe.setblocking(False)
            probe.sendto(b'ALAV?*', ('127.0.0.1', self.g.NET_PORT))
            await self.until(lambda: host._readable(probe))
            self.assertTrue(probe.recv(256).startswith(b'ALAV!*'))
        guest = self.g.Net('relay-test', False, ip='127.0.0.1')
        os.environ['ALAV_JOIN'] = ''
        self.nets.append(guest)
        self.messages[guest] = []
        await self.until(lambda: host.connected and guest.connected)

    async def test_address_metadata_and_lobby_launch_validation(self):
        import tool
        for address in ('https://alav.online/wrong', '127.0.0.1:0', 'bad host:123',
                        'http://alav.online/play-relay', 'https://alav.online:65536/play-relay'):
            os.environ['ALAV_RELAY'] = address
            with self.subTest(address=address), self.assertRaises(ValueError):
                self.g._relay_address()
        os.environ['ALAV_JOIN'] = 'relay:ABCDEFGH'
        launched = load_module('lobby_launched_alav', ROOT / 'kit/alav.py')
        self.assertEqual((launched.ROLE, launched.NET, launched._JOIN),
                         ('join', 'internet', 'relay:ABCDEFGH'))
        for value in ('true', 1, None):
            (self.game / 'game.json').write_text(json.dumps(dict(title='Test', version='1.0.0', net=True, internet=value)))
            with self.subTest(value=value), self.assertRaises(SystemExit):
                tool.meta(str(self.game))
        (self.game / 'game.json').write_text(json.dumps(dict(title='Test', version='1.0.0', net=True, internet=True)))
        self.assertTrue(tool.meta(str(self.game))['internet'])

    @unittest.skipUnless(shutil.which('openssl'), 'TLS fixture needs openssl to generate a local certificate')
    async def test_tls_http_upgrade_with_real_relay(self):
        cert, key = Path(self.tmp.name) / 'cert.pem', Path(self.tmp.name) / 'key.pem'
        subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes',
                        '-keyout', str(key), '-out', str(cert), '-days', '1',
                        '-subj', '/CN=127.0.0.1', '-addext', 'subjectAltName=IP:127.0.0.1'],
                       check=True, capture_output=True)
        server_tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        server_tls.load_cert_chain(cert, key)
        self.g._relay_tls = ssl.create_default_context(cafile=str(cert))
        self.relay.server.close()
        await self.relay.server.wait_closed()
        self.relay.server = await asyncio.start_server(self.relay.handle, '127.0.0.1', 0, ssl=server_tls)
        port = self.relay.server.sockets[0].getsockname()[1]
        os.environ['ALAV_RELAY'] = 'https://127.0.0.1:%d/play-relay' % port
        host = self.host()
        await self.until(lambda: host._session is not None)
        guest = self.join()
        await self.until(lambda: host.connected and guest.connected)
        host.send({'tls': True})
        guest.send({'upgrade': True})
        await self.until(lambda: bool(self.messages[host]) and bool(self.messages[guest]))
        self.assertEqual(self.messages[host], [(1, {'upgrade': True})])
        self.assertEqual(self.messages[guest], [(0, {'tls': True})])
        self.assertLess(self.max_frame, .3)

    async def test_bad_control_lines_and_oversize_do_not_crash(self):
        for payload in (b'CONN {"pair": []}\n', b'\xff\n', b'PING []\n',
                        b'CONN {oops}\n', b'x' * 513 + b'\n'):
            with self.subTest(payload=payload[:30]):
                host = self.host()
                await self.until(lambda: host._session is not None)
                self.relay.sessions['ABCDEFGH']['writer'].write(payload)
                with contextlib.redirect_stderr(io.StringIO()):
                    await self.until(lambda: not host._internet)
                self.assertFalse(host.connected)
                host.close()
                await self.until(lambda: 'ABCDEFGH' not in self.relay.sessions)

    async def test_game_stream_validation_and_queue_limit(self):
        host = self.host()
        await self.until(lambda: host._session is not None)
        guest = self.join()
        await self.until(lambda: host.connected and guest.connected)
        guest.peers[0][2] += b'not json\n' + b'[' * 100000 + b'0' + b']' * 100000 + b'\n{"ok":true}\n'
        await self.until(lambda: bool(self.messages[host]))
        self.assertEqual(self.messages[host], [(1, {'ok': True})])
        guest.peers[0][2] += b'x' * 270000
        guest.recv()
        self.assertFalse(guest.connected)


if __name__ == '__main__':
    if not RELAY.is_file():
        print('SKIP: real PlayRelay module missing: ' + str(RELAY))
    unittest.main(verbosity=2)
