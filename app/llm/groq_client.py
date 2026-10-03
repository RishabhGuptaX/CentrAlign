import os
from typing import Optional

from dotenv import load_dotenv
from groq import Groq


load_dotenv()


class GroqClient:
    """
    Centralized Groq API client for CentrAlign AI.

    This class is the only component that communicates directly
    with the Groq API.

    The rest of the application will use this abstraction for:
    - task understanding
    - planning
    - tool selection
    - agent decisions
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.api_key = api_key or os.getenv("GROQ_API_KEY")

        self.model = model or os.getenv(
            "GROQ_MODEL",
            "openai/gpt-oss-20b",
        )

        if not self.api_key:
            raise ValueError(
                "GROQ_API_KEY is missing. "
                "Add your Groq API key to the .env file."
            )

        self.client = Groq(
            api_key=self.api_key
        )

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.6,
        max_completion_tokens: int = 1024,
        reasoning_effort: str = "low",
    ) -> str:
        """
        Generate a response from Groq.

        GPT-OSS is a reasoning model. We explicitly disable returning
        reasoning content to the application because the application
        only needs the final answer.
        """

        messages = []

        if system_prompt:
            messages.append(
                {
                    "role": "system",
                    "content": system_prompt,
                }
            )

        messages.append(
            {
                "role": "user",
                "content": prompt,
            }
        )

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_completion_tokens=max_completion_tokens,
                reasoning_effort=reasoning_effort,
                include_reasoning=False,
            )

            if not response.choices:
                raise RuntimeError(
                    "Groq returned no response choices."
                )

            message = response.choices[0].message

            content = message.content

            if content:
                return content.strip()

            # Helpful diagnostic if Groq returns no visible content.
            reasoning = getattr(
                message,
                "reasoning",
                None,
            )

            if reasoning:
                return reasoning.strip()

            raise RuntimeError(
                "Groq returned a response, but both content "
                "and reasoning were empty."
            )

        except Exception as exc:

            raise RuntimeError(
                f"Groq API request failed: {exc}"
            ) from exc

    def health_check(self) -> bool:
        """
        Verify that Groq is reachable and returning usable output.
        """

        response = self.generate(
            prompt=(
                "Reply with exactly this text and nothing else: "
                "GROQ_OK"
            ),
            temperature=0,
            max_completion_tokens=32,
            reasoning_effort="low",
        )

        return response.strip() == "GROQ_OK"


if __name__ == "__main__":

    print("=" * 65)
    print("CentrAlign AI - Groq Connection Test")
    print("=" * 65)

    try:

        client = GroqClient()

        print()
        print(f"Model: {client.model}")

        print()
        print("Sending test request...")

        response = client.generate(
            prompt=(
                "Reply with exactly this text and nothing else: "
                "GROQ_CONNECTION_SUCCESS"
            ),
            temperature=0,
            max_completion_tokens=32,
            reasoning_effort="low",
        )

        print()
        print(f"Response: {response}")

        print()
        print("Running health check...")

        healthy = client.health_check()

        print()
        print(f"Health check: {healthy}")

        if healthy:
            print()
            print("=" * 65)
            print("SUCCESS: Groq connection is working.")
            print("=" * 65)

        else:
            print()
            print("=" * 65)
            print("ERROR: Groq health check failed.")
            print("=" * 65)

    except Exception as exc:

        print()
        print("=" * 65)
        print("GROQ TEST FAILED")
        print("=" * 65)

        print()
        print(str(exc))
