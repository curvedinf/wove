"""
Example: Dynamic Workflow with Live API Data and `merge`
This script demonstrates how to use `wove.merge` to build dynamic workflows
where the functions to be called are determined at runtime based on live API data.
- A main task fetches user data from a real public API (jsonplaceholder.typicode.com).
- Based on a value in the data (e.g., the user's ID), it dynamically chooses
  which function to execute next using `merge`.
- `merge` seamlessly handles calling both async and sync functions.
This pattern is useful for complex, stateful processes, conditional branching,
or workflows where the exact steps are not known ahead of time.
"""

import asyncio
import httpx
from functools import partial
from wove import weave, merge


# --- Functions that can be dynamically called ---
async def fetch_user_data(user_id: int):
    """Fetches user data from the JSONPlaceholder API."""
    print(f"Fetching data for user {user_id}...")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"https://jsonplaceholder.typicode.com/users/{user_id}"
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError:
            return None


async def process_special_user(user_data: dict):
    """A specific async task for processing a 'special' user (e.g., ID <= 5)."""
    print(
        f"Processing special privileges for user {user_data['id']} ({user_data['name']})..."
    )
    return f"Processed special user: {user_data['name']}"


def generate_standard_user_report(user_data: dict):
    """A specific sync task for generating a report for a standard user."""
    print(
        f"Generating standard report for user {user_data['id']} ({user_data['name']})..."
    )
    return f"Generated report for user: {user_data['name']}"


async def run_dynamic_workflow_example():
    """
    Runs the dynamic workflow example.
    """
    print("--- Running Dynamic Workflow Example ---")

    async with weave() as w:

        @w.do
        async def process_user_one():
            # Step 1: Fetch initial data for a user who will be 'special'.
            user = await fetch_user_data(1)
            if not user:
                return "User 1 not found"

            # Step 2: Dynamically choose the next function based on the data.
            # We'll treat users with ID <= 5 as 'special'.
            if user["id"] <= 5:
                # Use merge to call an async function.
                # `partial` is used to pass arguments to the function.
                result = await merge(partial(process_special_user, user))
            else:
                # Use merge to call a sync function.
                # A lambda is used here to pass arguments.
                result = await merge(lambda: generate_standard_user_report(user))

            return result

        @w.do
        async def process_user_two():
            # Run the same logic for a different user to show the other branch.
            user = await fetch_user_data(6)  # This user is a standard user.
            if not user:
                return "User 6 not found"

            if user["id"] <= 5:
                result = await merge(partial(process_special_user, user))
            else:
                result = await merge(lambda: generate_standard_user_report(user))

            return result

    # The results show that the correct function was called for each user.
    print(f"Result for User 1 (Special): {w.result['process_user_one']}")
    print(f"Result for User 6 (Standard):  {w.result['process_user_two']}")

    assert w.result["process_user_one"] == "Processed special user: Leanne Graham"
    assert (
        w.result["process_user_two"]
        == "Generated report for user: Mrs. Dennis Schulist"
    )

    print("--- Dynamic Workflow Example Finished ---")


if __name__ == "__main__":
    asyncio.run(run_dynamic_workflow_example())
