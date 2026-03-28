from django.shortcuts import render, get_object_or_404, redirect
from .models import TestDrive
from django.views.generic import ListView, CreateView,DetailView,UpdateView,DeleteView
from django.urls import reverse_lazy
from .forms import TestDriveForm,TestDriveUpdateForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.mail import send_mail
from django.conf import settings
from django.http import JsonResponse
from .ml_model import predictor
# @login_required
# def testdrive_list(request):
#     user = request.user 
#     testdrives = TestDrive.objects.filter(user=user)
#     return render(request, "TestDrive/testdrive_list.html", {
#         "testdrives": testdrives,
#     })


from twilio.rest import Client
from django.conf import settings 

from twilio.rest import Client
from django.conf import settings  

class TestDriveCreate(CreateView):
    model = TestDrive
    form_class = TestDriveForm
    template_name = 'TestDrive/add_testdrive.html'
    success_url = reverse_lazy("TestDrive:liste_testdrive")

    def form_valid(self, form):
        form.instance.user = self.request.user
        response = super().form_valid(form)

        # Envoi d'un email de confirmation
        try:
            subject = "Confirmation de votre Test Drive"
            message = (
                f"Salut {form.instance.user.first_name}, votre rendez-vous pour tester la "
                f"{form.instance.car.marque} {form.instance.car.modele} est confirmé pour le "
                f"{form.instance.reservation_date} à {form.instance.reservation_time}."
            )

            send_mail(
                subject=subject,
                message=message,
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
                recipient_list=[form.instance.user.email],
                fail_silently=False,
            )
        except Exception as e:
            print(f"Erreur lors de l'envoi de l'email : {e}")

        return response


# class TestDriveList(LoginRequiredMixin,ListView):
#     model = TestDrive
#     context_object_name = "testdrives" 
#     template_name = "TestDrive/liste_testdrive.html"

class TestDriveList(LoginRequiredMixin, ListView):
    model = TestDrive
    template_name = "TestDrive/liste_testdrive.html"
    context_object_name = "testdrives"  
    paginate_by = 10

    def get_queryset(self):
        qs = super().get_queryset().select_related("car", "user").order_by("-reservation_date", "-reservation_time")
        qs = qs.filter(user=self.request.user)

        q = self.request.GET.get("q", "").strip()
        status = self.request.GET.get("status", "").strip()
        sort = self.request.GET.get("sort", "").strip()

        if q:
            qs = qs.filter(
                Q(car__marque__icontains=q) |
                Q(car__modele__icontains=q) |
                Q(test_location__icontains=q)
            )

        if status in {"not_done", "done", "cancelled"}:
            qs = qs.filter(status=status)

        if sort == "date_asc":
            qs = qs.order_by("reservation_date", "reservation_time")
        elif sort == "date_desc":
            qs = qs.order_by("-reservation_date", "-reservation_time")

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['q'] = self.request.GET.get('q', '')
        context['status'] = self.request.GET.get('status', '')
        context['sort'] = self.request.GET.get('sort', '')

        query_params = self.request.GET.copy()
        if 'page' in query_params:
            query_params.pop('page')
        context['querystring'] = f"&{query_params.urlencode()}" if query_params else ""
        return context
class TestDriveDetails(DetailView):
    model=TestDrive
    context_object_name="testdrive"
    template_name="TestDrive/details_testdrive.html"
class TestDriveUpdate(UpdateView):
    model=TestDrive
    template_name="TestDrive/update_testdrive.html"
    # fields="__all__"
    success_url = reverse_lazy("TestDrive:liste_testdrive")
    form_class=TestDriveUpdateForm
@staff_member_required
def admin_testdrive_list(request):
    qs = TestDrive.objects.select_related("user", "car").all()

    status = request.GET.get("status")
    q = request.GET.get("q")

    if status in {"done", "not_done", "cancelled"}:
        qs = qs.filter(status=status)

    if q:
        qs = qs.filter(
            Q(car__marque__icontains=q) |
            Q(car__modele__icontains=q) |
            Q(user__first_name__icontains=q) |
            Q(test_location__icontains=q)
        )

    sort = request.GET.get("sort", "")
    if sort == "date_asc":
        qs = qs.order_by("reservation_date", "reservation_time")
    elif sort == "date_desc":
        qs = qs.order_by("-reservation_date", "-reservation_time")
    else:
        qs = qs.order_by("-reservation_date", "-id_test_drive")

    paginator = Paginator(qs, 10)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(request, "TestDrive/admin_liste_testdrive.html", {
        "page_obj": page_obj,
        "status": status or "",
        "q": q or "",
        "sort": sort,
    })


def admin_testdrive_update(request, pk):
    t = get_object_or_404(TestDrive, pk=pk)

    if request.method == "POST":
        form = TestDriveUpdateForm(request.POST, instance=t)
        if form.is_valid():
            form.save()
            
            return redirect("TestDrive:admin_testdrive_list")  
    else:
        form = TestDriveUpdateForm(instance=t)

    return render(request, "TestDrive/admin_update_testdrive.html", {"form": form, "t": t})

def admin_testdrive_detail(request, pk):
    t = get_object_or_404(TestDrive, pk=pk)
    return render(request, "TestDrive/admin_detail_testdrive.html", {"t": t})


def admin_testdrive_delete(request, pk):
    t = get_object_or_404(TestDrive, pk=pk)

    if request.method == "POST":
        t.delete()
        return redirect("TestDrive:admin_testdrive_list")

    return render(request, "TestDrive/admin_delete_testdrive.html", {"t": t})
def admin_testdrive_add(request):
    if request.method == "POST":
        form = TestDriveForm(request.POST)
        if form.is_valid():
            testdrive = form.save(commit=False)
            testdrive.user = request.user 
            testdrive.save()
            messages.success(request, "Le test drive a été ajouté avec succès.")
            return redirect("TestDrive:admin_testdrive_list")
        else:
            messages.error(request, "Veuillez corriger les erreurs dans le formulaire.")
    else:
        form = TestDriveForm()

    return render(request, "TestDrive/admin_add_testdrive.html", {"form": form})




@staff_member_required
def admin_predict_testdrive(request, pk):
    if request.method != "POST":
        return JsonResponse({"error": "Méthode non autorisée"}, status=405)

    t = get_object_or_404(TestDrive, pk=pk)
    try:
        result = predictor.predict_binary(t)
        t.prediction = result["prediction"]
        t.probability = result["probability"]
        t.save()

        if result["prediction"] == 1:
            msg = f"⚠️ No-Show (probabilité {result['probability']:.1%})"
        else:
            msg = f"✅ Client fiable (risque {result['probability']:.1%})"

        return JsonResponse({"result": msg})

    except Exception as e:
        return JsonResponse({"result": f"⚠️ Erreur IA : {str(e)}"})