import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from src.llm_agent import LLMAgent
from src.utils import load_dotenv

load_dotenv()

def test_llm_connection():
    try:
        agent = LLMAgent()
        if agent.server_url:
            print(f"Testing connection to server at {agent.server_url}...")
            response = agent.run({"prompt": "Hello, world!"})
            print("Response:", response)
        else:
            print("Server URL is not set in the environment variables.")
    except Exception as e:
        print("Error during connection test:", e)

if __name__ == "__main__":
    test_llm_connection()
