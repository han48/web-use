from src.agent.browser.config import BrowserConfig
from src.providers.ollama import ChatOllama
from src.agent import Agent
from dotenv import load_dotenv
import os

load_dotenv()

llm = ChatOllama(model='qwen3.5:397b-cloud', temperature=0.5)
config = BrowserConfig(browser='edge', headless=False,use_system_profile=True)
agent = Agent(config=config, llm=llm, use_vision=False, max_steps=100,)

user_query = input('Enter your query: ')
agent.print_response(user_query)