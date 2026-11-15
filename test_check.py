"""Network metadata, automatic checks and the shared distribution folder."""
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import Mock, patch
import zipfile

import tool


class NetworkTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.game = Path(self.tmp.name) / "netgame"
        self.game.mkdir()
        self.write_game({})

    def write_game(self, extra, source='import alav as g\ng.host("netgame")\n'):
        (self.game / "main.py").write_text(source, encoding="utf-8")
        (self.game / "game.json").write_text(json.dumps(dict(title="Network Game", version="1.0.0", **extra)))

    def test_network_calls_require_boolean_true_metadata(self):
        for module in ("g", "alav", "r36t"):
            for call in ("host", "join"):
                for value in (None, False, "true", 1):
                    with self.subTest(module=module, call=call, value=value):
                        self.write_game({"net": value}, '%s.%s("netgame")\n' % (module, call))
                        self.assertIn('add "net": true to game.json', tool.static_problems(str(self.game))[0])
        self.write_game({"net": True})
        self.assertEqual(tool.static_problems(str(self.game)), [])

    def test_string_join_and_comments_are_not_network_calls(self):
        self.write_game({}, '# g.host("netgame")\ntext = ",".join(["one", "two"])\n')
        self.assertEqual(tool.static_problems(str(self.game)), [])

    def test_new_preserves_network_declaration_from_example(self):
        for example in ("netduel", "minimal"):
            with self.subTest(example=example), patch.object(tool, "WORK", self.tmp.name), \
                    patch("sys.stdout", new_callable=io.StringIO):
                tool.cmd_new([example, "--from", example])
                info = tool.meta(str(Path(self.tmp.name) / "games" / example))
                self.assertEqual(info.get("net"), True if example == "netduel" else None)

    def test_network_metadata_or_flag_runs_host_join_and_lobby_checks(self):
        for metadata, flags in (({"net": True}, []), ({"net": True}, ["--net"]), ({}, ["--net"]), ({}, [])):
            with self.subTest(metadata=metadata, flags=flags):
                self.write_game(metadata, "pass\n")
                with patch.object(tool, "headless", return_value=("shots", Mock())) as headless, \
                        patch.object(tool, "judge", return_value=([], None)) as judge, \
                        patch.object(tool, "lobby_problems", return_value=[]) as lobby, \
                        patch.object(tool.time, "sleep"), patch("sys.stdout", new_callable=io.StringIO):
                    self.assertEqual(tool.cmd_check([str(self.game)] + flags), 0)
                network = bool(metadata or flags)
                self.assertEqual(headless.call_count, 3 if network else 1)
                self.assertEqual(lobby.call_count, int(network))
                self.assertTrue(all(c.args[3] == network for c in judge.call_args_list))

    def test_missing_network_metadata_fails_before_starting_game(self):
        with patch.object(tool, "headless") as headless, patch("sys.stdout", new_callable=io.StringIO) as out:
            self.assertEqual(tool.cmd_check([str(self.game), "--net"]), 1)
        headless.assert_not_called()
        self.assertIn('add "net": true', out.getvalue())

    def test_metadata_and_legacy_shim_survive_shared_stage_zip_and_tar(self):
        self.write_game({"net": True})
        with patch.object(tool, "DIST", str(Path(self.tmp.name) / "dist")):
            archive, folder, _ = tool.make_zip(str(self.game))
        expected = (self.game / "game.json").read_bytes()
        self.assertEqual((Path(folder) / "game.json").read_bytes(), expected)
        self.assertEqual((Path(folder) / "r36t.py").read_bytes(), (Path(tool.KIT) / "r36t.py").read_bytes())
        with zipfile.ZipFile(archive) as z:
            self.assertEqual(z.read("game.json"), expected)
        with tarfile.open(fileobj=io.BytesIO(tool.tar_bytes(folder)), mode="r:gz") as tar:
            self.assertEqual(tar.extractfile("./game.json").read(), expected)


if __name__ == "__main__":
    unittest.main()
