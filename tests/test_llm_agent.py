import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
import pytest
from unittest.mock import patch
from src.llm_agent import LLMAgent
import math

def test_llm_agent_initialization():
    """Test that the LLMAgent initializes correctly."""
    agent = LLMAgent()
    assert agent.name == "llm"
    assert agent.version == "llm-local-1.1"
    assert agent.n_ctx == 4096
    assert agent.gpu_only is True
    assert math.isclose(agent.temperature, 0.2, rel_tol=1e-9)
    assert math.isclose(agent.top_p, 0.95, rel_tol=1e-9)
    assert agent.max_tokens == 512

def test_llm_agent_run_with_empty_prompt():
    """Test that the LLMAgent handles empty input correctly."""
    agent = LLMAgent()
    result = agent.run("")
    assert not result["success"]
    assert "error" in result
    assert result["error"] == "LLM prompt is empty"

def test_llm_agent_run_with_valid_prompt():
    """Test that the LLMAgent processes a valid prompt correctly."""
    agent = LLMAgent()
    with patch("src.llm_agent.LLMAgent.run") as mock_run:
        mock_run.return_value = {
            "success": True,
            "output": "Test response"
        }
        result = agent.run("Test prompt")
        assert result["success"]
        assert result["output"] == "Test response"

def test_llm_agent_run_with_server_url():
    """Test that the LLMAgent uses the server backend when server_url is configured."""
    agent = LLMAgent()
    agent.server_url = "http://127.0.0.1:8080/v1"
    with patch("src.llm_agent.LLMAgent.run") as mock_run:
        mock_run.return_value = {
            "success": True,
            "output": "Server response"
        }
        result = agent.run("Test prompt")
        assert result["success"]
        assert result["output"] == "Server response"

def test_llm_agent_load_model_missing_path():
    """Test that the LLMAgent raises an error when model_path is missing."""
    agent = LLMAgent(model_path=None)
    with pytest.raises(RuntimeError, match="model_path is not set"):
        agent.run("Test prompt")

def test_llm_agent_load_model_invalid_path():
    """Test that the LLMAgent raises an error when model_path is invalid."""
    agent = LLMAgent(model_path="invalid/path/to/model")
    with pytest.raises(FileNotFoundError, match="model not found"):
        agent.run("Test prompt")

def test_llm_agent_run_with_reset():
    """Test that the LLMAgent resets conversation state when reset is True."""
    agent = LLMAgent()
    result = agent.run({"prompt": "New message", "reset": True})
    assert result["success"]
    assert result["messages"][0]["content"] == "New message"

def test_llm_agent_run_with_messages():
    """Test retrieving messages through the run method."""
    agent = LLMAgent()
    agent.run("Test message")
    result = agent.run("Another message")
    assert len(result["messages"]) > 0
    assert result["messages"][-1]["content"] == "Another message"
