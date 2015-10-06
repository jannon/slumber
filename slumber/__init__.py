import requests

try:
    from urllib.parse import urlparse, urlsplit, urlunsplit
except ImportError:
    from urlparse import urlparse, urlsplit, urlunsplit

from . import exceptions
from .serialize import Serializer
from .utils import url_join, iterator, copy_kwargs

__all__ = ["Resource", "API"]


class ResourceAttributesMixin(object):
    """
    A Mixin that allows access to an undefined attribute on a class.
    Instead of raising an attribute error, the undefined attribute will
    return a Resource Instance which can be used to make calls to the
    resource identified by the attribute.

    The type of the resource returned can be overridden by adding a
    resource_class attribute.

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
        # Don't allow access to 'private' by convention attributes.
        # @@@: How would this work with resources names that begin with
        # underscores?
        if item.startswith("_"):
            raise AttributeError(item)

        methods = self._get_methods()
        if item not in methods.keys():
            kwargs = copy_kwargs(self._store)
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

        kwargs = copy_kwargs(self._store)

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

        return self._get_resource(**kwargs)

    def _request(self, method, data=None, files=None, params=None):
        serializer = self._store["serializer"]
        url = self.url()

        headers = {"accept": serializer.get_content_type()}

        if not files:
            headers["content-type"] = serializer.get_content_type()
            if data is not None:
                data = serializer.dumps(data)

        resp = self._store["session"].request(method, url, data=data, params=params, files=files,
                                              headers=headers)

        # TODO: Deprecate custom exceptions and pass through requests exceptions
        if 400 <= resp.status_code <= 499:
            exception_class = exceptions.HttpNotFoundError if resp.status_code == 404 else exceptions.HttpClientError
            raise exception_class("Client Error %s: %s" % (resp.status_code, url), response=resp, content=resp.content)
        elif 500 <= resp.status_code <= 599:
            raise exceptions.HttpServerError("Server Error %s: %s" % (resp.status_code, url),
                                             response=resp, content=resp.content)

        self._ = resp

        return resp

    def _handle_redirect(self, resp, **kwargs):
        # @@@ Hacky, see description in __call__
        resource_obj = self(url_override=resp.headers["location"])
        return resource_obj.get(**kwargs)

    def _try_to_serialize_response(self, resp):
        s = self._store["serializer"]
        if resp.status_code in [204, 205]:
            return

        if resp.headers.get("content-type", None) and resp.content:
            content_type = resp.headers.get("content-type").split(";")[0].strip()

            try:
                stype = s.get_serializer(content_type=content_type)
            except exceptions.SerializerNotAvailable:
                return resp.content

            if type(resp.content) == bytes:
                try:
                    encoding = requests.utils.guess_json_utf(resp.content)
                    return stype.loads(resp.content.decode(encoding))
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

        if auth is not None:
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

    def _get_resource(self, **kwargs):
        return self.resource_class(**kwargs)

    def _set_response(self, resp):
        self._status_code = resp.status_code
        self._headers = resp.headers

    @property
    def status_code(self):
        return self._status_code

    @property
    def headers(self):
        return self._headers
