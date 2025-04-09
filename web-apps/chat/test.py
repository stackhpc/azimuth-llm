import os
import unittest
from unittest.mock import patch

# from unittest import mock
from gradio_client import Client
from app import build_chat_context, SystemMessage, HumanMessage, AIMessage

url = os.environ.get("GRADIO_URL", "http://localhost:7860")
client = Client(url)

class TestSuite(unittest.TestCase):
    # General tests
    def test_gradio_api(self):
        result = client.predict("Hi", api_name="/chat")
        self.assertGreater(len(result), 0)

    # build_chat_context function tests
    @patch("app.settings")
    @patch("app.INCLUDE_SYSTEM_PROMPT", True)
    def test_chat_context_system_prompt(self, mock_settings):
        mock_settings.model_instruction = "You are a helpful assistant."
        latest_message = "What is a mammal?"
        history = [
            {'role': 'user', 'metadata': None, 'content': 'Hi!', 'options': None},
            {"role": "assistant", 'metadata': None, "content": "Hello! How can I help you?", 'options': None},
        ]

        context = build_chat_context(latest_message, history)

        self.assertEqual(len(context), 4)
        self.assertIsInstance(context[0], SystemMessage)
        self.assertEqual(context[0].content, "You are a helpful assistant.")
        self.assertIsInstance(context[1], HumanMessage)
        self.assertEqual(context[1].content, "Hi!")
        self.assertIsInstance(context[2], AIMessage)
        self.assertEqual(context[2].content, "Hello! How can I help you?")
        self.assertIsInstance(context[3], HumanMessage)
        self.assertEqual(context[3].content, latest_message)

    @patch("app.settings")
    @patch("app.INCLUDE_SYSTEM_PROMPT", False)
    def test_chat_context_human_prompt(self, mock_settings):
        mock_settings.model_instruction = "You are a very helpful assistant."
        latest_message = "What is a fish?"
        history = [
            {"role": "user", 'metadata': None, "content": "Hi there!", 'options': None},
            {"role": "assistant", 'metadata': None, "content": "Hi! How can I help you?", 'options': None},
        ]

        context = build_chat_context(latest_message, history)

        self.assertEqual(len(context), 3)
        self.assertIsInstance(context[0], HumanMessage)
        self.assertEqual(context[0].content, "You are a very helpful assistant.\n\nHi there!")
        self.assertIsInstance(context[1], AIMessage)
        self.assertEqual(context[1].content, "Hi! How can I help you?")
        self.assertIsInstance(context[2], HumanMessage)
        self.assertEqual(context[2].content, latest_message)

if __name__ == "__main__":
    unittest.main()
