# Æon Framework - Real-World Examples

This directory contains **production-ready examples** of Æon Framework agents with real integrations and MCP servers.

## Quick Start Examples

### 1. Simple Chat Agents

- **[simple_chat_ollama.py](simple_chat_ollama.py)** - Local chat with Ollama
- **[simple_chat_openai.py](simple_chat_openai.py)** - OpenAI GPT-4o
- **[simple_chat_openrouter.py](simple_chat_openrouter.py)** - OpenRouter multi-model

### 2. Integration Examples

- **[telegram_bot.py](telegram_bot.py)** - Telegram messaging
- **[discord_bot.py](discord_bot.py)** - Discord integration
- **[slack_bot.py](slack_bot.py)** - Slack workspace bot
- **[multi_platform_bot.py](multi_platform_bot.py)** - Support 3+ platforms simultaneously

### 3. Real-World Applications

- **[journal_assistant.py](journal_assistant.py)** - Personal journal with AI review
- **[customer_support_bot.py](customer_support_bot.py)** - Multi-channel support bot
- **[research_assistant.py](research_assistant.py)** - Research with web search

### 4. Advanced Features

- **[with_mcp_weather.py](with_mcp_weather.py)** - Weather data via MCP
- **[with_mcp_search.py](with_mcp_search.py)** - Web search via Brave Search MCP
- **[with_mcp_database.py](with_mcp_database.py)** - SQLite database access
- **[with_safety_axioms.py](with_safety_axioms.py)** - Safety rules enforcement
- **[with_capabilities.py](with_capabilities.py)** - Custom capabilities system
- **[async_operations.py](async_operations.py)** - Non-blocking execution
- **[scheduling_tasks.py](scheduling_tasks.py)** - Temporal task scheduling

### 5. MCP Servers Integration

- **[mcp_tools_integration.py](mcp_tools_integration.py)** - Generic MCP server setup
- **[mcp_youtube_extractor.py](mcp_youtube_extractor.py)** - YouTube transcripts
- **[mcp_google_maps.py](mcp_google_maps.py)** - Location & directions
- **[mcp_puppeteer_scraper.py](mcp_puppeteer_scraper.py)** - Web scraping
- **[mcp_kubernetes_monitor.py](mcp_kubernetes_monitor.py)** - K8s cluster monitoring

## Setup Instructions

### Prerequisites

```bash
# Install Æon Framework
pip install aeon-core

# Install dependencies for examples
pip install -r requirements.txt

# Install Ollama (optional, for local models)
brew install ollama
ollama pull phi3.5
```

### Environment Variables

```bash
# LLM Providers
export OPENAI_API_KEY="sk-..."
export OPENROUTER_API_KEY="sk-or-..."
export AWS_ACCESS_KEY_ID="AKIA..."
export AWS_SECRET_ACCESS_KEY="..."

# Integrations
export TELEGRAM_BOT_TOKEN="123456:ABC..."
export DISCORD_BOT_TOKEN="..."
export SLACK_BOT_TOKEN="xoxb-..."

# MCP Servers
export BRAVE_SEARCH_API_KEY="..."
export GOOGLE_MAPS_API_KEY="..."
export YOUTUBE_API_KEY="..."
```

## Running Examples

### Local Chat (Fastest)
```bash
python simple_chat_ollama.py
```

### With OpenAI
```bash
python simple_chat_openai.py
```

### Telegram Bot
```bash
export TELEGRAM_BOT_TOKEN="your_token_here"
python telegram_bot.py
```

### Multi-Channel Support
```bash
python multi_platform_bot.py
```

### With MCP Weather
```bash
python with_mcp_weather.py
```

## MCP Servers Used

| MCP Server | Purpose | Category |
|-----------|---------|----------|
| [Brave Search](https://mcpserverhub.com/servers/brave-search) | Web search | Search |
| [Google Maps](https://mcpserverhub.com/servers/google-maps) | Location & directions | Location |
| [Puppeteer](https://mcpserverhub.com/servers/puppeteer) | Web scraping | Automation |
| [SQLite](https://mcpserverhub.com/servers/sqlite) | Database access | Storage |
| [YouTube Data](https://mcpserverhub.com/servers/serpapi-youtube) | Video transcripts | Media |
| [Metoro](https://mcpserverhub.com/servers/metoro) | Kubernetes monitoring | Cloud |
| [Sentry](https://mcpserverhub.com/servers/sentry) | Error tracking | Monitoring |
| [Time](https://mcpserverhub.com/servers/time) | Time & timezone | Utility |
| [Sequential Thinking](https://mcpserverhub.com/servers/sequentialthinking) | Structured reasoning | Agent |
| [Fetch](https://mcpserverhub.com/servers/fetch) | HTTP requests | API |

## Architecture Pattern

```
Your Agent
    ├── Cortex (LLM Reasoning)
    ├── Executive (Safety Rules/Axioms)
    ├── Synapse (MCP Tools)
    ├── Integrations (Multi-Platform)
    ├── Dialogue (Conversation Management)
    ├── Dispatcher (Event Handling)
    ├── Automation (Scheduling)
    └── Cache (Performance)
```

## Example Templates

### Minimal Agent (10 lines)
```python
from aeon import Agent

agent = Agent(
    name="MyBot",
    model_provider="ollama",
    model_name="phi3.5"
)
```

### Production Agent (with all features)
- See [customer_support_bot.py](customer_support_bot.py)

## Development Tips

1. **Start Local** - Use Ollama for development, migrate to cloud for production
2. **Enable Logging** - Add `logging.basicConfig(level=logging.DEBUG)`
3. **Test Integrations** - Start with one platform before adding more
4. **Monitor Costs** - Use the Economics subsystem to track spending
5. **Version Lock** - Pin package versions in `requirements.txt`

## Troubleshooting

### "Model not found"
```bash
ollama list  # For Ollama
```

### "API key invalid"
```bash
echo $OPENAI_API_KEY  # Verify it's set
```

### Agent not responding
```bash
# Test connectivity
curl http://localhost:11434/api/tags  # Ollama
```

## Next Steps

1. **Learn Æon Architecture** - Read [ARCHITECTURE.md](../ARCHITECTURE.md)
2. **Explore MCP Hub** - Visit https://mcpserverhub.com
3. **Join Community** - Share your own examples
4. **Deploy to Production** - Use the deployment guides

## License

Same as Æon Framework - Apache 2.0
