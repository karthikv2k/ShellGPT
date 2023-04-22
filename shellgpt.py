import subprocess
import os
import platform
import sys
import threading
from typing import Optional
import openai
import yaml
import logging
from prompt_toolkit import PromptSession
from prompt_toolkit.keys import Keys
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.input.defaults import create_input
from prompt_toolkit.layout.processors import BeforeInput
from pydantic import BaseModel
from pydantic import ValidationError
import argparse

# Read the prompt from the file prompts/self_reflection.txt
with open("sys_prompt.txt", "r") as f:
    SYS_PROMPT = f.read()

context = []


class Color:
    """Color codes for messages."""
    CMD_OUT = "\033[92m"
    CMD_ERR = "\033[91m"
    CLI = "\033[94m"
    END = "\033[0m"


SHELL_PREFIX = "> "


def get_system_info() -> dict:
    """
    Get system information.

    Returns:
        dict: A dictionary containing os_name, os_version, kernel_version, current_shell, and current_user.
    """
    os_name = platform.system()
    os_version = platform.release()

    kernel_version = platform.uname().version

    current_shell = os.environ.get("SHELL", "Unknown")
    current_user = os.environ.get("USER") or os.environ.get("USERNAME", "Unknown")
    return {
        "os_name": os_name,
        "os_version": os_version,
        "kernel_version": kernel_version,
        "current_shell": current_shell,
        "current_user": current_user,
    }


class OpenAIResponse(BaseModel):
    message_to_user: str
    can_generate: bool
    command: Optional[str] = None
    informational_command: bool = False


def send_query_to_openai(prompt: str, model: str) -> OpenAIResponse:
    """
    Send a query to OpenAI API.

    Args:
        prompt (str): The prompt to send to OpenAI API.
        model (str): The model to use for the API.

    Returns:
        OpenAIResponse: The response from the API parsed using the OpenAIResponse Pydantic model.
    """
    response = openai.ChatCompletion.create(
        model=model,
        messages=[
            {"role": "system", "content": SYS_PROMPT},
            {"role": "user", "content": prompt},
        ],
        max_tokens=1000,
        temperature=0.7,
    )
    logging.debug(f"OpenAI API response: {response}")
    response_content = yaml.safe_load(response.choices[0].message.content)
    return OpenAIResponse(**response_content)

def execute_command(CMD_OUT: str) -> tuple:
    """
    Execute a given command.

    Args:
        CMD_OUT (str): The command to execute.

    Returns:
        tuple: A tuple containing the output and a boolean indicating if there was an error.
    """
    try:
        output = subprocess.check_output(
            CMD_OUT, shell=True, stderr=subprocess.STDOUT, text=True, timeout=20
        )
        print(f"{Color.CMD_OUT}{output}{Color.END}")
        return output, False
    except subprocess.CalledProcessError as e:
        print(f"{Color.CMD_OUT}Error: {e.output}{Color.END}")
        return e.output, True
    except subprocess.TimeoutExpired as e:
        msg = "The command timedout. Mostly it was waiting for an input and ShellGPT doesn't yet support commands that take user input."
        print(f"{Color.CMD_OUT}Error: {msg}{Color.END}")
        return msg, True


def print_output(cmd_output: list, pipe, process, color: str) -> None:
    """
    Print the output of a command in real-time.

    Args:
        cmd_output (list): The list to store the output lines.
        pipe: The pipe used to read the output.
        process: The process executing the command.
        color (str): The color code to use for printing the output.
    """
    for line in iter(pipe.readline, b""):
        if line != b"":
            line_str = line.rstrip()
            cmd_output.append(line_str)
            print(f"{color}{line_str}{Color.END}")
        if line_str == "" and process.poll() is not None:
            break
    pipe.close()


def execute_command_rt_print(CMD_OUT: str) -> tuple:
    """
    Execute a given command and print its output in real-time.

    Args:
        CMD_OUT (str): The command to execute.

    Returns:
        tuple: A tuple containing the output and a boolean indicating if there was an error.
    """
    try:
        cmd_output = []
        try:
            process = subprocess.Popen(
                CMD_OUT,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            stdout_thread = threading.Thread(
                target=print_output,
                args=(cmd_output, process.stdout, process, Color.CMD_OUT),
            )
            stderr_thread = threading.Thread(
                target=print_output,
                args=(cmd_output, process.stderr, process, Color.CMD_ERR),
            )

            stdout_thread.start()
            stderr_thread.start()

            stdout_thread.join()
            stderr_thread.join()

            return_code = process.wait()
            return "\n".join(cmd_output), return_code != 0
        except KeyboardInterrupt:
            return "\n".join(cmd_output), False
    except subprocess.CalledProcessError as e:
        print(f"{Color.CMD_OUT}Error: {e.output}{Color.END}")
        return e.output, True
    except subprocess.TimeoutExpired as e:
        msg = "The command timedout. Mostly it was waiting for an input and ShellGPT doesn't yet support commands that take user input."
        print(f"{Color.CMD_OUT}Error: {msg}{Color.END}")
        return msg, True


def main(model: str) -> None:
    """Main function."""
    try:
        system_info_txt = ", ".join(
            [f"{k}:{v}" for (k, v) in get_system_info().items()]
        )
        context.append(f"ShellGPT: machine info: {system_info_txt}")
    except Exception as e:
        print(f"{Color.CMD_OUT}Error: Failed to get system info: {e} {Color.END}")
        pass

    session = PromptSession()

    key_bindings = KeyBindings()

    @key_bindings.add(Keys.Escape)
    def escape_key(event):
        event.app.exit("Provide more context and press 'Enter':")

    errored = False
    informational_command = False
    while True:
        # User input
        if not errored and not informational_command:
            user_input = session.prompt(SHELL_PREFIX)
            if user_input.lower() == "exit":
                break
            if user_input.strip() == "":
                continue
            context.append(f"User: {user_input}")
        errored = False
        informational_command = False

        # Command generation
        context_joined = "\n".join(context)
        prompt = f"{context_joined}\nShellGPT: What command should be executed to achieve the following task: {user_input}\n"
        if errored:
            prompt += "\nShellGPT: The previous command failed. Please provide a different command."
        
        try: 
            res = send_query_to_openai(prompt, model)
        except ValidationError as err:
            err_msg = "Got bad response from OpenAI. Trying again."
            print(f"{Color.CMD_OUT}Error: {err_msg}{Color.END}")
            context.append(f"Error: Certain output fields are missing {err}")
            errored=True
            continue
        except yaml.YAMLError as err:
            err_msg = "Got bad response from OpenAI. Trying again."
            print(f"{Color.CMD_OUT}Error: {err_msg}{Color.END}")
            context.append(f"Error: invalid YAML please output fully valid YAML with proper escaping {err}")
            errored=True
            continue


        print(f"{Color.CLI}{res.message_to_user}{Color.END}")
        if not res.can_generate:
            continue
        suggested_command = res.command.strip()
        if suggested_command == "":
            continue
        informational_command = res.informational_command

        # Command confirmation
        try:
            command = session.prompt(
                "cmd" + SHELL_PREFIX,
                default=suggested_command,
                key_bindings=key_bindings,
            )
        except KeyboardInterrupt:
            continue

        context.append(f"Command: {command}")
        output, errored = execute_command_rt_print(command)
        if len(output) > 500:
            output = output[:150] + "..." + output[-150:]

        if not errored:
            context.append(f"Output: {output}")
            errored = False
        else:
            context.append(f"Error: {output}")
            errored = True


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--model",
        type=str,
        default="gpt-4",
        choices=["gpt-4", "gpt-3.5-turbo"],
        help="Choose the model to use for the OpenAI API.",
    )
    parser.add_argument("-d", "--debug", help="Enable debug logs", action="store_true")
    args = parser.parse_args()
    
    log_level = logging.DEBUG if args.debug else logging.WARNING
    logging.basicConfig(level=log_level, format='%(asctime)s - %(levelname)s - %(message)s')

    print("Welcome to ShellGPT! Type your tasks or questions, and ShellGPT will suggest commands to execute.")
    print("Type what you want to acieve, and press Enter. Then ShellGPT will ask you to confirm the command it generated.")
    print("You can optionally modify the command, and press Enter to execute it.")
    print("CTL+C can be used to cancel the current command.")
    print("To exit, type 'exit' and press Enter.")
    try:
        main(args.model)
    except KeyboardInterrupt:
        sys.exit(0)