# RSV POC Website + Dual-Mode Chatbot

This Streamlit proof of concept demonstrates a dual-mode RSV chatbot (guided + free-text) powered by a data-driven response bank. The application ships with seven content pages plus the home page, deep links between sections, and OpenAI-based intent classification for free-text mode.

## Features
- **Seven-page POC** with top navigation and deep links
- **Chatbot on every page** with guided and free-text modes
- **Data-driven** response bank (`data/response_bank.json`) and intent-to-page mapping (`data/intent_to_page_map.json`)
- **Structured intent classification** with OpenAI Responses API and Pydantic schema
- **Safe defaults** when `OPENAI_API_KEY` is missing (guided mode remains available)

## Setup
1. Install Python 3.10+.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. (Optional) Add your OpenAI API key to enable free-text classification:
   ```bash
   export OPENAI_API_KEY="sk-..."
   ```

## Run
Launch Streamlit from the repository root:
```bash
streamlit run app.py
```

The app starts on the home page and exposes navigation links to all additional pages under `pages/`.

## How it works
- `components/response_bank.py` loads the response bank and intent-to-page mappings.
- `components/intent_classifier.py` wraps the OpenAI Responses API with a structured output schema and a confidence threshold. Hard-rule overrides route obvious emergency phrases to the `urgent_support` intent.
- `components/chatbot_widget.py` renders the shared chatbot widget with guided and free-text modes, deep links, and next-best-question prompts.
- `components/navigation.py` renders the top navigation bar on every page.

Free-text mode strictly classifies the user's message to an approved intent and replies with the response bank content for that intent; it never generates new medical advice.
