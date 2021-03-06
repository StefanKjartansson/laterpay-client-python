#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function

import copy
import json
import logging
import random
import re
import string
import time
import warnings

from . import signing
from . import compat


_log = logging.getLogger(__name__)


class InvalidTokenException(Exception):
    pass


class InvalidItemDefinition(Exception):
    def __init__(self, message):
        self.message = message

    def __repr__(self):
        return self.message


class APIException(Exception):
    """
    Thrown when generating the url
    """


class ItemDefinition(object):

    def __init__(self, item_id, pricing, vat, url, title, purchasedatetime=None, cp=None):

        for price in pricing.split(','):
            if not re.match('[A-Z]{3}\d+', price):
                raise InvalidItemDefinition('Pricing is not valid: %s' % pricing)

        for v in vat.split(','):

            if len(v) < 2:
                raise InvalidItemDefinition('Invalid length for vat: %s' % v)

            if not all((65 <= ord(c) <= 90) for c in v[:2]):
                raise InvalidItemDefinition('Invalid country for vat: %s' % vat)

            try:
                float(v[2:])
            except:
                raise InvalidItemDefinition('Invalid number part for vat: %s' % vat)

        if purchasedatetime is not None and not isinstance(purchasedatetime, int):
            raise InvalidItemDefinition("Invalid purchasedatetime %s. This should be a UTC-based epoch timestamp "
                                        "in seconds of type int")

        self.data = {
            'article_id': item_id,
            'purchasedatetime': int(time.time()) if purchasedatetime is None else purchasedatetime,
            'pricing': pricing,
            'vat': vat,
            'url': url,
            'title': title,
            'cp': cp,
        }


class LaterPayClient(object):

    def __init__(self,
                 cp_key,
                 shared_secret,
                 api_root='https://api.laterpay.net',
                 web_root='https://web.laterpay.net',
                 lptoken=None):

        self.cp_key = cp_key
        self.api_root = api_root
        self.web_root = web_root
        self.shared_secret = shared_secret
        self.lptoken = lptoken

    def get_gettoken_redirect(self, return_to):
        url = self._gettoken_url
        data = {
            'redir': return_to,
            'cp': self.cp_key,
        }
        params = self._sign_and_encode(
            params=data,
            url=url,
            method="GET",
        )
        url = '%s?%s' % (url, params)

        return url

    def get_identify_url(self, identify_callback=None):
        base_url = self._identify_url
        data = {'cp': self.cp_key}

        if identify_callback is not None:
            data['callback_url'] = identify_callback

        params = self._sign_and_encode(data, url=base_url, method="GET")
        url = '%s?%s' % (base_url, params)

        return url

    def get_iframeapi_links_url(self,
                                next_url,
                                css_url=None,
                                forcelang=None,
                                show_greeting=False,
                                show_long_greeting=False,
                                show_login=False,
                                show_signup=False,
                                show_long_signup=False,
                                use_jsevents=False):
        warnings.warn("get_iframe_links_url is deprecated. Please use get_controls_links_url. "
                      "It will be removed on a future release.")
        return self.get_controls_links_url(next_url, css_url, forcelang, show_greeting, show_long_greeting,
                                           show_login, show_signup, show_long_signup, use_jsevents)

    def get_controls_links_url(self,
                               next_url,
                               css_url=None,
                               forcelang=None,
                               show_greeting=False,
                               show_long_greeting=False,
                               show_login=False,
                               show_signup=False,
                               show_long_signup=False,
                               use_jsevents=False):

        data = {'next': next_url}
        data['cp'] = self.cp_key
        if forcelang is not None:
            data['forcelang'] = forcelang
        if css_url is not None:
            data['css'] = css_url
        if use_jsevents:
            data['jsevents'] = "1"
        if show_long_greeting:
            data['show'] = '%sgg' % data.get('show', '')
        elif show_greeting:
            data['show'] = '%sg' % data.get('show', '')
        if show_login:
            data['show'] = '%sl' % data.get('show', '')
        if show_long_signup:
            data['show'] = '%sss' % data.get('show', '')
        elif show_signup:
            data['show'] = '%ss' % data.get('show', '')

        data['xdmprefix'] = "".join(random.choice(string.ascii_letters) for x in xrange(10))

        url = '%s/controls/links' % self.web_root
        params = self._sign_and_encode(data, url, method="GET")

        return '%s?%s' % (url, params)

    def get_iframeapi_balance_url(self, forcelang=None):
        warnings.warn("get_iframe_balance_url is deprecated. Please use get_controls_balance_url. "
                      "It will be removed on a future release.")
        return self.get_controls_balance_url(forcelang)

    def get_controls_balance_url(self, forcelang=None):
        data = {'cp': self.cp_key}
        if forcelang is not None:
            data['forcelang'] = forcelang
        data['xdmprefix'] = "".join(random.choice(string.ascii_letters) for x in xrange(10))

        base_url = "{web_root}/controls/balance".format(web_root=self.web_root)
        encoded_data = self._sign_and_encode(data, base_url)
        url = "{base_url}?{encoded_data}".format(base_url=base_url, encoded_data=encoded_data)
        return url

    def _get_dialog_api_url(self, url):
        return '%s/dialog-api?url=%s' % (self.web_root, compat.quote_plus(url))

    def get_login_dialog_url(self, next_url, use_jsevents=False):
        url = '%s/account/dialog/login?next=%s%s%s' % (self.web_root, compat.quote_plus(next_url),
                                                       "&jsevents=1" if use_jsevents else "",
                                                       "&cp=%s" % self.cp_key)
        return self._get_dialog_api_url(url)

    def get_signup_dialog_url(self, next_url, use_jsevents=False):
        url = '%s/account/dialog/signup?next=%s%s%s' % (self.web_root, compat.quote_plus(next_url),
                                                        "&jsevents=1" if use_jsevents else "",
                                                        "&cp=%s" % self.cp_key)
        return self._get_dialog_api_url(url)

    def get_logout_dialog_url(self, next_url, use_jsevents=False):
        url = '%s/account/dialog/logout?next=%s%s%s' % (self.web_root, compat.quote_plus(next_url),
                                                        "&jsevents=1" if use_jsevents else "",
                                                        "&cp=%s" % self.cp_key)
        return self._get_dialog_api_url(url)

    @property
    def _access_url(self):
        return '%s/access' % self.api_root

    @property
    def _add_url(self):
        return '%s/add' % self.api_root

    @property
    def _identify_url(self):
        return '%s/identify' % self.api_root

    @property
    def _gettoken_url(self):
        return '%s/gettoken' % self.api_root

    def _get_web_url(self,
                     item_definition,
                     page_type,
                     product_key=None,
                     dialog=True,
                     use_jsevents=False,
                     skip_add_to_invoice=False,
                     transaction_reference=None,
                     consumable=False,
                     expires_at=None):

        data = copy.copy(item_definition.data)

        if use_jsevents:
            data['jsevents'] = 1

        if consumable:
            data['consumable'] = 1

        if expires_at is not None:
            data['expires_at'] = expires_at

        if transaction_reference:

            if len(transaction_reference) < 6:
                raise APIException('Transaction reference is not unique enough')

            data['tref'] = transaction_reference

        if skip_add_to_invoice:
            data['skip_add_to_invoice'] = 1

        if dialog:
            prefix = '%s/%s' % (self.web_root, 'dialog')
        else:
            prefix = self.web_root

        if product_key is not None:
            base_url = "%s/%s/%s" % (prefix, product_key, page_type)
        else:
            base_url = "%s/%s" % (prefix, page_type)

        params = self._sign_and_encode(data, base_url, method="GET")
        url = "{base_url}?{params}".format(base_url=base_url, params=params)

        return self._get_dialog_api_url(url)

    def get_buy_url(self,
                    item_definition,
                    product_key=None,
                    dialog=True,
                    use_jsevents=False,
                    skip_add_to_invoice=False,
                    transaction_reference=None,
                    consumable=False,
                    expires_at=None):

        return self._get_web_url(
            item_definition,
            'buy',
            product_key=product_key,
            dialog=dialog,
            use_jsevents=use_jsevents,
            skip_add_to_invoice=skip_add_to_invoice,
            transaction_reference=transaction_reference,
            consumable=consumable,
            expires_at=expires_at)

    def get_add_url(self,
                    item_definition,
                    product_key=None,
                    dialog=True,
                    use_jsevents=False,
                    skip_add_to_invoice=False,
                    transaction_reference=None,
                    consumable=False,
                    expires_at=None):

        return self._get_web_url(
            item_definition,
            'add',
            product_key=product_key,
            dialog=dialog,
            use_jsevents=use_jsevents,
            skip_add_to_invoice=skip_add_to_invoice,
            transaction_reference=transaction_reference,
            consumable=consumable,
            expires_at=expires_at)

    def _sign_and_encode(self, params, url, method="GET"):
        return signing.sign_and_encode(self.shared_secret, params, url=url, method=method)

    def _make_request(self, url, params, method='GET'):

        params = self._sign_and_encode(params=params, url=url, method=method)

        headers = {
            'X-LP-APIVersion': 2,
            'User-Agent': 'LaterPay Client - Python - v0.2'
        }

        if method == 'POST':
            req = compat.Request(url, data=params, headers=headers)
        else:
            url = "%s?%s" % (url, params)
            req = compat.Request(url, headers=headers)

        _log.debug("Making request to %s", url)

        try:
            response = compat.urlopen(req).read()
        except compat.URLError as e:
            _log.debug("Request failed with reason: %s", e.reason)
            resp = {'status': 'connection_error'}
        except:
            _log.debug("Unexpected error with request")
            resp = {'status': 'unexpected error'}
        else:
            _log.debug("Received response %s", response)
            resp = json.loads(response)

        if 'new_token' in resp:
            self.lptoken = resp['new_token']

        if resp.get('status', None) == 'invalid_token':
            self.lptoken = None

        return resp

    def has_token(self):

        return self.lptoken is not None

    def add_metered_access(self, article_id, threshold=5, product_key=None ):

        params = {
            'lptoken': self.lptoken,
            'cp': self.cp_key,
            'threshold': threshold,
            'feature': 'metered',
            'period': 'monthly',
            'article_id': article_id
        }
        if product_key is not None:
            params['product'] = product_key

        data = self._make_request(self._add_url, params, method='POST')

        if data['status'] == 'invalid_token':
            raise InvalidTokenException()

    def get_metered_access(self, article_ids, threshold=5, product_key=None):

        if not isinstance(article_ids, (list, tuple)):
            article_ids = [article_ids]

        params = {
            'lptoken': self.lptoken,
            'cp': self.cp_key,
            'article_id': article_ids,
            'feature': 'metered',
            'threshold': threshold,
            'period': 'monthly'
        }

        if product_key is not None:
            params['product'] = product_key

        data = self._make_request(self._access_url, params)
        subs = data.get('subs', [])

        if data['status'] == 'invalid_token':
            raise InvalidTokenException()

        if data['status'] != 'ok':
            raise Exception()

        exceeded = data.get('exceeded', False)

        return data['articles'], exceeded, subs

    def get_access(self, article_ids, product_key=None):

        if not isinstance(article_ids, (list, tuple)):
            article_ids = [article_ids]

        params = {
            'lptoken': self.lptoken,
            'cp': self.cp_key,
            'article_id': article_ids
        }

        if product_key is not None:
            params['product'] = product_key

        data = self._make_request(self._access_url, params)

        allowed_statuses = ['ok', 'invalid_token', 'connection_error']

        if data['status'] not in allowed_statuses:
            raise Exception(data['status'])

        return data
