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
from .ml_model import *

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
            obj.owner = request.user
            obj.save()


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
