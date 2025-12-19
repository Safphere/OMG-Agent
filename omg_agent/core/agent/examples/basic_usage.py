"""
Basic usage example for Agent.

This example demonstrates how to use the PhoneAgent to automate
phone interactions with natural language commands.
"""

import os
import sys

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from omg_agent.core.agent import PhoneAgent, AgentConfig, ReplyMode
from omg_agent.core.agent.llm import LLMConfig


def main():
    """Basic usage example."""
    # Configure LLM
    llm_config = LLMConfig(
        provider="openai",
        model="gpt-4o",
        api_key=os.environ.get("OPENAI_API_KEY"),
        # Or use local model:
        # provider="local",
        # api_base="http://localhost:8000/v1",
        # model="your-local-model",
    )

    # Configure agent
    agent_config = AgentConfig(
        device_id=None,  # Auto-detect device, or specify like "emulator-5554"
        max_steps=50,
        lang="zh",  # or "en"
        verbose=True,
        reply_mode=ReplyMode.CALLBACK,  # How to handle INFO actions
    )

    # Create agent
    agent = PhoneAgent(
        llm_config=llm_config,
        agent_config=agent_config,
        # Optional callbacks
        confirmation_callback=lambda msg: input(f"Confirm {msg}? (y/n): ").lower() == "y",
        takeover_callback=lambda msg: input(f"Please {msg}, then press Enter..."),
        info_callback=lambda q: input(f"Agent asks: {q}\nYour answer: "),
    )

    # Run a task
    task = "Open Settings app and check the Android version"
    print(f"\nStarting task: {task}\n")

    result = agent.run(task)

    print(f"\n{'='*50}")
    print(f"Task completed: {result.success}")
    print(f"Message: {result.message}")
    print(f"Steps taken: {result.step_count}")
    print(f"Stop reason: {result.stop_reason}")
    print(f"{'='*50}")


def step_by_step_example():
    """Example of manual step-by-step control."""
    llm_config = LLMConfig(provider="openai", model="gpt-4o")
    agent_config = AgentConfig(verbose=True)

    agent = PhoneAgent(llm_config, agent_config)

    task = "Open the camera app"

    # First step with task
    result = agent.step(task=task)
    print(f"Step 1: {result.action.action_type if result.action else 'None'}")

    # Continue stepping until finished
    while not result.finished:
        result = agent.step()
        print(f"Step {result.step_count}: {result.action.action_type if result.action else 'None'}")

        if result.needs_user_input:
            # Handle INFO action
            user_reply = input(f"Agent asks: {result.user_prompt}\nYour answer: ")
            result = agent.step(user_reply=user_reply)

    print(f"\nTask finished: {result.message}")


def session_example():
    """Example of session management for task resumption."""
    llm_config = LLMConfig(provider="openai", model="gpt-4o")

    # Configure with PAUSE mode - session will pause on INFO action
    agent_config = AgentConfig(
        reply_mode=ReplyMode.PAUSE,
        session_dir="./sessions",  # Persist sessions to disk
    )

    agent = PhoneAgent(llm_config, agent_config)

    # Start task
    result = agent.run("Search for restaurants nearby")

    if result.stop_reason == "paused":
        print(f"Task paused. Agent asked: {result.final_action.params.get('value')}")
        print(f"Session ID: {result.session_id}")

        # Later, resume with user's answer
        user_answer = "I want Italian food"
        result = agent.run(
            task="",  # Not needed for resume
            session_id=result.session_id,
            user_reply=user_answer
        )

    print(f"Final result: {result.message}")


if __name__ == "__main__":
    main()
