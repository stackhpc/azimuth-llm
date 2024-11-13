import os
import unittest

# from unittest import mock
from gradio_client import Client

url = os.environ.get("GRADIO_URL", "http://localhost:7860")
client = Client(url)

class TestSuite(unittest.TestCase):

    def test_gradio_api(self):
        result = client.predict("Hi", api_name="/chat")
        self.assertGreater(len(result), 0)

    # def test_mock_response(self):
    #     with mock.patch('app.client.stream_response', return_value=(char for char in "Mocked")) as mock_response:
    #         result = client.predict("Hi", api_name="/chat")
    #         # mock_response.assert_called_once_with("Hi", [])
    #         self.assertEqual(result, "Mocked")

if __name__ == "__main__":
    unittest.main()
