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
from django.db.models import Exists, OuterRef, Q, Count, Min, Max
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
    # Base queryset: only posts without PAID achat
    base_qs = Post.objects.annotate(
        has_paid_achat=Exists(
            Achat.objects.filter(post_id=OuterRef('pk'), statut=Achat.Status.PAID)
        )
    ).filter(has_paid_achat=False)

    # --- Global min/max price from DB ---
    price_agg = base_qs.aggregate(
        min_price=Min('price'),
        max_price=Max('price'),
    )
    price_min = price_agg['min_price'] or 0
    price_max = price_agg['max_price'] or 0

    # --- Search text ---
    q = request.GET.get("q", "").strip()

    # --- Selected price (from GET) ---
    min_price_param = request.GET.get("min_price")
    max_price_param = request.GET.get("max_price")

    min_price_sel = price_min
    max_price_sel = price_max
    try:
        if min_price_param is not None:
            min_price_sel = float(min_price_param)
        if max_price_param is not None:
            max_price_sel = float(max_price_param)
    except ValueError:
        min_price_sel = price_min
        max_price_sel = price_max

    # Clamp to global range
    if min_price_sel < price_min:
        min_price_sel = price_min
    if max_price_sel > price_max:
        max_price_sel = price_max
    if min_price_sel > max_price_sel:
        min_price_sel, max_price_sel = max_price_sel, min_price_sel

    # Start from base_qs and apply filters in layers
    filtered_qs = base_qs

    # 1) search filter
    if q:
        filtered_qs = filtered_qs.filter(
            Q(marque__icontains=q) |
            Q(modele__icontains=q) |
            Q(gouvernerat__icontains=q) |
            Q(energy__icontains=q)
        )

    # 2) price filter
    if price_min != price_max:
        filtered_qs = filtered_qs.filter(
            price__gte=min_price_sel,
            price__lte=max_price_sel,
        )

    # 3) fuel / energy filter (counts before filtering, so you see all options)
    energy_counts = (
        filtered_qs
        .values("energy")
        .annotate(count=Count("id"))
        .order_by("energy")
    )

    selected_energies = request.GET.getlist("energy")
    if selected_energies:
        filtered_qs = filtered_qs.filter(energy__in=selected_energies)

    # 4) marque filter + counts
    marque_counts = (
        filtered_qs
        .values("marque")
        .annotate(count=Count("id"))
        .order_by("marque")
    )

    selected_marques = request.GET.getlist("marque")
    if selected_marques:
        posts = filtered_qs.filter(marque__in=selected_marques)
    else:
        posts = filtered_qs

    # Slider positions (0–100)
    if price_max != price_min:
        min_percent = (min_price_sel - price_min) / (price_max - price_min) * 100
        max_percent = (max_price_sel - price_min) / (price_max - price_min) * 100
    else:
        min_percent = 0
        max_percent = 100
        # --- Transmission filter ---
    transmission_counts = (
        filtered_qs
        .values("transmission")
        .annotate(count=Count("id"))
        .order_by("transmission")
    )

    selected_transmissions = request.GET.getlist("transmission")
    if selected_transmissions:
        filtered_qs = filtered_qs.filter(transmission__in=selected_transmissions)

    # --- Etat Général filter ---
    etat_counts = (
        filtered_qs
        .values("etat_general")
        .annotate(count=Count("id"))
        .order_by("etat_general")
    )

    selected_etats = request.GET.getlist("etat_general")
    if selected_etats:
        filtered_qs = filtered_qs.filter(etat_general__in=selected_etats)

    # --- Carrosserie filter ---
    carrosserie_counts = (
        filtered_qs
        .values("carrosserie")
        .annotate(count=Count("id"))
        .order_by("carrosserie")
    )

    selected_carrosseries = request.GET.getlist("carrosserie")
    if selected_carrosseries:
        filtered_qs = filtered_qs.filter(carrosserie__in=selected_carrosseries)


    template = 'portfolio-2.html'
    return render_template(
        request,
        template,
        {
            "posts": posts,
            "marque_counts": marque_counts,
            "selected_marques": selected_marques,
            "energy_counts": energy_counts,
            "selected_energies": selected_energies,
            "q": q,
            "price_min": price_min,
            "price_max": price_max,
            "min_price_sel": min_price_sel,
            "max_price_sel": max_price_sel,
            "min_percent": min_percent,
            "max_percent": max_percent,
            "transmission_counts": transmission_counts,
            "selected_transmissions": selected_transmissions,
            "etat_counts": etat_counts,
            "selected_etats": selected_etats,
            "carrosserie_counts": carrosserie_counts,
            "selected_carrosseries": selected_carrosseries,

        },
        backoffice
    )
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
