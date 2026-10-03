"""Dummy-only official transport routing and isolated modern run contracts."""

import hashlib
import json
import os
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import requests

from scripts import modern_synthetic_canary as m
from tests import test_modern_synthetic_canary as fixtures


class ModernSupportedRouteTests(unittest.TestCase):
    setUp = fixtures.ModernCanaryTests.setUp

    def live_fixture(self):
        now = datetime.now(timezone.utc)
        self.grant.update(
            started_at=now.isoformat(),
            valid_until=(now + timedelta(minutes=30)).isoformat(),
        )
        m.atomic(self.stage / "approval.json", self.grant)

    def test_new_run_is_fixed_and_old_packet_stays_immutable(self):
        self.assertEqual(m.NAMESPACE, "pices-modern-synthetic-20261003-code-02")
        old = Path(__file__).resolve().parents[1] / "docs/handoff/modern-synthetic-canary-20261003-code-01"
        self.assertEqual(
            m.sha((old / "INVENTORY.json").read_bytes()),
            "95d125ba6e47cb87cd89fcc981c8a179ee37127e0fe9ccab5711f9984b79787e",
        )
        self.assertNotEqual(m.PACKET, old)
        for item in json.loads((old / "INVENTORY.json").read_bytes()):
            raw = (old / item["path"]).read_bytes()
            self.assertEqual(len(raw), item["bytes"])
            self.assertEqual(hashlib.sha256(raw).hexdigest(), item["sha256"])
        self.assertEqual(m.LIMITS, {"create": 1, "doi": 1, "metadata": 1,
                                    "init": 1, "content": 1, "commit": 1, "get": 8})

    def test_prior_unknown_run_is_rejected_without_touching_its_files(self):
        old = Path(self.temp.name) / "pices-modern-synthetic-20261003-code-01"
        old.mkdir(mode=0o700)
        for name, data in {
            "state.json": {"counts": {"create": 1}, "failed": True, "pending": {"kind": "create"}},
            "approval.json": {"approved": True, "namespace": old.name},
        }.items():
            m.atomic(old / name, data)
        before = {path.name: path.read_bytes() for path in old.iterdir()}
        with patch("requests.sessions.Session.send") as send, self.assertRaises(m.Held):
            m.execute(old, fixtures.TOKEN)
        send.assert_not_called()
        self.assertEqual({path.name: path.read_bytes() for path in old.iterdir()}, before)

    def test_standard_request_merges_dummy_proxy_and_ca_without_leaking_them(self):
        self.live_fixture()
        observed = []

        def send(session, request, **options):
            self.assertTrue(session.trust_env)
            self.assertEqual(options["proxies"]["https"], "http://dummy-route.test:8080")
            self.assertEqual(options["verify"], "/dummy/approved-ca.pem")
            self.assertFalse(options["allow_redirects"])
            self.assertEqual(request.headers["Authorization"], "Bearer " + fixtures.TOKEN)
            observed.append(request.url)
            return fixtures.Response({"message": "failed fixture"}, 500)

        with (
            patch.dict(os.environ, {
                "https_proxy": "http://dummy-route.test:8080",
                "REQUESTS_CA_BUNDLE": "/dummy/approved-ca.pem",
            }, clear=True),
            patch("requests.sessions.get_netrc_auth", return_value=None),
            patch("requests.sessions.Session.send", send),
            self.assertRaises(m.Held),
        ):
            m.execute(self.stage, fixtures.TOKEN)
        self.assertEqual(observed, [m.ORIGIN + "/api/records"])
        state = m.load(self.stage / "state.json")
        self.assertEqual(state["counts"]["create"], 1)
        diagnostic = state["attempt_diagnostics"][0]
        self.assertTrue(diagnostic["send_call_started"])
        self.assertEqual(diagnostic["status"], 500)
        serialized = json.dumps(state["attempt_diagnostics"])
        for private in (fixtures.TOKEN, "dummy-route.test", "approved-ca.pem"):
            self.assertNotIn(private, serialized)

    def test_netrc_authorization_replacement_holds_before_send(self):
        self.live_fixture()
        with (
            patch("requests.sessions.get_netrc_auth", return_value=("dummy-other-user", "dummy-password")),
            patch("requests.sessions.Session.send") as send,
            self.assertRaises(m.Held),
        ):
            m.execute(self.stage, fixtures.TOKEN)
        send.assert_not_called()
        state = m.load(self.stage / "state.json")
        self.assertEqual(state["counts"]["create"], 1)
        self.assertTrue(state["failed"])
        diagnostic = state["attempt_diagnostics"][0]
        self.assertFalse(diagnostic["send_call_started"])
        self.assertFalse(diagnostic["adapter_entered"])
        self.assertEqual(diagnostic["failure"]["phase"], "request_prepared")

    def test_original_adapter_is_preserved_and_entry_is_observed(self):
        self.live_fixture()
        session = requests.Session()
        original_adapter = session.get_adapter(m.ORIGIN)
        calls = []

        def adapter_send(adapter, request, **options):
            self.assertIs(adapter, original_adapter)
            self.assertEqual(adapter.max_retries.total, 0)
            calls.append(request.url)
            response = requests.Response()
            response.status_code = 500
            response._content = b'{"message":"failed fixture"}'
            response._content_consumed = True
            response.headers["Content-Type"] = "application/json"
            return response

        def send(session, request, **options):
            options.pop("allow_redirects")
            return session.get_adapter(request.url).send(request, **options)

        with (
            patch.dict(os.environ, {}, clear=True),
            patch("requests.sessions.get_netrc_auth", return_value=None),
            patch.object(m.requests, "Session", return_value=session),
            patch("requests.sessions.Session.send", send),
            patch("requests.adapters.HTTPAdapter.send", adapter_send),
            self.assertRaises(m.Held),
        ):
            m.execute(self.stage, fixtures.TOKEN)
        self.assertEqual(calls, [m.ORIGIN + "/api/records"])
        diagnostic = m.load(self.stage / "state.json")["attempt_diagnostics"][0]
        self.assertTrue(diagnostic["adapter_entered"])
        self.assertTrue(diagnostic["response_seen"])
        self.assertEqual(diagnostic["status"], 500)

    def test_nonzero_adapter_retries_hold_without_replacing_adapter(self):
        self.live_fixture()
        session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(max_retries=1)
        session.mount("https://", adapter)
        with (
            patch("requests.sessions.get_netrc_auth", return_value=None),
            patch.object(m.requests, "Session", return_value=session),
            patch("requests.sessions.Session.send") as send,
            self.assertRaises(m.Held),
        ):
            m.execute(self.stage, fixtures.TOKEN)
        send.assert_not_called()
        self.assertIs(session.get_adapter(m.ORIGIN), adapter)
        state = m.load(self.stage / "state.json")
        self.assertEqual(state["counts"]["create"], 1)
        self.assertFalse(state["attempt_diagnostics"][0]["send_call_started"])


if __name__ == "__main__":
    unittest.main()
