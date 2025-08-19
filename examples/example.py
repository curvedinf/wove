# your_app/views.py
from django.http import JsonResponse
from asgiref.sync import sync_to_async
from django.contrib.auth.models import User
from .models import Post, Comment
import wove
from wove import weave

async def post_detail_view(request, post_id: int):
    """
    Final version demonstrating both result unpacking and the .final shortcut.
    """
    async with weave() as w:
        @w.do
        def post():
            post_lookup = sync_to_async(Post.objects.values().get)
            return await post_lookup(id=post_id)

        @w.do
        def author(post):
            author_lookup = sync_to_async(
                User.objects.values('username', 'email').get
            )
            return await author_lookup(id=post['author_id'])

        @w.do
        def comments(post):
            comments_lookup = sync_to_async(
                lambda: list(Comment.objects.values('author_name', 'text').filter(post_id=post['id']))
            )
            return await comments_lookup()

        # This is the last-defined task.
        @w.do
        def composed_response(post, author, comments):
            post['author'] = author
            post['comments'] = comments
            return post

    # --- Accessing the Results ---
    # 1. Unpack all results by their definition order.
    post_obj, author_obj, comments_list, final_response = w.result

    # 2. Use the .final shortcut for the last task's output.
    # This is often the cleanest option for returning a response.
    assert w.result.final == final_response
    assert w.result.final == w.result['composed_response']

    return JsonResponse(w.result.final)
