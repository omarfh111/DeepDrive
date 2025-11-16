from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.urls import reverse
from django.contrib import messages
from .models import Post
from .form import PostForm
from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import PermissionDenied
from django.db.models import Exists, OuterRef
from posts.models import Post
from achats.models import Achat
# --- Helpers d'accès ---
def is_admin(user):
    # Adaptez selon votre app "user": ex. user.profile.role == 'admin'
    return user.is_staff or user.is_superuser

def admin_required(view_func):
    return login_required(user_passes_test(is_admin))(view_func)

# --- Render helper existant ---
def render_template(request, template_name, context=None, backoffice=False):
    if backoffice:
        template_name = f'posts/back_{template_name}'
    else:
        template_name = f'posts/{template_name}'
    return render(request, template_name, context or {})

# --- Liste / Portfolio ---
def portfolio(request, backoffice=False):
    posts = Post.objects.annotate(
        has_paid_achat=Exists(
            Achat.objects.filter(post_id=OuterRef('pk'), statut=Achat.Status.PAID)
        )
    ).filter(has_paid_achat=False)
    template = 'portfolio-2.html'
    return render_template(request, template, {'posts': posts}, backoffice)


# --- Create ---
@login_required
def add_car(request, backoffice=False):
    template = 'add_car.html'
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.owner = request.user
            obj.save()
            if backoffice:
                return redirect('posts:admin_portfolio')
            return redirect('posts:portfolio')
    else:
        form = PostForm()
    return render_template(request, template, {'form': form}, backoffice)

# --- Update ---
@login_required
def update_post(request, post_id, backoffice=False):
    template = 'update_post.html'
    post = get_object_or_404(Post, id=post_id)

    if not (request.user.is_staff or request.user == post.owner):
        raise PermissionDenied
    
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            form.save()
            if backoffice:
                return redirect('posts:admin_portfolio')
            return redirect('posts:portfolio')
    else:
        form = PostForm(instance=post)
    return render_template(request, template, {'form': form, 'post': post}, backoffice)

# --- Delete ---
@login_required
def delete_car(request, pk, backoffice=False):
    template = 'delete_car.html'
    car = get_object_or_404(Post, pk=pk)

    if not (request.user.is_staff or request.user == car.owner):
        raise PermissionDenied
    
    if request.method == 'POST':
        car.delete()
        messages.success(request, "Annonce supprimée.")
        return redirect('posts:admin_portfolio' if backoffice else 'posts:portfolio')
    return render_template(request, template, {'car': car}, backoffice)

# =========================
# Wrappers Backoffice (protégés)
# =========================
@staff_member_required
def admin_portfolio(request):
    return portfolio(request, backoffice=True)



@staff_member_required
def admin_add_car(request):
    return add_car(request, backoffice=True)

@staff_member_required
def admin_update_post(request, post_id):
    return update_post(request, post_id=post_id, backoffice=True)

@staff_member_required
def admin_delete_car(request, pk):
    return delete_car(request, pk=pk, backoffice=True)

def post_detail(request, pk, backoffice=False):
    template = 'portfolio-details.html'  # file is templates/posts/portfolio-details.html
    post = get_object_or_404(Post, pk=pk)
    return render_template(request, template, {'post': post}, backoffice)
