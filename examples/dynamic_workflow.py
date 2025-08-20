"""
Example: Dynamic Workflow with `merge`
This script demonstrates how to use the `wove.merge` function to build dynamic
workflows where the functions to be called are determined at runtime based on
conditional logic inside a task.

- A main task fetches some data.
- Based on a value in the data (e.g., user role), it dynamically chooses
  which function to execute next using `merge`.
- `merge` seamlessly handles calling both async and sync functions.

This pattern is useful for complex, stateful processes, conditional branching,
or workflows where the exact steps are not known ahead of time.
"""
import asyncio
from functools import partial
from wove import weave, merge

# --- Functions that can be dynamically called ---
async def fetch_user_data(user_id: int):
    """Simulates fetching user data from a database or API."""
    print(f"Fetching data for user {user_id}...")
    # In a real app, this would be an I/O call. Here we simulate the result.
    return {"id": user_id, "role": "admin" if user_id == 1 else "user"}

async def process_admin_privileges(user_data: dict):
    """A specific async task for processing an admin user."""
    print(f"Processing special admin privileges for user {user_data['id']}...")
    return f"Processed admin: {user_data['id']}"

def generate_standard_user_report(user_data: dict):
    """A specific sync task for generating a report for a standard user."""
    print(f"Generating standard report for user {user_data['id']}...")
    return f"Generated report for user: {user_data['id']}"

async def run_dynamic_workflow_example():
    """
    Runs the dynamic workflow example.
    """
    print("--- Running Dynamic Workflow Example ---")
    
    async with weave() as w:
        @w.do
        async def process_user_one():
            # Step 1: Fetch initial data.
            user = await fetch_user_data(1)  # This user will be an admin.
            
            # Step 2: Dynamically choose the next function based on the data.
            if user['role'] == 'admin':
                # Use merge to call an async function.
                # `partial` is used to pass arguments to the function.
                result = await merge(partial(process_admin_privileges, user))
            else:
                # Use merge to call a sync function.
                # A lambda is used here to pass arguments.
                result = await merge(lambda: generate_standard_user_report(user))
            
            return result

        @w.do
        async def process_user_two():
            # Run the same logic for a different user to show the other branch.
            user = await fetch_user_data(2)  # This user is a standard user.
            
            if user['role'] == 'admin':
                result = await merge(partial(process_admin_privileges, user))
            else:
                result = await merge(lambda: generate_standard_user_report(user))
            
            return result

    # The results show that the correct function was called for each user.
    print(f"Result for User 1 (Admin): {w.result['process_user_one']}")
    print(f"Result for User 2 (User):  {w.result['process_user_two']}")
    
    assert w.result['process_user_one'] == "Processed admin: 1"
    assert w.result['process_user_two'] == "Generated report for user: 2"
    
    print("--- Dynamic Workflow Example Finished ---")

if __name__ == "__main__":
    asyncio.run(run_dynamic_workflow_example())
