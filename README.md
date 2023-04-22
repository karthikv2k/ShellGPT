# ShellGPT

ShellGPT is an AI-powered command-line interface (CLI) that generates and executes commands based on user input. It utilizes OpenAI's GPT-4 language model to understand the user's query and generate appropriate commands. ShellGPT also supports real-time command output, making it an interactive and user-friendly tool.

## Features

- Generates commands based on user input
- Executes the generated commands
- Prints real-time command output
- Provides an interactive command-line interface
- Utilizes OpenAI's GPT-4 language model

## Requirements

### OpenAI Access
- You need to have access to GPT4 API access (not ChatGPT Plus). You can use GPT3.5-Turbo model (`--model gpt-3.5-turbo` flag) but the experience will be very degraded.

### Python
- Python 3.6 or later
- `openai` Python package
- `prompt_toolkit` Python package
- `PyYAML` Python package

## Setup

1. Install the required Python packages:

```bash
pip install openai prompt_toolkit PyYAML
```

2. Obtain an API key from OpenAI and set it as an environment variable:

```bash
export OPENAI_API_KEY="your_api_key_here"
```

## Usage

1. Run the ShellGPT script:

```bash
python shellgpt.py
```

2. Type a task or question and press Enter. ShellGPT will suggest a command to execute.

3. The suggested command will be displayed, and you can either modify it or press Enter to execute it.

4. The real-time output of the command will be displayed.

5. To exit ShellGPT, type `exit` and press Enter.

## Example
![](https://raw.githubusercontent.com/karthikv2k/ShellGPT/main/screenshot.jpg)

```
Welcome to ShellGPT! Type your tasks or questions, and ShellGPT will suggest commands to execute.
Type what you want to acieve, and press Enter. Then ShellGPT will ask you to confirm the command it generated.
You can optionally modify the command, and press Enter to execute it.
CTL+C can be used to cancel the current command.
To exit, type 'exit' and press Enter.
> show my cloud run services
Ah, I see you're a Google Cloud Run user! Execute 'gcloud run services list' to show your Cloud Run services.
cmd> gcloud run services list
   SERVICE  REGION       URL                                   LAST DEPLOYED BY      LAST DEPLOYED AT
✔  prod     us-central1  https://prod-**********-uc.a.run.app  ******************  2023-04-11T02:14:50.133955Z
✔  test     us-central1  https://test-**********-uc.a.run.app  ******************  2023-04-11T00:42:37.623346Z
```

## Troubleshooting

- If the script cannot connect to OpenAI's API, ensure that your API key is set as an environment variable.
- If you encounter any issues related to the `openai`, `prompt_toolkit`, or `PyYAML` packages, ensure that they are installed and up-to-date.
