"""
Example: Django-style View with Live API Data
This script simulates a common web-backend scenario using a real-world API:
fetching a main resource (a Post), its related data (Author, Comments), and
then conditionally fetching additional data based on the results.
- It uses `httpx` to make asynchronous API calls to jsonplaceholder.typicode.com.
- The `author_permissions` task demonstrates conditional logic: if the author's
  ID is 1 (we'll treat them as an admin), it uses `wove.merge` to dynamically
  call another function (`fetch_admin_permissions`) to get extra data.
- The final result is composed from the outputs of all preceding tasks.
"""

import asyncio
import json
import httpx
from wove import weave, merge

BASE_URL = "https://jsonplaceholder.typicode.com"

# --- Real Async API Fetching Functions ---
# These simulate non-blocking database/API calls by using a real public API.


async def fetch_post(post_id: int):
    """Fetches a single post from the JSONPlaceholder API."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{BASE_URL}/posts/{post_id}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError:
            return None


async def fetch_author_details(user_id: int):
    """Fetches user (author) details from the JSONPlaceholder API."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/users/{user_id}")
        response.raise_for_status()
        return response.json()


async def fetch_comments(post_id: int):
    """Fetches comments for a post from the JSONPlaceholder API."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/posts/{post_id}/comments")
        response.raise_for_status()
        return response.json()


async def fetch_admin_permissions(user_id: int):
    """A separate function to fetch extra data, called dynamically."""
    print(f"-> Dynamically fetching admin permissions for user {user_id}...")
    await asyncio.sleep(0.02)  # Simulate a separate I/O call
    return ["create_post", "delete_post", "edit_user"]


# --- Main Wove Orchestration Logic ---


async def get_post_details(post_id: int):
    """
    Fetches post details, author, comments, and conditional permissions
    concurrently using Wove.
    """
    print(f"--- Running Live API Example for Post {post_id} ---")
    async with weave() as w:

        @w.do
        async def post():
            return await fetch_post(post_id)

        @w.do
        async def author(post):
            # This task depends on `post`. It won't run until `post` is complete.
            if not post:
                return None
            return await fetch_author_details(post["userId"])

        @w.do
        async def comments(post):
            # This task also depends on `post` and runs in parallel with `author`.
            if not post:
                return []
            return await fetch_comments(post["id"])

        @w.do
        async def author_permissions(author):
            """
            Conditionally fetches permissions using `merge`.
            We'll treat user ID 1 as an "admin" for this example.
            """
            if author and author.get("id") == 1:
                # If the author is an admin, dynamically call the permission-fetching
                # function and wait for its result. `merge` integrates this call
                # into Wove's execution graph.
                return await merge(lambda: fetch_admin_permissions(author["id"]))
            else:
                # If not an admin, return a default value.
                return []

        # This final task depends on all the previous data-fetching tasks.
        @w.do
        def composed_response(post, author, comments, author_permissions):
            if not post:
                return {"error": "Post not found"}

            post["author"] = author
            post["comments"] = comments
            if author_permissions:
                # Add a synthetic `is_admin` field for clarity in the output
                post["author"]["is_admin"] = True
                post["author"]["permissions"] = author_permissions
            elif author:
                post["author"]["is_admin"] = False
            return post

    # The `.final` property is a convenient shortcut for the result of the
    # last-defined task in the `weave` block.
    return w.result.final


async def main():
    # --- Run for an "admin" user (Post 1 is authored by User 1) ---
    admin_post_response = await get_post_details(1)
    print("\nFinal Response (Admin Author):")
    print(json.dumps(admin_post_response, indent=2))

    # Verification for admin case
    assert admin_post_response["author"]["is_admin"] is True
    assert "permissions" in admin_post_response["author"]
    assert admin_post_response["author"]["permissions"] == [
        "create_post",
        "delete_post",
        "edit_user",
    ]
    assert admin_post_response["userId"] == 1

    # --- Run for a non-admin user (Post 11 is authored by User 2) ---
    non_admin_post_response = await get_post_details(11)
    print("\nFinal Response (Non-Admin Author):")
    print(json.dumps(non_admin_post_response, indent=2))

    # Verification for non-admin case
    assert non_admin_post_response["author"]["is_admin"] is False
    assert "permissions" not in non_admin_post_response["author"]
    assert non_admin_post_response["userId"] == 2

    print("\n--- Live API Example Finished ---")


if __name__ == "__main__":
    asyncio.run(main())
