---
name: llms-txt
description: Discover markdown versions of documentation on websites via /llms.txt. Use whenever asked to read documentation or explore an API reference — especially for AI tooling sites.
compatibility: Requires internet access
allowed-tools: WebFetch
---

## What is llms.txt

`/llms.txt` is a standard where sites publish a concise, LLM-optimised markdown overview of their docs at `{origin}/llms.txt`.

## Steps

1. Extract the origin from the target URL (e.g. `https://docs.example.com`)
2. Fetch `{origin}/llms.txt`
3. If found (200 OK, markdown content): read it to understand the docs structure, then fetch specific pages listed there as needed
4. If not found or returns HTML/404: fall back to fetching the original URL directly
5. Optionally try `{origin}/llms-full.txt` if you need complete content and `llms.txt` only lists links

## Known sites with llms.txt
- Anthropic/Claude: https://platform.claude.com/llms.txt
- Gemini CLI: https://geminicli.com/llms.txt
- GitHub Copilot CLI: https://docs.github.com/en/copilot.md
- OpenAI: https://developers.openai.com/llms.txt
- GitHub: https://docs.github.com/llms.txt
- Gas City: https://docs.gascityhall.com/llms.txt

## Notes

- `llms.txt` often contains a map of all pages — prefer it over sitemap.xml or nav crawling
- Some sites host docs on a subdomain (`docs.example.com`) — use that origin, not the root domain
