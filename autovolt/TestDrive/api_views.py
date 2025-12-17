
from datetime import datetime, time, timedelta
import json

from django.conf import settings
from django.http import JsonResponse
from django.utils.crypto import constant_time_compare
from django.utils.dateparse import parse_date, parse_time
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST
from django.db import IntegrityError, transaction

from django.contrib.auth import get_user_model
from .models import TestDrive
from vehicles.models import Voiture

User = get_user_model()


def _generate_slots(date, start=time(9, 0), end=time(17, 0), step_min=30):
    cur = datetime.combine(date, start)
    end_dt = datetime.combine(date, end)
    out = []
    while cur < end_dt:
        out.append(cur.time().replace(second=0, microsecond=0))
        cur += timedelta(minutes=step_min)
    return out


@require_GET
def api_slots(request):
    car_id = request.GET.get("car_id")
    date_str = request.GET.get("date")

    if not car_id or not date_str:
        return JsonResponse({"error": "car_id and date are required"}, status=400)

    date = parse_date(date_str)
    if not date:
        return JsonResponse({"error": "invalid date (YYYY-MM-DD)"}, status=400)

    if not Voiture.objects.filter(id=car_id).exists():
        return JsonResponse({"error": "car not found"}, status=404)

    taken = set(
        TestDrive.objects.filter(car_id=car_id, reservation_date=date)
        .values_list("reservation_time", flat=True)
    )

    all_slots = _generate_slots(date)
    free_slots = [t.strftime("%H:%M") for t in all_slots if t not in taken]

    return JsonResponse({"car_id": int(car_id), "date": date_str, "free_slots": free_slots})


@csrf_exempt
@require_POST
def api_book(request):
    # 1) API Key auth (machine-to-machine)
    if not getattr(settings, "TESTDRIVE_API_KEY", None):
        return JsonResponse({"error": "server misconfigured: missing TESTDRIVE_API_KEY"}, status=500)

    api_key = request.headers.get("X-API-KEY", "")
    if not constant_time_compare(api_key, settings.TESTDRIVE_API_KEY):
        return JsonResponse({"error": "unauthorized"}, status=401)

    # 2) JSON parsing safe
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "invalid json"}, status=400)

    # 3) Required fields
    car_id = payload.get("car_id")
    date = parse_date(payload.get("date", ""))
    time_ = parse_time(payload.get("time", ""))

    user_id = payload.get("user_id")  # V1 obligatoire
    if not user_id:
        return JsonResponse({"error": "user_id required (V1)"}, status=400)

    if not (car_id and date and time_):
        return JsonResponse({"error": "car_id, date, time are required"}, status=400)

    # 4) Optional fields
    location = payload.get("location", "Tunis")
    phone = payload.get("contact_phone")
    license_no = payload.get("driver_license_number")
    comments = payload.get("comments", "")

    # 5) Validate references
    car = Voiture.objects.filter(id=car_id).first()
    if not car:
        return JsonResponse({"error": "car not found"}, status=404)

    user = User.objects.filter(id=user_id).first()
    if not user:
        return JsonResponse({"error": "user not found"}, status=404)

    # 6) Create atomically + handle UNIQUE constraint race conditions
    try:
        with transaction.atomic():
            td = TestDrive.objects.create(
                user=user,
                car=car,
                reservation_date=date,
                reservation_time=time_,
                test_location=location,
                contact_phone=phone,
                driver_license_number=license_no,
                comments=comments,
            )
    except IntegrityError:
        return JsonResponse({"error": "slot already taken"}, status=409)

    return JsonResponse({
        "ok": True,
        "id_test_drive": td.id_test_drive,
        "summary": f"{car.marque} {car.modele} le {date} à {time_}",
    })


@require_GET
def api_cars(request):
    qs = Voiture.objects.all().order_by("marque", "modele")[:500]
    data = [{"id": v.id, "marque": v.marque, "modele": v.modele} for v in qs]
    return JsonResponse({"cars": data})
