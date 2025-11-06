from django.shortcuts import render, get_object_or_404, redirect
from .models import Post
from .form import PostForm


# Generic render helper for front/back templates
def render_template(request, template_name, context=None, backoffice=False):
    """
    Automatically use correct path for posts templates.
    Backoffice templates are also inside templates/posts/.
    """
    if backoffice:
        template_name = f'posts/back_{template_name}'
    else:
        template_name = f'posts/{template_name}'
    return render(request, template_name, context or {})


def portfolio(request, backoffice=False):
    posts = Post.objects.all()
    template = 'portfolio-2.html'
    return render_template(request, template, {'posts': posts}, backoffice)


def add_car(request, backoffice=False):
    template = 'add_car.html'
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('admin_portfolio' if backoffice else 'portfolio')
    else:
        form = PostForm()
    return render_template(request, template, {'form': form}, backoffice)


def update_post(request, post_id, backoffice=False):
    template = 'update_post.html'
    post = get_object_or_404(Post, id=post_id)

    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            form.save()
            return redirect('admin_portfolio' if backoffice else 'portfolio')
    else:
        form = PostForm(instance=post)

    return render_template(request, template, {'form': form, 'post': post}, backoffice)


def delete_car(request, pk, backoffice=False):
    template = 'delete_car.html'
    car = get_object_or_404(Post, pk=pk)
    if request.method == 'POST':
        car.delete()
        return redirect('admin_portfolio' if backoffice else 'portfolio')
    return render_template(request, template, {'car': car}, backoffice)
