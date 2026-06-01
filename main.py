from src.agent.browser.config import BrowserConfig
from src.agent import Agent
from src.agent.events.json_subscriber import JSONEventSubscriber
from dotenv import load_dotenv
from datetime import datetime
from pathlib import Path
import csv
import os

load_dotenv()

# Read potential Google API key early (may be used later)
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY') or os.getenv('GOOGLE_AISTUDIO_API_KEY')

# Prefer Ollama provider if an OLLAMA_MODEL is set
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL')

if OLLAMA_MODEL:
	from src.providers.ollama import ChatOllama

	ollama_host = os.getenv('OLLAMA_HOST')
	llm = ChatOllama(model=OLLAMA_MODEL, host=ollama_host)
else:
	GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY') or os.getenv('GOOGLE_AISTUDIO_API_KEY')
	if GOOGLE_API_KEY:
		from src.providers.google import ChatGoogle

		llm = ChatGoogle(model='gemini-2.5-flash', api_key=GOOGLE_API_KEY)
	else:
		from src.providers.mistral import ChatMistral

		llm = ChatMistral(model='mistral-large-2512')

# Browser selection: allow overriding with BROWSER env var (edge/chrome)
browser_env = (os.getenv('BROWSER') or '').lower()
if browser_env in ('edge', 'msedge', 'microsoft-edge'):
	browser_name = 'edge'
elif browser_env in ('chrome', 'google-chrome'):
	browser_name = 'chrome'
else:
	browser_name = None

config = BrowserConfig(browser=browser_name, headless=False)

# Pass sensitive data so it can be redacted in logs/messages
sensitive = {}
if GOOGLE_API_KEY:
	sensitive['GOOGLE_API_KEY'] = GOOGLE_API_KEY

agent = Agent(
    config=config,
    llm=llm,
    use_vision=False,
    use_web_mcp=True,
    max_steps=100,
    keep_alive=True,
    log_to_file=True,
    sensitive_data=sensitive,
)

# Optional: record events to JSON for replay/inspection
record_dir_env = os.getenv('RECORD_DIR') or os.getenv('RECORD_JSON_PATH') or os.getenv('RECORD_EVENTS_JSON')
record_path = None
record_filename = None
csv_map_path = None
if record_dir_env:
	record_candidate = Path(record_dir_env)
	if record_candidate.suffix.lower() == '.json' and not record_dir_env.endswith(('/', '\\')):
		record_path = record_candidate
		record_filename = record_path.name
		record_path.parent.mkdir(parents=True, exist_ok=True)
		csv_map_path = record_path.parent / 'query_map.csv'
	else:
		record_dir = record_candidate
		record_dir.mkdir(parents=True, exist_ok=True)
		ts = datetime.now().strftime('%Y%m%d_%H%M%S')
		record_filename = f'web-use-record_{ts}.json'
		record_path = record_dir / record_filename
		csv_map_path = record_dir / 'query_map.csv'

if record_path:
	agent.event.add_subscriber(JSONEventSubscriber(record_path))

user_query = input('Enter your query: ')
if csv_map_path and record_filename:
	csv_map_path.parent.mkdir(parents=True, exist_ok=True)
	write_header = not csv_map_path.exists()
	with csv_map_path.open('a', newline='', encoding='utf-8') as csvfile:
		writer = csv.writer(csvfile)
		if write_header:
			writer.writerow(['timestamp', 'query', 'record_file'])
		writer.writerow([datetime.now().isoformat(), user_query, record_filename])

agent.print_response(user_query)