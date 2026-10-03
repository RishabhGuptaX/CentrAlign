from app.llm.groq_client import GroqClient


def test_groq_client_initialization():
    client = GroqClient()

    assert client.client is not None
    assert client.model


if __name__ == "__main__":
    print("Groq client initialization test passed.")
