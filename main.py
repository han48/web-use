from src.agent.browser.config import BrowserConfig
from src.providers.mistral import ChatMistral
from src.agent import Agent
from dotenv import load_dotenv
import os

load_dotenv()

llm = ChatMistral(model='mistral-large-2512')
config = BrowserConfig(browser='chrome', headless=False)
agent = Agent(config=config, llm=llm, use_vision=False, use_web_mcp=True, max_steps=100, keep_alive=True)

user_query = input('Enter your query: ')
agent.print_response(user_query)