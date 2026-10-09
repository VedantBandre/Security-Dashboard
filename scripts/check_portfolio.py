"""Smoke-test a built deployment behind the documented trusted ingress contract.

Usage: python scripts/check_portfolio.py http://127.0.0.1:8000 demo.example.com
This internal test supplies ingress headers; it is not a public TLS certificate test.
"""
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def main():
    base, host = sys.argv[1:]
    parsed = urllib.parse.urlsplit(base)
    if parsed.scheme not in {'http', 'https'} or not parsed.netloc:
        raise ValueError('Provide an HTTP or HTTPS application URL.')
    opener = urllib.request.build_opener(NoRedirect())

    def request(path, expected, *, forwarded=True, request_host=host, data=None):
        headers = {'Host': request_host}
        if forwarded:
            headers['X-Forwarded-Proto'] = 'https'
        req = urllib.request.Request(base.rstrip('/') + path, headers=headers, data=data)  # noqa: S310 -- HTTP(S) base validated above.
        try:
            response = opener.open(req, timeout=10)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            if response.status != expected:
                raise RuntimeError(f'{path}: expected {expected}, got {response.status}')
            return response.headers, response.read()

    headers, html = request('/', 200)
    if 'no-store' not in headers.get('Cache-Control', ''):
        raise RuntimeError('Entry document must not be cached.')
    assets = re.findall(r'(?:src|href)="(/assets/[^\"]+)"', html.decode())
    if len(assets) < 2:
        raise RuntimeError('Built frontend scripts/styles were not found.')
    for asset in assets:
        _, data = request(asset, 200)
        if not data:
            raise RuntimeError('Empty frontend asset.')
    _, data = request('/health/', 200)
    if json.loads(data) != {'status': 'ok'}:
        raise RuntimeError('Database health check failed.')
    request('/events', 403)
    request('/auth/login', 403, data=b'{}')
    request('/unknown-api', 404)
    request('/health/', 400, request_host='untrusted.example.com')
    request(assets[0], 400, request_host='untrusted.example.com')
    headers, _ = request('/auth/session', 200)
    cookie = headers.get('Set-Cookie', '')
    if 'Secure' not in cookie or 'HttpOnly' not in cookie:
        raise RuntimeError('CSRF session bootstrap cookie must be Secure and HttpOnly.')
    headers, _ = request('/', 301, forwarded=False)
    if not headers.get('Location', '').startswith('https://'):
        raise RuntimeError('HTTP must redirect to HTTPS.')
    print('Portfolio smoke check passed: frontend assets, database health, host validation, HTTPS redirect, CSRF, and anonymous API restrictions.')


if __name__ == '__main__':
    main()
