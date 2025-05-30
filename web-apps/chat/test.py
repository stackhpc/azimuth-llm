import openai
import os
import unittest

from gradio_client import Client
from unittest.mock import patch, MagicMock, Mock
from langchain.schema import HumanMessage, AIMessage, SystemMessage
from app import build_chat_context, inference, PossibleSystemPromptException, gr

url = os.environ.get("GRADIO_URL", "http://localhost:7860")
client = Client(url)
latest_message = "Why don't humans drink horse milk?"
history = [
    {
        "role": "user",
        "metadata": None,
        "content": "Hi!",
        "options": None,
    },
    {
        "role": "assistant",
        "metadata": None,
        "content": "Hello! How can I help you?",
        "options": None,
    },
]

class TestAPI(unittest.TestCase):
    def test_gradio_api(self):
        result = client.predict("Hi", api_name="/chat")
        self.assertGreater(len(result), 0)

class TestBuildChatContext(unittest.TestCase):
    @patch("app.settings")
    @patch("app.INCLUDE_SYSTEM_PROMPT", True)
    def test_chat_context_system_prompt(self, mock_settings):
        mock_settings.model_instruction = "You are a helpful assistant."

        context = build_chat_context(latest_message, history)

        self.assertEqual(len(context), 4)
        self.assertIsInstance(context[0], SystemMessage)
        self.assertEqual(context[0].content, "You are a helpful assistant.")
        self.assertIsInstance(context[1], HumanMessage)
        self.assertEqual(context[1].content, history[0]["content"])
        self.assertIsInstance(context[2], AIMessage)
        self.assertEqual(context[2].content, history[1]["content"])
        self.assertIsInstance(context[3], HumanMessage)
        self.assertEqual(context[3].content, latest_message)

    @patch("app.settings")
    @patch("app.INCLUDE_SYSTEM_PROMPT", False)
    def test_chat_context_human_prompt(self, mock_settings):
        mock_settings.model_instruction = "You are a very helpful assistant."

        context = build_chat_context(latest_message, history)

        self.assertEqual(len(context), 3)
        self.assertIsInstance(context[0], HumanMessage)
        self.assertEqual(context[0].content, "You are a very helpful assistant.\n\nHi!")
        self.assertIsInstance(context[1], AIMessage)
        self.assertEqual(context[1].content, history[1]["content"])
        self.assertIsInstance(context[2], HumanMessage)
        self.assertEqual(context[2].content, latest_message)

class TestInference(unittest.TestCase):
    @patch("app.settings")
    @patch("app.llm")
    @patch("app.log")
    def test_inference_success(self, mock_logger, mock_llm, mock_settings):
        mock_llm.stream.return_value = [MagicMock(content="response_chunk")]

        mock_settings.model_instruction = "You are a very helpful assistant."

        responses = list(inference(latest_message, history))

        self.assertEqual(responses, ["response_chunk"])
        mock_logger.debug.assert_any_call("Inference request received with history: %s", history)

    @patch("app.llm")
    @patch("app.build_chat_context")
    def test_inference_thinking_tags(self, mock_build_chat_context, mock_llm):
        mock_build_chat_context.return_value = ["mock_context"]
        mock_llm.stream.return_value = [
            MagicMock(content="<think>"),
            MagicMock(content="processing"),
            MagicMock(content="</think>"),
            MagicMock(content="final response"),
        ]

        responses = list(inference(latest_message, history))

        self.assertEqual(responses, ["Thinking...", "Thinking...", "", "final response"])

    @patch("app.llm")
    @patch("app.INCLUDE_SYSTEM_PROMPT", True)
    @patch("app.build_chat_context")
    @patch("app.log")
    def test_inference_PossibleSystemPromptException(self, mock_logger, mock_build_chat_context, mock_llm):
        mock_build_chat_context.return_value = ["mock_context"]
        mock_response = Mock()
        mock_response.json.return_value = {"message": "Bad request"}

        mock_llm.stream.side_effect = openai.BadRequestError(
            message="Bad request",
            response=mock_response,
            body=None
        )

        with self.assertRaises(PossibleSystemPromptException):
            list(inference(latest_message, history))
        mock_logger.error.assert_called_once_with("Received BadRequestError from backend API: %s", mock_llm.stream.side_effect)

    @patch("app.llm")
    @patch("app.INCLUDE_SYSTEM_PROMPT", False)
    @patch("app.build_chat_context")
    @patch("app.log")
    def test_inference_general_error(self, mock_logger, mock_build_chat_context, mock_llm):
        mock_build_chat_context.return_value = ["mock_context"]
        mock_response = Mock()
        mock_response.json.return_value = {"message": "Bad request"}

        mock_llm.stream.side_effect = openai.BadRequestError(
            message="Bad request",
            response=mock_response,
            body=None
        )

        exception_message = "\'API Error received. This usually means the chosen LLM uses an incompatible prompt format. Error message was: Bad request\'"

        with self.assertRaises(gr.Error) as gradio_error:
            list(inference(latest_message, history))
        self.assertEqual(str(gradio_error.exception), exception_message)
        mock_logger.error.assert_called_once_with("Received BadRequestError from backend API: %s", mock_llm.stream.side_effect)

    @patch("app.llm")
    @patch("app.build_chat_context")
    @patch("app.log")
    @patch("app.gr")
    @patch("app.BACKEND_INITIALISED", False)
    def test_inference_APIConnectionError(self, mock_gr, mock_logger, mock_build_chat_context, mock_llm):
        mock_build_chat_context.return_value = ["mock_context"]
        mock_request = Mock()
        mock_request.json.return_value = {"message": "Foo"}

        mock_llm.stream.side_effect = openai.APIConnectionError(
            message="Foo",
            request=mock_request,
        )

        list(inference(latest_message, history))
        mock_logger.info.assert_any_call("Backend API not yet ready")
        mock_gr.Info.assert_any_call("Backend not ready - model may still be initialising - please try again later.")

    @patch("app.llm")
    @patch("app.build_chat_context")
    @patch("app.log")
    @patch("app.gr")
    @patch("app.BACKEND_INITIALISED", True)
    def test_inference_APIConnectionError_initialised(self, mock_gr, mock_logger, mock_build_chat_context, mock_llm):
        mock_build_chat_context.return_value = ["mock_context"]
        mock_request = Mock()
        mock_request.json.return_value = {"message": "Foo"}

        mock_llm.stream.side_effect = openai.APIConnectionError(
            message="Foo",
            request=mock_request,
        )

        list(inference(latest_message, history))
        mock_logger.error.assert_called_once_with("Failed to connect to backend API: %s", mock_llm.stream.side_effect)
        mock_gr.Warning.assert_any_call("Failed to connect to backend API.")

    @patch("app.llm")
    @patch("app.build_chat_context")
    @patch("app.gr")
    def test_inference_InternalServerError(self, mock_gr, mock_build_chat_context, mock_llm):
        mock_build_chat_context.return_value = ["mock_context"]
        mock_request = Mock()
        mock_request.json.return_value = {"message": "Foo"}

        mock_llm.stream.side_effect = openai.InternalServerError(
            message="Foo",
            response=mock_request,
            body=None
        )

        list(inference(latest_message, history))
        mock_gr.Warning.assert_any_call("Internal server error encountered in backend API - see API logs for details.")

if __name__ == "__main__":
    unittest.main(verbosity=2)
