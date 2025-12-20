from src.container import Container
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def main():
    """
    Main function to initialize and run the AI agent.
    """
    container = Container()
    agent_executor = container.get_agent_graph()

    print("AI Agent initialized. Type 'exit' to quit.")

    while True:
        user_input = input("You: ")
        if user_input.lower() == "exit":
            break

        # For LangGraph, you might need to structure the input state
        # based on your AgentState definition.
        # Assuming AgentState has 'input' and 'chat_history'
        initial_state = {
            "input": user_input,
            "chat_history": [],
            "intermediate_steps": [],
            "tool_output": "",
            "response": "",
        }

        # The stream method returns an iterator of states as the graph executes
        for s in agent_executor.stream(initial_state):
            # The 'output' key usually contains the state of the graph
            # after each node's execution.
            print(f"Intermediate State: {s}")
            # If you want to see the final output only
            if "__end__" in s:
                final_state = s["__end__"]
                print(f"Agent: {final_state.get('response')
                      or final_state.get('tool_output')}")
                break


if __name__ == "__main__":
    main()
