import requests

try:
    from urllib.parse import urlparse, urlsplit, urlunsplit
except ImportError:
    from urlparse import urlparse, urlsplit, urlunsplit

from . import exceptions
from .serialize import Serializer
from .utils import url_join, iterator

__all__ = ["Resource", "API"]


class ResourceAttributesMixin(object):
    """
    A Mixin that makes it so that accessing an undefined attribute on a class
    results in returning a Resource Instance. This Instance can then be used
    to make calls to the a Resource.

    It assumes that a Meta class exists at self._meta with all the required
    attributes.
    """

    _methods = {
        'get': {'method': 'GET', 'has_data': False},
        'head': {'method': 'HEAD', 'has_data': False},
        'options': {'method': 'OPTIONS', 'has_data': False},
        'post': {'method': 'POST', 'has_data': True},
        'put': {'method': 'PUT', 'has_data': True},
        'patch': {'method': 'PATCH', 'has_data': True},
        'delete': {'method': 'DELETE', 'has_data': True},
    }

    def __getattr__(self, item):
        if item.startswith("_"):
            raise AttributeError(item)

        methods = self._get_methods()
        if item not in methods.keys():
            kwargs = self._store.copy()
            kwargs.update({"base_url": url_join(self._store["base_url"], item)})

            return Resource(**kwargs)
        self._call = methods[item]
        return self

    def _get_methods(self):
        return self._methods


class Resource(ResourceAttributesMixin, object):
    """
    Resource provides the main functionality behind slumber. It handles the
    attribute -> url, kwarg -> query param, and other related behind the scenes
    python to HTTP transformations. It's goal is to represent a single resource
    which may or may not have children.

    It assumes that a Meta class exists at self._meta with all the required
    attributes.
    """

    def __init__(self, *args, **kwargs):
        self._store = kwargs
        self._call = None

    def __call__(self, res_id=None, res_format=None, url_override=None, **kwargs):
        """
        Returns a new instance of self modified by one or more of the available
        parameters. These allows us to do things like override format for a
        specific request, and enables the api.resource(ID).get() syntax to get
        a specific resource by it's ID.
        """

        # Try for method call first
        if self._call:
            return self._perform_action(**kwargs)

        # Short Circuit out if the call is empty
        if res_id is None and res_format is None and url_override is None:
            return self

        kwargs = self._store.copy()

        if id is not None:
            kwargs["base_url"] = url_join(self._store["base_url"], res_id)

        if res_format is not None:
            kwargs["format"] = res_format

        if url_override is not None:
            # @@@ This is hacky and we should probably figure out a better way
            #    of handling the case when a POST/PUT doesn't return an object
            #    but a Location to an object that we need to GET.
            kwargs["base_url"] = url_override

        kwargs["session"] = self._store["session"]

        return self.__class__(**kwargs)

    def _request(self, method, data=None, files=None, params=None):
        s = self._store["serializer"]
        url = self.url()

        headers = {"accept": s.get_content_type()}

        if not files:
            headers["content-type"] = s.get_content_type()
            if data is not None:
                data = s.dumps(data)

        resp = self._store["session"].request(method, url, data=data, params=params, files=files,
                                              headers=headers)

        # TODO: Deprecate custom exceptions and pass through requests exceptions
        if 400 <= resp.status_code <= 499:
            raise exceptions.HttpClientError("Client Error %s: %s" % (resp.status_code, url),
                                             response=resp, content=resp.content)
        elif 500 <= resp.status_code <= 599:
            raise exceptions.HttpServerError("Server Error %s: %s" % (resp.status_code, url),
                                             response=resp, content=resp.content)

        self._ = resp

        return resp

    def _handle_redirect(self, resp, **kwargs):
        # @@@ Hacky, see description in __call__
        resource_obj = self(url_override=resp.headers["location"])
        return resource_obj.get(params=kwargs)

    def _try_to_serialize_response(self, resp):
        s = self._store["serializer"]

        if resp.headers.get("content-type", None) and resp.content:
            content_type = resp.headers.get("content-type").split(";")[0].strip()

            try:
                stype = s.get_serializer(content_type=content_type)
            except exceptions.SerializerNotAvailable:
                return resp.content

            if type(resp.content) == bytes:
                try:
                    return stype.loads(resp.content.decode())
                except:
                    return resp.content
            return stype.loads(resp.content)
        else:
            return resp.content

    def _process_response(self, resp):
        self._store["api"]._set_response(resp)

        if 200 <= resp.status_code <= 299:
            return self._try_to_serialize_response(resp)
        else:
            return  # @@@ We should probably do some sort of error here? (Is this even possible?)

    def _perform_action(self, **kwargs):
        method = self._call['method']

        if self._call['has_data']:
            data = kwargs.pop('data', None)
            files = kwargs.pop('files', None)
            resp = self._request(method, data=data, files=files, params=kwargs)
        else:
            resp = self._request(method, params=kwargs)

        return self._process_response(resp)

    def url(self):
        url = self._store["base_url"]

        if self._store["append_slash"] and not url.endswith("/"):
            url = url + "/"

        return url


class API(ResourceAttributesMixin, object):

    def __init__(self, base_url=None, auth=None, res_format=None, append_slash=True, session=None,
                 serializer=None):
        if serializer is None:
            serializer = Serializer(default=res_format)

        if session is None:
            session = requests.session()
            session.auth = auth

        self._store = {
            "base_url": base_url,
            "format": res_format if res_format is not None else "json",
            "append_slash": append_slash,
            "session": session,
            "serializer": serializer,
            "api": self
        }

        # Do some Checks for Required Values
        if self._store.get("base_url") is None:
            raise exceptions.ImproperlyConfigured("base_url is required")

    def _set_response(self, resp):
        self._status_code = resp.status_code
        self._headers = resp.headers

    @property
    def status_code(self):
        return self._status_code

    @property
    def headers(self):
        return self._headers
