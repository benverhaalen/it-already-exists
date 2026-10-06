#!/usr/bin/env python3
"""Seed synthetic users in an already-running Firebase Auth emulator.

This is a local fixture adapter, not a production auth client or APK router.
"""
import argparse
import json
import re
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, ProxyHandler, HTTPRedirectHandler


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class LocalAuth:
    def __init__(self, endpoint='http://127.0.0.1:9099'):
        parsed = urlsplit(endpoint)
        if (parsed.scheme != 'http' or parsed.hostname not in {'127.0.0.1', '::1'}
                or parsed.username or parsed.password or parsed.path not in {'', '/'}
                or parsed.query or parsed.fragment):
            raise ValueError('Use an explicit loopback HTTP emulator endpoint')
        self.endpoint = endpoint.rstrip('/')
        self.opener = build_opener(ProxyHandler({}), NoRedirect())

    def call(self, operation, payload):
        allowed = {'accounts:signUp', 'accounts:signInWithPassword',
                   'accounts:signInWithCustomToken',
                   'accounts:update', 'accounts:lookup', 'accounts:delete'}
        if operation not in allowed:
            raise ValueError('Unsupported local auth operation')
        request = Request(self.endpoint + '/identitytoolkit.googleapis.com/v1/'
                          + operation + '?key=fake-api-key',
                          data=json.dumps(payload).encode(),
                          headers={'Content-Type': 'application/json'}, method='POST')
        try:
            with self.opener.open(request, timeout=10) as response:
                return json.load(response)
        except HTTPError as error:
            # Do not include response bodies: they can contain identity/session data.
            raise RuntimeError('Local auth returned HTTP ' + str(error.code)) from None

    def create(self, email, name, password):
        if not isinstance(email, str) or email.count('@') != 1 or not email.endswith('.invalid'):
            raise ValueError('Synthetic account email must use a .invalid domain')
        if not isinstance(name, str) or not name.strip() or len(name) > 120:
            raise ValueError('Supply a bounded synthetic display name')
        if not isinstance(password, str) or len(password) < 8:
            raise ValueError('Supply a synthetic password of at least eight characters')
        account = self.call('accounts:signUp', {
            'email': email, 'password': password, 'returnSecureToken': True})
        try:
            self.call('accounts:update', {
                'idToken': account['idToken'], 'displayName': name,
                'returnSecureToken': True})
        except Exception:
            # No hidden retry or fake success if profile setup fails.
            raise RuntimeError('Local account created but display-name setup failed') from None
        return {'uid': account['localId'], 'email': email, 'display_name': name,
                'authority': 'local-test-only'}

    def fast_account(self, uid, email, name):
        """Create/select a local persona and edit it without a credential prompt.

        Uses the emulator-only JSON custom-token contract. This intentionally
        bypasses credential entry for test setup, not for auth-flow comparison.
        """
        if not isinstance(uid, str) or not re.fullmatch(r'rdd-test-[A-Za-z0-9_-]{1,80}', uid):
            raise ValueError('Choose an rdd-test- synthetic persona ID')
        if not isinstance(email, str) or email.count('@') != 1 or not email.endswith('.invalid'):
            raise ValueError('Synthetic account email must use a .invalid domain')
        if not isinstance(name, str) or not name.strip() or len(name) > 120:
            raise ValueError('Supply a bounded synthetic display name')
        session = self.call('accounts:signInWithCustomToken', {
            'token': json.dumps({'uid': uid}), 'returnSecureToken': True})
        self.call('accounts:update', {'idToken': session['idToken'],
                  'email': email, 'displayName': name, 'returnSecureToken': True})
        return {'uid': uid, 'email': email, 'display_name': name,
                'authority': 'local-test-only', 'mode': 'fast-persona-setup'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--endpoint', default='http://127.0.0.1:9099')
    parser.add_argument('--fixture', required=True,
                        help='Private JSON with synthetic email, name and password')
    parser.add_argument('--persona', help='rdd-test- ID for password-free local setup')
    args = parser.parse_args()
    with open(args.fixture) as stream:
        fixture = json.load(stream)
    auth = LocalAuth(args.endpoint)
    result = (auth.fast_account(args.persona, fixture['email'], fixture['name'])
              if args.persona else auth.create(
                  fixture['email'], fixture['name'], fixture['password']))
    print(json.dumps(result))


if __name__ == '__main__':
    main()
