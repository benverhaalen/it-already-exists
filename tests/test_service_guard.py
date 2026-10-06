"""Owned request fixtures; policy enforcement is separate from device egress."""
import base64
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / 'skills/reference-driven-development/scripts'
sys.path.insert(0, str(SCRIPTS))
import service_guard as guard


def request(method='GET', target='/catalog', body=b'', host='catalog.example.org', headers=None):
    return ('https', host, 443, method, target, headers or [], body)


def policy(rules=(), hosts=()):
    return guard.Policy({'schema_version': 1, 'protected_hosts': list(hosts), 'rules': list(rules)})


def forward(req):
    return {'fingerprint': guard.fingerprint(*req), 'action': 'forward', 'read_only_review': 'owned-review.json'}


class GuardTests(unittest.TestCase):
    def test_no_rule_no_network_even_for_get(self):
        for req in [request(), request(target='/buy'), request(method='POST', body=b'{}')]:
            self.assertEqual(policy().decide(*req, live=True)['action'], 'deny')

    def test_forward_needs_opt_in_and_exact_review(self):
        req = request(headers=[('authorization', 'owned-token')])
        p = policy([forward(req)])
        self.assertEqual(p.decide(*req)['reason'], 'live-disabled')
        self.assertEqual(p.decide(*req, live=True)['action'], 'forward')
        for altered in [request(target='/buy', headers=req[5]), request(host='other.example.org', headers=req[5]),
                        request(headers=[('authorization', 'different-token')]), request(body=b'buy', headers=req[5])]:
            self.assertEqual(p.decide(*altered, live=True)['action'], 'deny')

    def test_graphql_mutation_cannot_reuse_query_rule(self):
        req = request(method='POST', target='/graphql', body=b'{"query":"{catalog{id}}"}')
        p = policy([forward(req)])
        self.assertEqual(p.decide(*req, live=True)['action'], 'forward')
        mutation = request(method='POST', target='/graphql', body=b'{"query":"mutation{buyPass{id}}"}')
        self.assertEqual(p.decide(*mutation, live=True)['action'], 'deny')

    def test_protected_hosts_override_live_rules(self):
        for host in ['pay.example.org', 'api.pay.example.org']:
            req = request(host=host)
            self.assertEqual(policy([forward(req)], ['pay.example.org']).decide(*req, live=True)['reason'], 'protected-host')

    def test_checkout_fixture_never_forwards_even_live_enabled(self):
        req = request(method='POST', target='/buy', body=b'{"savedCard":"owned"}')
        rule = {'fingerprint': guard.fingerprint(*req), 'action': 'fixture', 'status': 200,
                'content_type': 'application/json', 'body_base64': base64.b64encode(b'{"testPass":true}').decode()}
        p = policy([rule], ['catalog.example.org'])
        for live in (False, True):
            d = p.decide(*req, live=live)
            self.assertEqual(d['action'], 'fixture')
            self.assertEqual(d['body'], b'{"testPass":true}')

    def test_no_redirect_or_upgrade_tunnel(self):
        req = request(headers=[('upgrade', 'websocket')])
        self.assertEqual(policy().decide(*req, live=True)['reason'], 'invalid-request')
        req = request()
        rule = {'fingerprint': guard.fingerprint(*req), 'action': 'fixture', 'status': 302,
                'content_type': 'text/plain', 'body_base64': ''}
        with self.assertRaisesRegex(ValueError, 'redirect'):
            policy([rule])

    def test_changed_query_duplicate_header_and_oversize_rejected(self):
        req = request(headers=[('x-mode', 'view')])
        p = policy([forward(req)])
        for altered in [request(target='/catalog?buy=1', headers=req[5]), request(headers=req[5] + [('x-mode', 'buy')]),
                        request(body=b'a' * (guard.MAX_BODY + 1))]:
            self.assertEqual(p.decide(*altered, live=True)['action'], 'deny')

    def test_policy_rejects_ambiguous_or_unreviewed_rules(self):
        r = forward(request())
        with self.assertRaises(ValueError):
            policy([r, r])
        with self.assertRaises(ValueError):
            policy([dict(r, read_only_review='')])
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'policy.json'
            path.write_text('{"schema_version":1,"schema_version":1,"protected_hosts":[],"rules":[]}')
            with self.assertRaisesRegex(ValueError, 'duplicate JSON'):
                guard.Policy.load(path)

    def test_hash_record_does_not_retain_auth_body_or_url(self):
        req = request(headers=[('authorization', 'private-owned-token')], body=b'private-owned-card')
        r = forward(req)
        serialized = json.dumps(r)
        self.assertNotIn('private-owned', serialized)
        self.assertNotIn('/catalog', serialized)


class AdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            from mitmproxy import http
        except ImportError:
            raise unittest.SkipTest('optional pinned mitmproxy dependency not installed')
        cls.http = http
        spec = importlib.util.spec_from_file_location('service_guard_mitm', SCRIPTS / 'service_guard_mitm.py')
        cls.adapter = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.adapter)

    def test_real_http_flow_local_checkout_and_unknown_denial(self):
        from mitmproxy.test import tflow
        self.adapter.ctx.options = SimpleNamespace(rdd_live=True)
        addon = self.adapter.ServiceGuard()
        flow = tflow.tflow()
        flow.request = self.http.Request.make('POST', 'https://catalog.example.org/buy', b'owned-card-token')
        r = flow.request
        req = (r.scheme, r.host, r.port, r.method, r.path, list(r.headers.items(multi=True)), r.raw_content)
        rule = {'fingerprint': guard.fingerprint(*req), 'action': 'fixture', 'status': 200,
                'content_type': 'application/json', 'body_base64': base64.b64encode(b'{"local":true}').decode()}
        addon.policy = policy([rule])
        addon.request(flow)
        self.assertEqual(flow.response.status_code, 200)
        self.assertEqual(flow.response.content, b'{"local":true}')
        flow.response = None
        flow.request.content = b'other-card-token'
        addon.request(flow)
        self.assertEqual(flow.response.status_code, 403)

    def test_failed_policy_reload_invalidates_existing_permission(self):
        addon = self.adapter.ServiceGuard()
        addon.policy = policy([forward(request())])
        self.adapter.ctx.options = SimpleNamespace(rdd_policy='/nonexistent/owned-policy.json', rdd_live=True)
        addon.configure({'rdd_policy'})
        self.assertIsNone(addon.policy)


if __name__ == '__main__':
    unittest.main()
