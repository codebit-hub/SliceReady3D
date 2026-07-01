import os
import sys
from typing import Dict, Any

import requests  # type: ignore
from dotenv import load_dotenv  # type: ignore


def test_huggingface_api(prompt: str, output_file: str) -> None:
    """
    Tests the Hugging Face Inference API for text-to-image generation.
    Loads credentials safely from a local .env file.
    """
    # Load environment variables from the .env file in the root directory
    load_dotenv()

    # Searching for the specific variable name you set in your file
    token: str | None = os.getenv("HF_API_TOKEN")
    if not token:
        print("Error: HF_API_TOKEN was not found.")
        print("Please ensure your .env file is in the same directory.")
        sys.exit(1)

    api_url: str = (
        "https://api-inference.huggingface.co/models/"
        "stabilityai/stable-diffusion-xl-base-1.0"
    )

    headers: Dict[str, str] = {"Authorization": f"Bearer {token}"}
    payload: Dict[str, Any] = {"inputs": prompt}

    print(f"Targeting: {api_url}")
    print(f"Prompt: '{prompt}'")
    print("Sending request... (If the model is sleeping, this may take 2-3 mins)")

    try:
        # 180-second timeout to survive the dreaded "cold start"
        response = requests.post(
            api_url,
            headers=headers,
            json=payload,
            timeout=180
        )

        if response.status_code == 200:
            with open(output_file, "wb") as f:
                f.write(response.content)
            print(f"\nSuccess! Image saved to {output_file}")
        elif response.status_code == 503:
            print("\nError 503: The model is currently loading.")
            print(f"API Response: {response.json()}")
            print("Wait a minute and run the script again.")
        else:
            print(f"\nFailed with status code: {response.status_code}")
            print(f"Response: {response.text}")

    except requests.exceptions.Timeout:
        print("\nError: The request timed out.")
        print("The model is likely still loading into VRAM on the server.")
        print("Try running the script one more time.")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")


if __name__ == "__main__":
    test_prompt: str = (
        "A cute yellow duck built out of plastic bricks, "
        "sitting on a wooden table, high quality photography"
    )
    test_huggingface_api(test_prompt, "test_duck.png")
