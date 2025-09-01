import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

import pytest
from unittest.mock import patch, MagicMock, Mock
from src.llm_agent import LLMAgent
import json


def test_llm_agent_initialization():
    """Test that the LLMAgent initializes correctly."""
    agent = LLMAgent()
    assert agent.name == "llm"
    assert agent.version == "llm-local-1.1"
    assert agent.n_ctx == 4096
    assert agent.gpu_only is True
    assert abs(agent.temperature - 0.2) < 1e-9
    assert abs(agent.top_p - 0.95) < 1e-9
    assert agent.max_tokens == 512


@patch.dict(os.environ, {"ORBITSUITE_LLM_SERVER_URL": "http://172.23.80.1:8080"})
def test_llm_agent_run_with_empty_prompt() -> None:
    """Test that the LLMAgent handles empty input correctly."""
    agent = LLMAgent()
    
    # Test with empty string - this should be caught before hitting the server
    result = agent.run("")
    assert not result["success"]
    assert "error" in result
    assert "empty" in result["error"].lower()
    
    # Test with empty dict - this should also be caught before hitting the server
    result = agent.run({})
    assert not result["success"] 
    assert "error" in result
    assert "empty" in result["error"].lower()


@patch.dict(os.environ, {"ORBITSUITE_LLM_SERVER_URL": "http://172.23.80.1:8080"})
@patch('urllib.request.urlopen')
def test_llm_agent_run_with_reset(mock_urlopen: MagicMock) -> None:
    """Test that the LLMAgent resets conversation state when reset is True."""
    # Mock the HTTP response
    mock_response = Mock()
    mock_response.read.return_value = json.dumps({
        "choices": [{"message": {"content": "New response"}}],
        "usage": {"total_tokens": 10}
    }).encode('utf-8')
    mock_urlopen.return_value.__enter__.return_value = mock_response
    
    agent = LLMAgent()
    
    # First message to establish conversation history
    result1 = agent.run({"prompt": "First message"})
    assert result1["success"]
    
    # Reset conversation and send new message
    result2 = agent.run({"prompt": "New message", "reset": True})
    assert result2["success"]
    assert result2["output"] == "New response"
    # After reset, should only have system (if any) + user + assistant
    assert len(result2["messages"]) <= 3


@patch.dict(os.environ, {"ORBITSUITE_LLM_SERVER_URL": "http://172.23.80.1:8080"})
@patch('urllib.request.urlopen')
def test_llm_agent_run_with_messages(mock_urlopen: MagicMock) -> None:
    """Test retrieving messages through the run method."""
    # Mock the HTTP response
    mock_response = Mock()
    mock_response.read.return_value = json.dumps({
        "choices": [{"message": {"content": "Test response"}}],
        "usage": {"total_tokens": 10}
    }).encode('utf-8')
    mock_urlopen.return_value.__enter__.return_value = mock_response
    
    agent = LLMAgent()
    
    # Send first message
    result1 = agent.run("First message")
    assert result1["success"]
    
    # Send second message and check conversation history
    result2 = agent.run("Second message")
    assert result2["success"]
    assert len(result2["messages"]) > 0
    
    # Should contain both user messages in conversation history
    message_contents = [msg["content"] for msg in result2["messages"]]
    assert "Second message" in message_contents


def test_llm_agent_run_with_server_url():
    """Test that the LLMAgent uses the server backend when server_url is configured."""
    agent = LLMAgent()
    agent.server_url = "http://127.0.0.1:8080"
    
    with patch.object(agent, '_server_chat_completion') as mock_server:
        mock_server.return_value = ("Server response", {"total_tokens": 10})
        
        result = agent.run("Test prompt")
        assert result["success"]
        assert result["output"] == "Server response"
        mock_server.assert_called_once()


def test_llm_agent_load_model_missing_path():
    """Test that the LLMAgent raises an error when model_path is missing and no server."""
    # Test without server URL - should fail when trying to load local model with no path
    agent = LLMAgent(model_path=None)
    
    # This should raise a RuntimeError, either for model_path or llama-cpp-python
    with pytest.raises(RuntimeError):
        agent.run("Test prompt")


def test_llm_agent_load_model_invalid_path():
    """Test that the LLMAgent raises an error when model_path is invalid and no server."""
    agent = LLMAgent(model_path="invalid/path/to/model")
    with pytest.raises(FileNotFoundError, match="model not found"):
        agent.run("Test prompt")
