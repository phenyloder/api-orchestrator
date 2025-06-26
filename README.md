# API Orchestrator

An intelligent API orchestration service that automatically chains API calls based on natural language queries.

## Features

- 🤖 Natural language query processing using LLMs
- 🔗 Automatic API dependency resolution
- 📋 Intelligent execution planning
- 🔄 Support for complex multi-step workflows
- 📖 OpenAPI/Swagger specification parsing
- ⚡ Minimal LLM hallucination through structured prompts
- 🔧 Built with FastAPI and LangChain

## Quick Start

### Prerequisites
- Docker and Docker Compose
- OpenAI API key

### Setup

1. Clone/create the project:
   ```bash
   python create_api_orchestrator.py
   cd api-orchestrator
```

## Poetry Dependency Management

This project uses [Poetry](https://python-poetry.org/) for dependency management.

### Common Commands

- **Install dependencies:**
  ```sh
  poetry install
  ```
- **Add a new dependency:**
  ```sh
  poetry add <package-name>
  ```
- **Run the app inside Poetry shell:**
  ```sh
  poetry shell
  python app/main.py
  ```
- **Run tests:**
  ```sh
  poetry run pytest
  ```
