# Promptcraft

This is a simple Flask application with a "Hello, World!" REST API endpoint.

## Setup

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd promptcraft
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install the dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## Running the application

1.  **Run the Flask development server:**
    ```bash
    python app.py
    ```

2.  **Access the endpoint:**
    Open your browser or use a tool like `curl` to access the endpoint:
    ```bash
    curl http://127.0.0.1:5000/
    ```
    You should see the "Hello, World!" message.

## API Usage Examples

All endpoints require the `X-Authorization: admin` header.

### Create a new prompt

```bash
curl -X POST http://127.0.0.1:8000/prompts \\
-H "Content-Type: application/json" \\
-H "X-Authorization: admin" \\
-d '{
    "text": "Write a short story about a robot who discovers music.",
    "intended_use": "Creative writing",
    "target_audience": "Sci-fi readers",
    "expected_outcome": "An engaging short story.",
    "tags": "sci-fi, robot, music"
}'
```

### Get private prompts

```bash
curl -X GET http://127.0.0.1:8000/prompts/private \\
-H "X-Authorization: admin"
```

### Publish a prompt to the shared library

Replace `1` with the ID of the prompt you want to publish.

```bash
curl -X PUT http://127.0.0.1:8000/prompts/1/publish \\
-H "X-Authorization: admin"
```

### Get shared prompts

```bash
curl -X GET http://127.0.0.1:8000/prompts/shared \\
-H "X-Authorization: admin"
```

### Search shared prompts

```bash
curl -X GET "http://127.0.0.1:8000/prompts/shared/search?tags=sci-fi&target_audience=readers" \\
-H "X-Authorization: admin"
```

### Generate content with Gemini

```bash
curl -X POST http://127.0.0.1:8000/prompts/generate \\
-H "Content-Type: application/json" \\
-H "X-Authorization: admin" \\
-d '{"prompt_text": "What is the meaning of life?"}'
```
