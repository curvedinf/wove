"""
Example: Django-style View with Dynamic Tasks
This script simulates a common web-backend scenario: fetching a main resource
(a Post), its related data (Author, Comments), and then conditionally fetching
additional data based on the results.
- It uses mock data and functions to simulate database lookups.
- The `author_permissions` task demonstrates conditional logic: if the author
  is an admin, it uses `wove.merge` to dynamically call another function
  (`fetch_admin_permissions`) to get extra data.
- The final result is composed from the outputs of all preceding tasks.
"""
import asyncio
import json
from wove import weave, merge

# --- Mock Data Store ---
# In a real application, this data would come from a database.
USERS = {
    1: {"id": 1, "username": "admin_user", "email": "admin@example.com", "is_admin": True},
    2: {"id": 2, "username": "jane_doe", "email": "jane@example.com", "is_admin": False},
}
POSTS = {
    101: {"id": 101, "title": "Wove in Action", "author_id": 1},
}
COMMENTS = {
    101: [
        {"author_name": "jane_doe", "text": "Great post!"},
        {"author_name": "some_user", "text": "Very informative."},
    ]
}

# --- Mock Async Data Fetching Functions ---
# These simulate non-blocking database/API calls.
async def fetch_post_from_db(post_id: int):
    """Simulates an async database lookup for a post."""
    await asyncio.sleep(0.01)
    return POSTS.get(post_id)

async def fetch_user_from_db(user_id: int):
    """Simulates an async database lookup for a user."""
    await asyncio.sleep(0.01)
    return USERS.get(user_id)

async def fetch_comments_from_db(post_id: int):
    """Simulates an async database lookup for comments."""
    await asyncio.sleep(0.01)
    return COMMENTS.get(post_id, [])

async def fetch_admin_permissions(user_id: int):
    """A separate function to fetch extra data, called dynamically."""
    print(f"-> Dynamically fetching admin permissions for user {user_id}...")
    await asyncio.sleep(0.02)
    return ["create_post", "delete_post", "edit_user"]

# --- Main Wove Orchestration Logic ---
async def get_post_details(post_id: int):
    """
    Fetches post details, author, comments, and conditional permissions
    concurrently using Wove.
    """
    print(f"--- Running Django-style Example for Post {post_id} ---")
    async with weave() as w:
        @w.do
        async def post():
            return await fetch_post_from_db(post_id)

        @w.do
        async def author(post):
            # This task depends on `post`. It won't run until `post` is complete.
            if not post:
                return None
            return await fetch_user_from_db(post['author_id'])

        @w.do
        async def comments(post):
            # This task also depends on `post` and runs in parallel with `author`.
            if not post:
                return []
            return await fetch_comments_from_db(post['id'])

        @w.do
        async def author_permissions(author):
            """
            Conditionally fetches permissions using `merge`.
            This task depends on `author`.
            """
            if author and author.get("is_admin"):
                # If the author is an admin, dynamically call the permission-fetching
                # function and wait for its result. `merge` integrates this call
                # into Wove's execution graph.
                return await merge(lambda: fetch_admin_permissions(author['id']))
            else:
                # If not an admin, return a default value.
                return []

        # This final task depends on all the previous data-fetching tasks.
        @w.do
        def composed_response(post, author, comments, author_permissions):
            if not post:
                return {"error": "Post not found"}
            
            post['author'] = author
            post['comments'] = comments
            if author_permissions:
                post['author']['permissions'] = author_permissions
            return post

    # The `.final` property is a convenient shortcut for the result of the
    # last-defined task in the `weave` block.
    return w.result.final

async def main():
    # --- Run for an admin user ---
    admin_post_response = await get_post_details(101)
    print("\nFinal Response (Admin Author):")
    print(json.dumps(admin_post_response, indent=2))
    
    # Verification for admin case
    assert admin_post_response['author']['is_admin'] is True
    assert "permissions" in admin_post_response['author']
    assert admin_post_response['author']['permissions'] == ["create_post", "delete_post", "edit_user"]

    # --- Add a non-admin post and run for that user ---
    POSTS[102] = {"id": 102, "title": "Another Post", "author_id": 2}
    non_admin_post_response = await get_post_details(102)
    print("\nFinal Response (Non-Admin Author):")
    print(json.dumps(non_admin_post_response, indent=2))

    # Verification for non-admin case
    assert non_admin_post_response['author']['is_admin'] is False
    assert "permissions" not in non_admin_post_response['author']
    
    print("\n--- Django-style Example Finished ---")

if __name__ == "__main__":
    asyncio.run(main())
