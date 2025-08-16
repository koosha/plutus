# Plutus - Wealth Building Coach Brain

A multiagent system using LangGraph and Claude API for providing personalized financial advice and wealth building guidance.

## Overview

Plutus serves as the intelligent backend for a wealth building coaching application. It uses a multiagent architecture to:

- Analyze user financial data from connected accounts
- Understand user goals and preferences through conversations
- Provide personalized financial advice and strategies
- Learn and adapt to user behavior over time

## Architecture

- **Multiagent System**: Built with LangGraph for complex decision workflows
- **AI Integration**: Claude API for advanced reasoning and financial analysis
- **Data Processing**: Pandas and NumPy for financial data analysis
- **Database**: SQLAlchemy with support for various databases
- **API**: FastAPI for serving the wealth coaching engine

## Setup

1. Create and activate virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Copy and configure environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and configuration
   ```

4. Run the application:
   ```bash
   uvicorn src.main:app --reload
   ```

## Development

- **Code formatting**: `black src tests`
- **Linting**: `ruff check src tests`
- **Type checking**: `mypy src`
- **Testing**: `pytest tests/`

## Project Structure

```
src/
├── agents/         # LangGraph agent definitions
├── core/          # Core business logic and configurations
├── models/        # Data models and schemas
├── services/      # External service integrations
└── utils/         # Utility functions and helpers
tests/             # Test files
docs/              # Documentation
```