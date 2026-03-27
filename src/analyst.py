"""Claude-powered security analyst — sends Zscaler data to Claude for analysis."""

import json
import anthropic

SYSTEM_PROMPT = """You are a senior network security analyst specializing in Zscaler Zero Trust architecture.

When analyzing data:
- Lead with the most critical findings
- Be specific: reference actual rule names, app names, policy IDs from the data
- Give actionable remediation steps, not generic advice
- Flag compliance risks (PCI, HIPAA, SOC2) where relevant
- Keep summaries concise — use bullet points for findings

Your audience is a Network Security Lead who knows Zscaler well."""


class ZscalerAnalyst:
    def __init__(self, api_key: str):
        self.client = anthropic.Anthropic(api_key=api_key)

    def analyze(self, data, question: str, *, stream: bool = True) -> str:
        payload = json.dumps(data, indent=2)

        # Warn if payload is large
        tokens_estimate = len(payload) // 4
        if tokens_estimate > 50_000:
            print(f"  [!] Large payload (~{tokens_estimate:,} est. tokens) — consider filtering first")

        messages = [{
            "role": "user",
            "content": f"## Zscaler Data\n```json\n{payload}\n```\n\n## Question\n{question}",
        }]

        if stream:
            return self._stream(messages)
        else:
            resp = self.client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                messages=messages,
            )
            return resp.content[0].text

    def _stream(self, messages: list) -> str:
        full_text = ""
        with self.client.messages.stream(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=messages,
        ) as stream:
            for text in stream.text_stream:
                print(text, end="", flush=True)
                full_text += text
        print()  # newline after stream ends
        return full_text
