#!/usr/bin/env python3
"""Optional Exa discovery and APKCube acquisition. No automatic retries or installs."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import time
from urllib import request, parse, error


class NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('redirect refused; credentials and signed URLs must stay scoped')


def write_private(path, value):
    with open(path, 'x', encoding='utf-8', opener=lambda p, f: os.open(p, f, 0o600)) as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')


def api(url, key_name, body=None):
    parsed = parse.urlsplit(url)
    expected = {'EXA_API_KEY': 'api.exa.ai', 'APKCUBE_API_KEY': 'apkcube.com'}.get(key_name)
    if (expected is None or parsed.scheme != 'https' or parsed.hostname != expected or
            parsed.username or parsed.password or parsed.port not in (None, 443) or
            (key_name == 'APKCUBE_API_KEY' and not parsed.path.startswith('/api/v1/'))):
        raise ValueError('unqualified API credential origin')
    key = os.environ.get(key_name)
    if not key:
        raise ValueError(key_name + ' is not configured')
    headers = {'Content-Type': 'application/json'}
    headers['x-api-key' if key_name == 'EXA_API_KEY' else 'Authorization'] = key if key_name == 'EXA_API_KEY' else 'Bearer ' + key
    req = request.Request(url, data=None if body is None else json.dumps(body).encode(), headers=headers)
    started = time.monotonic()
    try:
        with request.build_opener(NoRedirect).open(req, timeout=30) as response:
            payload = response.read(8 * 1024 * 1024 + 1)
            if len(payload) > 8 * 1024 * 1024:
                raise ValueError('API response exceeds 8 MiB')
            data = json.loads(payload)
            receipt = {'elapsed_seconds': time.monotonic() - started,
                       'credits_cost': response.headers.get('X-Credits-Cost'),
                       'credits_remaining': response.headers.get('X-Credits-Remaining')}
            return data, receipt
    except error.HTTPError as exc:
        raise ValueError('API HTTP ' + str(exc.code) + '; no retry performed') from None
    except error.URLError:
        raise ValueError('API transport failure; no retry performed') from None


def exa_body(query, mode='auto', domains=()):
    if not query.strip() or mode not in {'auto', 'fast', 'instant', 'deep-lite', 'deep', 'deep-reasoning'}:
        raise ValueError('invalid search query or mode')
    result = {'query': query, 'type': mode, 'numResults': 10, 'contents': {'highlights': True}}
    if domains:
        result['includeDomains'] = list(domains)
    return result


def package_path(package):
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z][A-Za-z0-9_]*)+', package):
        raise ValueError('provide an exact Android package identifier')
    return 'https://apkcube.com/api/v1/apps/' + package


def download(ticket, package, apk_id, target, limit):
    """Qualify provider identity/hash/size; download with no API authorization header."""
    if ticket.get('packageName') != package or str(ticket.get('apkId')) != apk_id:
        raise ValueError('ticket does not match selected package/build')
    digest = ticket.get('sha256', '')
    size = ticket.get('fileSize')
    if not re.fullmatch(r'[0-9a-fA-F]{64}', digest) or type(size) is not int or not 0 < size <= limit:
        raise ValueError('missing or invalid bounded SHA-256/size')
    url = parse.urlsplit(ticket.get('url', ''))
    # Documented download host; unknown hosts require a reviewed adapter change.
    if (url.scheme != 'https' or not url.hostname or
            not url.hostname.endswith('.r2.cloudflarestorage.com') or
            url.username or url.password or url.port not in (None, 443)):
        raise ValueError('unqualified download origin')
    target = Path(target)
    if target.exists():
        raise FileExistsError('output already exists')
    tmp = None
    try:
        with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as stream:
            tmp = Path(stream.name)
            total, actual = 0, hashlib.sha256()
            try:
                with request.build_opener(NoRedirect).open(request.Request(ticket['url']), timeout=30) as response:
                    while True:
                        chunk = response.read(1024 * 1024)
                        if not chunk:
                            break
                        total += len(chunk)
                        if total > size:
                            raise ValueError('download exceeds declared size')
                        stream.write(chunk)
                        actual.update(chunk)
            except (error.HTTPError, error.URLError):
                raise ValueError('file transport failure; signed URL withheld; no retry performed') from None
        if total != size or actual.hexdigest() != digest.lower():
            raise ValueError('download size or SHA-256 mismatch')
        os.link(tmp, target)  # atomic no-clobber publication after qualification
        return {'packageName': package, 'apkId': apk_id, 'sha256': actual.hexdigest(),
                'bytes': total, 'format': ticket.get('format'), 'versionName': ticket.get('versionName'),
                'versionCode': ticket.get('versionCode'), 'signature_verified_locally': False}
    finally:
        if tmp is not None:
            tmp.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    exa = commands.add_parser('exa-search')
    exa.add_argument('query')
    exa.add_argument('--mode', default='auto')
    exa.add_argument('--domain', action='append', default=[])
    exa.add_argument('--output', required=True, type=Path)
    for name in ['apk-search', 'apk-versions', 'apk-download']:
        command = commands.add_parser(name)
        command.add_argument('selection')
        command.add_argument('--output', required=True, type=Path)
        if name == 'apk-download':
            command.add_argument('--apk-id', required=True)
            command.add_argument('--receipt', required=True, type=Path)
            command.add_argument('--max-bytes', type=int, default=1024 * 1024 * 1024)
    args = parser.parse_args()
    destinations = [args.output] + ([args.receipt] if args.command == 'apk-download' else [])
    if len(set(destinations)) != len(destinations) or any(not p.parent.is_dir() for p in destinations):
        parser.error('outputs need distinct paths in existing directories; no request sent')
    if args.output.exists() or (args.command == 'apk-download' and args.receipt.exists()):
        parser.error('output already exists; no request sent')
    try:
        if args.command == 'exa-search':
            body = exa_body(args.query, args.mode, args.domain)
            data, receipt = api('https://api.exa.ai/search', 'EXA_API_KEY', body)
            write_private(args.output, {'provider': 'exa', 'query': body, 'response': data, 'receipt': receipt,
                                        'source_inspection_performed': False})
        elif args.command == 'apk-search':
            data, receipt = api('https://apkcube.com/api/v1/apps?' + parse.urlencode({'q': args.selection}), 'APKCUBE_API_KEY')
            write_private(args.output, {'provider': 'apkcube', 'response': data, 'receipt': receipt})
        elif args.command == 'apk-versions':
            data, receipt = api(package_path(args.selection) + '/versions', 'APKCUBE_API_KEY')
            write_private(args.output, {'provider': 'apkcube', 'response': data, 'receipt': receipt})
        else:
            if not re.fullmatch(r'[0-9]+', args.apk_id) or args.max_bytes <= 0:
                raise ValueError('invalid build identifier or download bound')
            ticket, receipt = api(package_path(args.selection) + '/download', 'APKCUBE_API_KEY', {'apkId': args.apk_id})
            result = download(ticket, args.selection, args.apk_id, args.output, args.max_bytes)
            write_private(args.receipt, {'provider': 'apkcube', 'artifact': result, 'receipt': receipt,
                                         'signed_url_retained': False, 'installed': False})
        print('Saved private output; provider result requires inspection.')
    except (ValueError, OSError) as exc:
        parser.exit(1, str(exc) + '\n')


if __name__ == '__main__':
    main()
