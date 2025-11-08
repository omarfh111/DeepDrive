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


# @login_required
# def testdrive_list(request):
#     user = request.user 
#     testdrives = TestDrive.objects.filter(user=user)
#     return render(request, "TestDrive/testdrive_list.html", {
#         "testdrives": testdrives,
#     })


class TestDriveCreate(CreateView):
    model = TestDrive
    form_class = TestDriveForm
    template_name = 'TestDrive/add_testdrive.html'
    success_url = reverse_lazy("liste_testdrive")

    def form_valid(self, form):
        form.instance.user = self.request.user
        response = super().form_valid(form)
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
    ordering = ["-reservation_date", "-reservation_time"]

    def get_queryset(self):
        qs = super().get_queryset().filter(user=self.request.user)

        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(car__marque__icontains=q) |
                Q(car__modele__icontains=q)
            )

        status = self.request.GET.get("status", "").strip()
        if status:
            qs = qs.filter(status=status)

        return qs.select_related("car")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["q"] = self.request.GET.get("q", "")
        context["status"] = self.request.GET.get("status", "")
        context["status_choices"] = TestDrive.STATUS_CHOICES
        return context

class TestDriveDetails(DetailView):
    model=TestDrive
    context_object_name="testdrive"
    template_name="TestDrive/details_testdrive.html"
class TestDriveUpdate(UpdateView):
    model=TestDrive
    template_name="TestDrive/update_testdrive.html"
    # fields="__all__"
    success_url = reverse_lazy("liste_testdrive")
    form_class=TestDriveUpdateForm
@staff_member_required
def admin_testdrive_list(request):
    qs = TestDrive.objects.select_related("user", "car").all().order_by("-reservation_date", "-id_test_drive")

    status = request.GET.get("status")
    q = request.GET.get("q")

    if status in {"done", "not_done", "cancelled"}:
        qs = qs.filter(status=status)

    if q:
        qs = qs.filter(
            Q(car__marque__icontains=q)
            | Q(car__modele__icontains=q)
            | Q(user__username__icontains=q)
        )

    paginator = Paginator(qs, 10)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(request, "TestDrive/admin_liste_testdrive.html", {
        "page_obj": page_obj,
        "status": status or "",
        "q": q or "",
    })

def admin_testdrive_update(request, pk):
    t = get_object_or_404(TestDrive, pk=pk)

    if request.method == "POST":
        form = TestDriveUpdateForm(request.POST, instance=t)
        if form.is_valid():
            form.save()
            
            return redirect("admin_testdrive_list")  
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
        return redirect("admin_testdrive_list")

    return render(request, "TestDrive/admin_delete_testdrive.html", {"t": t})
def admin_testdrive_add(request):
    if request.method == "POST":
        form = TestDriveForm(request.POST)
        if form.is_valid():
            testdrive = form.save(commit=False)
            testdrive.user = request.user 
            testdrive.save()
            messages.success(request, "Le test drive a été ajouté avec succès.")
            return redirect("admin_testdrive_list")
        else:
            messages.error(request, "Veuillez corriger les erreurs dans le formulaire.")
    else:
        form = TestDriveForm()

    return render(request, "TestDrive/admin_add_testdrive.html", {"form": form})