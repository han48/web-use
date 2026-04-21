<div align="center">

  <h1>🌐 Web-Use</h1>

  <a href="https://github.com/Jeomon/Web-Agent/blob/main/LICENSE">
    <img src="https://img.shields.io/badge/license-MIT-green" alt="License">
  </a>
  <img src="https://img.shields.io/badge/python-3.12%2B-blue" alt="Python">
  <img src="https://img.shields.io/badge/Powered%20by-CDP-orange" alt="Powered by CDP">
  <br>

  <a href="https://x.com/CursorTouch">
    <img src="https://img.shields.io/badge/follow-%40CursorTouch-1DA1F2?logo=twitter&style=flat" alt="Follow on Twitter">
  </a>
  <a href="https://discord.com/invite/Aue9Yj2VzS">
    <img src="https://img.shields.io/badge/Join%20on-Discord-5865F2?logo=discord&logoColor=white&style=flat" alt="Join us on Discord">
  </a>

</div>

<br>

**Web-Use** is an intelligent autonomous browsing agent, built to seamlessly navigate websites, interact with dynamic content, perform smart searches, download files, and adapt to ever-changing pages — all with minimal effort from you. Powered by advanced LLMs and the Chrome DevTools Protocol, it transforms complex web tasks into streamlined, automated workflows that boost productivity and save time.

## ✨Key Features

- **🤖 Autonomous Web Navigation** — Navigate websites, fill forms, and interact with dynamic content without manual intervention
- **🛠️ Multi-LLM Support** — Works with Anthropic Claude, Google Gemini, OpenAI, Groq, Ollama, Cerebras, Mistral, and more
- **📸 Vision Capability** — Understands visual content on pages for better decision-making
- **🔗 Web Model Context Protocol (WebMCP)** — Discovers and uses custom tools exposed by websites, enabling context-aware interactions
- **⚡ Efficient Element Interaction** — Indexed DOM elements for fast, accurate clicking and typing
- **📥 File Operations** — Download files and upload content to forms
- **🔄 State Awareness** — Maintains understanding of page state to avoid loops and recover from errors
- **⏱️ Intelligent Waiting** — Handles loading states, animations, and user interactions (CAPTCHA, OTP)

## 🌐 Web Model Context Protocol (WebMCP)

Web-Use supports **WebMCP**, a protocol that allows websites to expose custom tools and capabilities directly to the agent. When visiting a website with WebMCP support:

- **Auto-Discovery** — The agent automatically detects available tools
- **Dynamic Registration** — Tools are added to the agent's toolkit on-the-fly
- **Full Integration** — WebMCP tools appear in the browser state with complete schema information
- **Seamless Execution** — Tools are called like built-in tools with proper parameter validation

### Example

If you visit a documentation site that supports WebMCP with a `search_docs` tool:

```
**WebMCP Tools Available:**
**search_docs** — Search documentation
  - `query` (string) [✓ required]
  - `limit` (integer) [○ optional]
```

The agent will automatically use this tool when relevant to the task.

Enable WebMCP support:
```python
agent = Agent(
    config=config,
    llm=llm,
    use_web_mcp=True,  # Enable WebMCP discovery
    max_steps=100
)
```

## 🛠️Installation Guide

### **Prerequisites**

- Python 3.11 or higher
- UV

### **Installation Steps**

**Clone the repository:**

```bash
git clone https://github.com/CursorTouch/Web-Use.git
cd Web-Use
```

**Install dependencies:**

```bash
uv sync
```

**Launch Chrome with remote debugging:**

```bash
chrome --remote-debugging-port=9222
```

---

**Setting up the `.env` file:**

```bash
GOOGLE_API_KEY="<API_KEY_HERE>"
```

**Basic Setup:**

```python
from src.agent.browser.config import BrowserConfig
from src.providers.ollama import ChatOllama
from src.agent import Agent
from dotenv import load_dotenv

load_dotenv()

# Initialize LLM
llm = ChatOllama(model='qwen3.5:397b-cloud', temperature=0.5)

# Configure browser
config = BrowserConfig(
    browser='chrome',
    headless=False,
    use_system_profile=True
)

# Create agent with WebMCP support
agent = Agent(
    config=config,
    llm=llm,
    use_vision=False,
    use_web_mcp=True,  # Enable WebMCP for website tools
    max_steps=100
)

# Run agent
user_query = input('Enter your query: ')
agent.print_response(user_query)
```

**Execute:**

```bash
uv run main.py
```

## ⚙️Configuration Options

### Agent Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `config` | BrowserConfig | Required | Browser configuration (headless, profile, etc.) |
| `llm` | BaseChatLLM | Required | Language model to use for reasoning |
| `use_vision` | bool | False | Enable screenshot-based visual understanding |
| `use_web_mcp` | bool | False | **NEW:** Enable Web Model Context Protocol to discover website tools |
| `max_steps` | int | 25 | Maximum number of actions before timeout |
| `max_consecutive_failures` | int | 3 | Retry limit for failed tool calls |
| `include_human_in_loop` | bool | False | Allow pausing for human input |
| `keep_alive` | bool | False | Keep browser open after task completion |

### Browser Configuration

```python
config = BrowserConfig(
    browser='chrome',              # 'chrome' or 'edge'
    headless=False,                # Run in headless mode
    use_system_profile=True,       # Use real browser profile with auth
    user_data_dir='/path/to/profile',  # Custom profile directory
    cdp_port=9222,                 # Chrome DevTools Protocol port
    downloads_dir='/Downloads',    # Where to save files
    attach_to_existing=False,      # Connect to running browser
    update_cdp=False,              # Regenerate CDP protocol files
)
```

## 🎥Demos

**Prompt:** I want to know the price details of the RTX 4060 laptop gpu from varrious sellers from amazon.in

https://github.com/user-attachments/assets/c729dda9-0ecc-4b07-9113-62fddccca52f

**Prompt:** Make a twitter post about AI on X

https://github.com/user-attachments/assets/126ef697-f506-4630-9a0a-1dbbfead9f7e

**Prompt:** Can you play the trailer of GTA 6 on youtube

https://github.com/user-attachments/assets/7abde708-7fe0-46f8-96ac-16124aaf2ef4

**Prompt:** Can you go to my github account and visit the Windows MCP

https://github.com/user-attachments/assets/cb8ad60c-0609-42e3-9fb9-584ad77c4e3a

---

## 🪪License

This project is licensed under MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝Contributing

Contributions are welcome! Please see [CONTRIBUTING](CONTRIBUTING.md) for setup instructions and development guidelines.

Made with ❤️ by [Jeomon George](https://github.com/Jeomon), [Muhammad Yaseen](https://github.com/mhmdyaseen)

---

## 📒References

- **[Chrome DevTools Protocol](https://chromedevtools.github.io/devtools-protocol/)**  
- **[LangGraph Examples](https://github.com/langchain-ai/langgraph/blob/main/examples/web-navigation/web_voyager.ipynb)**  
- **[vimGPT](https://github.com/ishan0102/vimGPT)**  
- **[WebVoyager](https://github.com/MinorJerry/WebVoyager)**  
