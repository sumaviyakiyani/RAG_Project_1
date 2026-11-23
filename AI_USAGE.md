# AI usage

| Item | Details |
|---|---|
| AI tool used for building | Claude (Anthropic) in the Claude web/app chat |
| Model | Claude Sonnet 5.5 |
| Runtime LLM in the project | Groq-hosted open model set in `.env` (`LLM_MODEL`); fill in the exact name you used |
| Embedding model | sentence-transformers/all-MiniLM-L6-v2 (local) |
| Configuration | temperature 0, max_tokens 600, timeout 30 s, 2 retries |

## How AI assistance was used
Claude generated the initial project structure, code, tests, frontend and documentation from the instructor
requirements. The student must read and be able to explain every file, run the tests and evaluation themselves,
and record any changes they make.

## Prompts used
1. The master prompt (full text of the project requirements) - paste it here.
2. "Everything is installed u just make me project"
3. Add every later prompt here, with the date.

## Conversation history
Export or copy the full Claude conversation into `docs/conversation_history.md` and commit it, as the instructor requires.
