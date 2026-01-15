# JARVIS AI Operating Layer

> A comprehensive, local-first AI assistant with 60+ modules and 100+ tool functions.

## Quick Start

```bash
# 1. Install Ollama and pull model
ollama pull phi3:mini

# 2. Install dependencies
cd jarvis-ai
pip install -r requirements.txt
playwright install  # For browser automation

# 3. Run JARVIS
python main.py --text     # CLI mode
python ui/server.py       # Web UI (http://localhost:8080)
```

## Features

| Category | Features |
|----------|----------|
| **AI** | Local LLM, Speech-to-Text, Text-to-Speech, Wake Word |
| **System** | App control, screenshots, clipboard, media, file sync |
| **Code** | Python interpreter, Git, terminal, code analysis |
| **Web** | Search, browser automation, scraping |
| **Agents** | Multi-step reasoning, planning, research, RAG |
| **Smart Home** | Device control, scenes, automation |
| **Security** | Encryption, auth, password vault |

## Project Structure

```
jarvis-ai/
├── ai/           # LLM, STT, TTS, Wake Word
├── core/         # Agent, Intent, Memory
├── tools/        # System, Web, Code, Productivity, Vision, Automation
├── agents/       # Planning, Execution, Research, Workflow, RAG
├── security/     # Encryption, Auth, Vault
├── integrations/ # API, Webhooks, Smart Home, Notifications, Calendar
├── plugins/      # Plugin system with examples
├── ui/           # FastAPI server + Web frontend
└── main.py
```

## Creating Plugins

```bash
# Create a new plugin template
python -c "from plugins import PluginManager; PluginManager().create_plugin_template('My Plugin')"
```

See `plugins/examples/` for sample plugins (weather, quotes).

## License

MIT
