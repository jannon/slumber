import sys
import mock
import requests
import slumber
import slumber.serialize
import unittest2 as unittest

from slumber import exceptions


class ResourceTestCase(unittest.TestCase):

    def setUp(self):
        self.base_resource = slumber.Resource(base_url="http://example/api/v1/test", format="json", append_slash=False)

    def test_get_200_json(self):
        r = mock.Mock(spec=requests.Response)
        r.status_code = 200
        r.headers = {"content-type": "application/json"}
        r.content = '{"result": ["a", "b", "c"]}'

        self.base_resource._store.update({
            "session": mock.Mock(spec=requests.Session),
            "serializer": slumber.serialize.Serializer(),
        })
        self.base_resource._store["session"].request.return_value = r

        resp = self.base_resource._request("GET")

        self.assertTrue(resp is r)
        self.assertEqual(resp.content, r.content)

        self.base_resource._store["session"].request.assert_called_once_with(
            "GET",
            "http://example/api/v1/test",
            data=None,
            files=None,
            params=None,
            headers={"content-type": self.base_resource._store["serializer"].get_content_type(), "accept": self.base_resource._store["serializer"].get_content_type()}
        )

        resp = self.base_resource.get()
        self.assertEqual(resp['result'], ['a', 'b', 'c'])

    def test_get_200_text(self):
        r = mock.Mock(spec=requests.Response)
        r.status_code = 200
        r.headers = {"content-type": "text/plain"}
        r.content = "Mocked Content"

        self.base_resource._store.update({
            "session": mock.Mock(spec=requests.Session),
            "serializer": slumber.serialize.Serializer(),
        })
        self.base_resource._store["session"].request.return_value = r

        resp = self.base_resource._request("GET")

        self.assertTrue(resp is r)
        self.assertEqual(resp.content, "Mocked Content")

        self.base_resource._store["session"].request.assert_called_once_with(
            "GET",
            "http://example/api/v1/test",
            data=None,
            files=None,
            params=None,
            headers={"content-type": self.base_resource._store["serializer"].get_content_type(), "accept": self.base_resource._store["serializer"].get_content_type()}
        )

        resp = self.base_resource.get()
        self.assertEqual(resp, r.content)

    def test_options_200_json(self):
        r = mock.Mock(spec=requests.Response)
        r.status_code = 200
        r.headers = {"content-type": "application/json"}
        r.content = '{"actions": {"POST": {"foo": {"required": false, "type": "string"}}}}'

        self.base_resource._store.update({
            "session": mock.Mock(spec=requests.Session),
            "serializer": slumber.serialize.Serializer(),
        })
        self.base_resource._store["session"].request.return_value = r

        resp = self.base_resource._request("OPTIONS")

        self.assertTrue(resp is r)
        self.assertEqual(resp.content, r.content)

        self.base_resource._store["session"].request.assert_called_once_with(
            "OPTIONS",
            "http://example/api/v1/test",
            data=None,
            files=None,
            params=None,
            headers={"content-type": self.base_resource._store["serializer"].get_content_type(),
                     "accept": self.base_resource._store["serializer"].get_content_type()}
        )

        resp = self.base_resource.options()
        self.assertTrue('POST' in resp['actions'])
        self.assertTrue('foo' in resp['actions']['POST'])
        self.assertTrue('type' in resp['actions']['POST']['foo'])
        self.assertEqual(resp['actions']['POST']['foo']['type'], 'string')

    def test_head_200_json(self):
        r = mock.Mock(spec=requests.Response)
        r.status_code = 200
        r.headers = {"content-type": "application/json"}
        r.content = ''

        self.base_resource._store.update({
            "session": mock.Mock(spec=requests.Session),
            "serializer": slumber.serialize.Serializer(),
        })
        self.base_resource._store["session"].request.return_value = r

        resp = self.base_resource._request("HEAD")

        self.assertTrue(resp is r)
        self.assertEqual(resp.content, r.content)

        self.base_resource._store["session"].request.assert_called_once_with(
            "HEAD",
            "http://example/api/v1/test",
            data=None,
            files=None,
            params=None,
            headers={"content-type": self.base_resource._store["serializer"].get_content_type(),
                     "accept": self.base_resource._store["serializer"].get_content_type()}
        )

        resp = self.base_resource.head()
        self.assertEqual(resp, r.content)

    def test_post_201_redirect(self):
        r1 = mock.Mock(spec=requests.Response)
        r1.status_code = 201
        r1.headers = {"location": "http://example/api/v1/test/1"}
        r1.content = ''

        r2 = mock.Mock(spec=requests.Response)
        r2.status_code = 200
        r2.headers = {"content-type": "application/json"}
        r2.content = '{"result": ["a", "b", "c"]}'

        self.base_resource._store.update({
            "session": mock.Mock(spec=requests.Session),
            "serializer": slumber.serialize.Serializer(),
        })
        self.base_resource._store["session"].request.side_effect = (r1, r2)

        resp = self.base_resource._request("POST")

        self.assertTrue(resp is r1)
        self.assertEqual(resp.content, r1.content)

        self.base_resource._store["session"].request.assert_called_once_with(
            "POST",
            "http://example/api/v1/test",
            data=None,
            files=None,
            params=None,
            headers={"content-type": self.base_resource._store["serializer"].get_content_type(), "accept": self.base_resource._store["serializer"].get_content_type()}
        )

        resp = self.base_resource.post(data={'foo': 'bar'})
        self.assertEqual(resp['result'], ['a', 'b', 'c'])

    def test_post_decodable_response(self):
        r = mock.Mock(spec=requests.Response)
        r.status_code = 200
        r.content = '{"result": ["a", "b", "c"]}'
        r.headers = {"content-type": "application/json"}

        self.base_resource._store.update({
            "session": mock.Mock(spec=requests.Session),
            "serializer": slumber.serialize.Serializer(),
        })
        self.base_resource._store["session"].request.return_value = r

        resp = self.base_resource._request("POST")

        self.assertTrue(resp is r)
        self.assertEqual(resp.content, r.content)

        self.base_resource._store["session"].request.assert_called_once_with(
            "POST",
            "http://example/api/v1/test",
            data=None,
            files=None,
            params=None,
            headers={"content-type": self.base_resource._store["serializer"].get_content_type(), "accept": self.base_resource._store["serializer"].get_content_type()}
        )

        resp = self.base_resource.post(data={'foo': 'bar'})
        self.assertEqual(resp['result'], ['a', 'b', 'c'])

    def test_patch_201_redirect(self):
        r1 = mock.Mock(spec=requests.Response)
        r1.status_code = 201
        r1.headers = {"location": "http://example/api/v1/test/1"}
        r1.content = ''

        r2 = mock.Mock(spec=requests.Response)
        r2.status_code = 200
        r2.headers = {"content-type": "application/json"}
        r2.content = '{"result": ["a", "b", "c"]}'

        self.base_resource._store.update({
            "session": mock.Mock(spec=requests.Session),
            "serializer": slumber.serialize.Serializer(),
        })
        self.base_resource._store["session"].request.side_effect = (r1, r2)

        resp = self.base_resource._request("PATCH")

        self.assertTrue(resp is r1)
        self.assertEqual(resp.content, r1.content)

        self.base_resource._store["session"].request.assert_called_once_with(
            "PATCH",
            "http://example/api/v1/test",
            data=None,
            files=None,
            params=None,
            headers={"content-type": self.base_resource._store["serializer"].get_content_type(), "accept": self.base_resource._store["serializer"].get_content_type()}
        )

        resp = self.base_resource.patch(data={'foo': 'bar'})
        self.assertEqual(resp['result'], ['a', 'b', 'c'])

    def test_patch_decodable_response(self):
        r = mock.Mock(spec=requests.Response)
        r.status_code = 200
        r.content = '{"result": ["a", "b", "c"]}'
        r.headers = {"content-type": "application/json"}

        self.base_resource._store.update({
            "session": mock.Mock(spec=requests.Session),
            "serializer": slumber.serialize.Serializer(),
        })
        self.base_resource._store["session"].request.return_value = r

        resp = self.base_resource._request("PATCH")

        self.assertTrue(resp is r)
        self.assertEqual(resp.content, r.content)

        self.base_resource._store["session"].request.assert_called_once_with(
            "PATCH",
            "http://example/api/v1/test",
            data=None,
            files=None,
            params=None,
            headers={"content-type": self.base_resource._store["serializer"].get_content_type(), "accept": self.base_resource._store["serializer"].get_content_type()}
        )

        resp = self.base_resource.patch(data={'foo': 'bar'})
        self.assertEqual(resp['result'], ['a', 'b', 'c'])

    def test_put_201_redirect(self):
        r1 = mock.Mock(spec=requests.Response)
        r1.status_code = 201
        r1.headers = {"location": "http://example/api/v1/test/1"}
        r1.content = ''

        r2 = mock.Mock(spec=requests.Response)
        r2.status_code = 200
        r2.headers = {"content-type": "application/json"}
        r2.content = '{"result": ["a", "b", "c"]}'

        self.base_resource._store.update({
            "session": mock.Mock(spec=requests.Session),
            "serializer": slumber.serialize.Serializer(),
        })
        self.base_resource._store["session"].request.side_effect = (r1, r2)

        resp = self.base_resource._request("PUT")

        self.assertTrue(resp is r1)
        self.assertEqual(resp.content, r1.content)

        self.base_resource._store["session"].request.assert_called_once_with(
            "PUT",
            "http://example/api/v1/test",
            data=None,
            files=None,
            params=None,
            headers={"content-type": self.base_resource._store["serializer"].get_content_type(), "accept": self.base_resource._store["serializer"].get_content_type()}
        )

        resp = self.base_resource.put(data={'foo': 'bar'})
        self.assertEqual(resp['result'], ['a', 'b', 'c'])

    def test_put_decodable_response(self):
        r = mock.Mock(spec=requests.Response)
        r.status_code = 200
        r.content = '{"result": ["a", "b", "c"]}'
        r.headers = {"content-type": "application/json"}

        self.base_resource._store.update({
            "session": mock.Mock(spec=requests.Session),
            "serializer": slumber.serialize.Serializer(),
        })
        self.base_resource._store["session"].request.return_value = r

        resp = self.base_resource._request("PUT")

        self.assertTrue(resp is r)
        self.assertEqual(resp.content, r.content)

        self.base_resource._store["session"].request.assert_called_once_with(
            "PUT",
            "http://example/api/v1/test",
            data=None,
            files=None,
            params=None,
            headers={"content-type": self.base_resource._store["serializer"].get_content_type(), "accept": self.base_resource._store["serializer"].get_content_type()}
        )

        resp = self.base_resource.put(data={'foo': 'bar'})
        self.assertEqual(resp['result'], ['a', 'b', 'c'])

    def test_handle_serialization(self):
        self.base_resource._store.update({
            "serializer": slumber.serialize.Serializer(),
        })

        resp = mock.Mock(spec=requests.Response)
        resp.headers = {"content-type": "application/json; charset=utf-8"}
        resp.content = '{"foo": "bar"}'

        r = self.base_resource._try_to_serialize_response(resp)

        if not isinstance(r, dict):
            self.fail("Serialization did not take place")

    def test_get_200_subresource_json(self):
        r = mock.Mock(spec=requests.Response)
        r.status_code = 200
        r.headers = {"content-type": "application/json"}
        r.content = '{"result": ["a", "b", "c"]}'

        self.base_resource._store.update({
            "session": mock.Mock(spec=requests.Session),
            "serializer": slumber.serialize.Serializer(),
        })
        self.base_resource._store["session"].request.return_value = r

        resp = self.base_resource.subresource._request("GET")

        self.assertTrue(resp is r)
        self.assertEqual(resp.content, r.content)

        self.base_resource._store["session"].request.assert_called_once_with(
            "GET",
            "http://example/api/v1/test/subresource",
            data=None,
            files=None,
            params=None,
            headers={"content-type": self.base_resource._store["serializer"].get_content_type(), "accept": self.base_resource._store["serializer"].get_content_type()}
        )

        resp = self.base_resource.get()
        self.assertEqual(resp['result'], ['a', 'b', 'c'])

    def test_bad_resource_name(self):
        with self.assertRaises(AttributeError):
            self.base_resource._subresource

    def test_get_400_response(self):
        r = mock.Mock(spec=requests.Response)
        r.status_code = 400
        r.headers = {"content-type": "application/json"}
        r.content = ''

        self.base_resource._store.update({
            "session": mock.Mock(spec=requests.Session),
            "serializer": slumber.serialize.Serializer(),
        })
        self.base_resource._store["session"].request.return_value = r

        with self.assertRaises(exceptions.HttpClientError):
            self.base_resource.req._request("GET")

    def test_get_500_response(self):
        r = mock.Mock(spec=requests.Response)
        r.status_code = 500
        r.headers = {"content-type": "application/json"}
        r.content = ''

        self.base_resource._store.update({
            "session": mock.Mock(spec=requests.Session),
            "serializer": slumber.serialize.Serializer(),
        })
        self.base_resource._store["session"].request.return_value = r

        with self.assertRaises(exceptions.HttpServerError):
            self.base_resource.req._request("GET")

    def test_improperly_conf(self):
        with self.assertRaises(exceptions.ImproperlyConfigured):
            client = slumber.API()

    def test_api(self):
        r = mock.Mock(spec=requests.Response)
        r.status_code = 200
        r.headers = {"content-type": "application/json"}
        r.content = '{"result": ["a", "b", "c"]}'

        client = slumber.API(base_url="http://example/api/v1", session=mock.Mock(spec=requests.Session))
        client.test._store["session"].request.return_value = r
        resp = client.test.get()

        self.assertEqual(resp['result'], ['a', 'b', 'c'])

    def test_url(self):
        self.assertEqual(self.base_resource.url(), "http://example/api/v1/test")

    def test_get_200_json_py3(self):
        r = mock.Mock(spec=requests.Response)
        r.status_code = 200
        r.headers = {"content-type": "application/json"}
        r.content = b'{"result": ["a", "b", "c"]}'

        self.base_resource._store.update({
            "session": mock.Mock(spec=requests.Session),
            "serializer": slumber.serialize.Serializer(),
        })
        self.base_resource._store["session"].request.return_value = r

        resp = self.base_resource._request("GET")

        self.assertTrue(resp is r)
        self.assertEqual(resp.content, r.content)

        self.base_resource._store["session"].request.assert_called_once_with(
            "GET",
            "http://example/api/v1/test",
            data=None,
            files=None,
            params=None,
            headers={"content-type": self.base_resource._store["serializer"].get_content_type(), "accept": self.base_resource._store["serializer"].get_content_type()}
        )

        resp = self.base_resource.get()
        self.assertEqual(resp['result'], ['a', 'b', 'c'])
