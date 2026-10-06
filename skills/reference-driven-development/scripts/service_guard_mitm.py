"""mitmproxy adapter; load with lazy connections and no direct device egress.

Missing/invalid policy stays deny-all. Never load third-party forwarding addons
or replay saved production flows alongside this adapter.
"""
import logging

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    parser.error('Load this addon with mitmdump -s; see references/service-testing.md')

from mitmproxy import ctx, http
from service_guard import Policy


class ServiceGuard:
    def __init__(self):
        self.policy = None

    def load(self, loader):
        loader.add_option('rdd_policy', str, '', 'Private reviewed policy JSON')
        loader.add_option('rdd_live', bool, False, 'Explicitly enable reviewed read-only forwarding')

    def configure(self, updates):
        # Invalidate first, including failed reloads; stale permission must not survive.
        self.policy = None
        if ctx.options.rdd_policy:
            try:
                self.policy = Policy.load(ctx.options.rdd_policy)
            except (OSError, ValueError, TypeError):
                logging.error('RDD policy rejected; all requests remain blocked')

    def request(self, flow):
        decision = {'action': 'deny'}
        try:
            if self.policy:
                r = flow.request
                decision = self.policy.decide(r.scheme, r.host, r.port, r.method, r.path,
                                              list(r.headers.items(multi=True)), r.raw_content or b'',
                                              live=ctx.options.rdd_live)
        except Exception:
            # Do not print headers, URLs, bodies or exception contents containing credentials.
            logging.error('RDD evaluation failed; request blocked')
        action = decision['action']
        flow.metadata['rdd_service_guard'] = action
        if action == 'forward':
            return
        if action == 'fixture':
            flow.response = http.Response.make(decision['status'], decision['body'],
                                               {'content-type': decision['content_type'], 'cache-control': 'no-store'})
        else:
            flow.response = http.Response.make(403, b'{"error":"test_request_blocked"}',
                                               {'content-type': 'application/json', 'cache-control': 'no-store'})


addons = [ServiceGuard()]
