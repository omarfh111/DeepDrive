from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.urls import reverse
from django.contrib import messages
from .models import Post
from .form import PostForm
from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import PermissionDenied
from django.db.models import Exists, OuterRef,Case, When, IntegerField
from posts.models import Post
from achats.models import Achat
from .ml_model import *
from django.db.models import Exists, OuterRef, Q, Count, Min, Max
from pgvector.django import CosineDistance
import math
from decimal import Decimal

def cosine_distance(a, b):
    dot = 0.0
    na = 0.0
    nb = 0.0
    for x, y in zip(a, b):
        dot += x * y
        na += x * x
        nb += y * y
    denom = math.sqrt(na) * math.sqrt(nb)
    if denom == 0:
        return 1.0
    return 1.0 - (dot / denom)



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
    # Accept both GET (filters) and POST (image upload + filters)
    data = request.POST if request.method == "POST" else request.GET

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
    q = (data.get("q") or "").strip()

    # --- Selected price ---
    min_price_param = data.get("min_price")
    max_price_param = data.get("max_price")

    min_price_sel = price_min
    max_price_sel = price_max
    try:
        if min_price_param is not None and str(min_price_param).strip() != "":
            min_price_sel = float(min_price_param)
        if max_price_param is not None and str(max_price_param).strip() != "":
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

    # --- Selected multi-filters ---
    selected_energies = data.getlist("energy")
    selected_marques = data.getlist("marque")
    selected_transmissions = data.getlist("transmission")
    selected_etats = data.getlist("etat_general")
    selected_carrosseries = data.getlist("carrosserie")

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

    # 3) counts BEFORE applying their own filter (to show available options)
    energy_counts = (
        filtered_qs.values("energy")
        .annotate(count=Count("id"))
        .order_by("energy")
    )
    marque_counts = (
        filtered_qs.values("marque")
        .annotate(count=Count("id"))
        .order_by("marque")
    )
    transmission_counts = (
        filtered_qs.values("transmission")
        .annotate(count=Count("id"))
        .order_by("transmission")
    )
    etat_counts = (
        filtered_qs.values("etat_general")
        .annotate(count=Count("id"))
        .order_by("etat_general")
    )
    carrosserie_counts = (
        filtered_qs.values("carrosserie")
        .annotate(count=Count("id"))
        .order_by("carrosserie")
    )

    # 4) apply checkbox filters
    if selected_energies:
        filtered_qs = filtered_qs.filter(energy__in=selected_energies)

    if selected_transmissions:
        filtered_qs = filtered_qs.filter(transmission__in=selected_transmissions)

    if selected_etats:
        filtered_qs = filtered_qs.filter(etat_general__in=selected_etats)

    if selected_carrosseries:
        filtered_qs = filtered_qs.filter(carrosserie__in=selected_carrosseries)

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

    # --- Image similarity search (POST multipart) ---
    sorted_by_similarity = False
    query_image = request.FILES.get("query_image")

    if query_image:
        try:
            q_emb = embed_car_image(query_image)  # list[float] len=512

            # IMPORTANT: limit candidates for performance (tune the slice)
            candidate_rows = list(
                posts.exclude(embedding__isnull=True)
                    .exclude(embedding=[])
                    .values("id", "embedding")[:3000]
            )

            scored = []
            for row in candidate_rows:
                emb = row["embedding"]
                if not isinstance(emb, list) or len(emb) != len(q_emb):
                    continue
                d = cosine_distance(emb, q_emb)
                scored.append((row["id"], d))

            scored.sort(key=lambda t: t[1])
            ordered_ids = [pid for pid, _ in scored]

            if ordered_ids:
                whens = [When(id=pid, then=pos) for pos, pid in enumerate(ordered_ids)]
                posts = posts.filter(id__in=ordered_ids).annotate(
                    _order=Case(*whens, output_field=IntegerField())
                ).order_by("_order")
                sorted_by_similarity = True

        except Exception as e:
            print(f"[SIMSEARCH] failed: {e!r}")

    # --- Sort by price (only if not similarity-sorted) ---
    order = data.get("order")
    if not sorted_by_similarity:
        if order == "price_asc":
            posts = posts.order_by("price")
        elif order == "price_desc":
            posts = posts.order_by("-price")
        # else: keep default ordering from Meta (by -id)

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
            "selected_order": order,
            "sorted_by_similarity": sorted_by_similarity,
        },
        backoffice
    )













@login_required
def add_car(request, backoffice=False):
    template = 'add_car.html'
    if request.method == 'POST':
        dashboard_image = request.FILES.get('dashboard_image')
        car_image       = request.FILES.get('image')

        extracted_km = None
        ocr_error = False
        car_error = False

        # ---- 1) Verify that the main car image really contains a car ----
        if car_image:
            try:
                is_car = verify_car_image(car_image)
                if not is_car:
                    messages.error(
                        request,
                        "❌ L'image principale ne semble pas contenir une vraie voiture. "
                        "Veuillez téléverser une photo claire de la voiture réelle."
                    )
                    car_error = True
            except Exception as e:
                # We already log inside verify_car_image; here we warn but do not block hard
                messages.warning(
                    request,
                    "⚠ Impossible de vérifier que l'image est bien une voiture. "
                    "Veuillez vérifier manuellement."
                )

       
        if dashboard_image and not car_error:
            try:
                result = extract_kilometrage_from_image(dashboard_image)
                extracted_km = result["kilometrage"]
            except ValueError as e:
                messages.error(request, f"❌ {e}")
                ocr_error = True
            except Exception as e:
                messages.error(
                    request,
                    f"❌ Erreur technique lors de l'extraction du kilométrage: {str(e)}"
                )
                ocr_error = True
        else:
            if not dashboard_image:
                messages.error(
                    request,
                    "❌ L'image du tableau de bord est obligatoire pour extraire le kilométrage."
                )
                ocr_error = True

        # ---- 3) Recréer les données du formulaire (en intégrant le km extrait) ----
        post_data = request.POST.copy()
        if extracted_km is not None:
            post_data["kilometrage"] = str(extracted_km)

        form = PostForm(post_data, request.FILES)

        # Si problème de voiture ou d'odomètre → ne pas sauvegarder
        if car_error or ocr_error:
            return render_template(request, template, {"form": form}, backoffice)

        # ---- 4) Validation finale du formulaire ----
        if form.is_valid():
            obj = form.save(commit=False)
            try:
                pred_price, label = predict_price_and_label(
                    annee=obj.annee,
                    kilometrage=obj.kilometrage,
                    marque=obj.marque,
                    modele=obj.modele,
                    seller_price=float(obj.price),
                )
                obj.predicted_price = Decimal(str(round(pred_price)))
                obj.offer_label = label
            except Exception as e:
                print(f"[PRICE_ML] failed for post: {e!r}")
            obj.owner = request.user
            obj.save()
            try:
                with obj.image.open("rb") as f:
                    obj.embedding = embed_car_image(f)   
                obj.save(update_fields=["embedding"])
            except Exception as e:
                print(f"[EMBED] failed for post {obj.id}: {e!r}")
            if backoffice:
                return redirect('posts:admin_portfolio')
            return redirect('posts:portfolio')
        else:
            messages.error(request, "❌ Veuillez corriger les erreurs dans le formulaire.")
    else:
        form = PostForm()

    return render_template(request, template, {'form': form}, backoffice)






@login_required
def update_post(request, post_id, backoffice=False):
    template = 'update_post.html'
    post = get_object_or_404(Post, id=post_id)

    if not (request.user.is_staff or request.user == post.owner):
        raise PermissionDenied

    if request.method == 'POST':
        dashboard_image = request.FILES.get('dashboard_image')
        car_image       = request.FILES.get('image')  # only set if user uploads a new one
        extracted_km = None
        car_error = False

        # ---- 1) If a new main image is provided, verify it is a real car ----
        if car_image:
            try:
                is_car = verify_car_image(car_image)
                if not is_car:
                    messages.error(
                        request,
                        "❌ La nouvelle image ne semble pas contenir une vraie voiture. "
                        "Veuillez téléverser une photo claire de la voiture réelle."
                    )
                    car_error = True
            except Exception as e:
                messages.warning(
                    request,
                    "⚠ Impossible de vérifier que l'image est bien une voiture. "
                    "Veuillez vérifier manuellement."
                )

        # ---- 2) Optional odometer OCR on update (if new dashboard_image) ----
        if dashboard_image and not car_error:
            try:
                result = extract_kilometrage_from_image(dashboard_image)
                if result and result.get('kilometrage') is not None:
                    extracted_km = result['kilometrage']
            except ValueError as e:
                messages.warning(
                    request,
                    f"⚠ Impossible de détecter le compteur sur l'image: {str(e)}. "
                    "Veuillez vérifier la photo ou saisir le kilométrage manuellement."
                )
            except Exception as e:
                messages.error(
                    request,
                    f"❌ Erreur lors de l'extraction du kilométrage: {str(e)}"
                )

        # ---- 3) Recréer POST data (en remplaçant éventuellement le kilométrage) ----
        post_data = request.POST.copy()

        if extracted_km is not None:
            post_data['kilometrage'] = str(int(extracted_km))

        form = PostForm(post_data, request.FILES, instance=post)

        # Si l'image n'est pas une vraie voiture → ne pas sauvegarder
        if car_error:
            return render_template(request, template, {'form': form, 'post': post}, backoffice)

        # ---- 4) Validation et sauvegarde ----
        if form.is_valid():
            updated_post = form.save(commit=False)
            updated_post.owner = post.owner
            updated_post.save()

            messages.success(request, "✓ Voiture mise à jour avec succès.")

            if backoffice:
                return redirect('posts:admin_portfolio')
            return redirect('posts:portfolio')
        else:
            messages.error(request, "❌ Veuillez corriger les erreurs dans le formulaire.")
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
