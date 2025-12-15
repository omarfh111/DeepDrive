from django.urls import path

from .views import TestDriveCreate, TestDriveList,TestDriveDetails,TestDriveUpdate,admin_testdrive_list,admin_testdrive_update,admin_testdrive_detail,admin_testdrive_delete,admin_testdrive_add,admin_predict_testdrive

app_name = 'TestDrive'

urlpatterns = [
    path("add/", TestDriveCreate.as_view(), name="TestDrive_creation"),
    path("liste/", TestDriveList.as_view(), name="liste_testdrive"),
    path("<int:pk>/", TestDriveDetails.as_view(), name="testdrive_details"),
    path("edit/<int:pk>/", TestDriveUpdate.as_view(),name="TestDrive_update"),
    path("back/testdrive/liste", admin_testdrive_list, name="admin_testdrive_list"),
    path("back/testdrive/<int:pk>/edit", admin_testdrive_update, name="testdrive_edit"),
    path("back/testdrive/<int:pk>/detail", admin_testdrive_detail, name="testdrive_detail"),
    path("back/testdrive/<int:pk>/delete", admin_testdrive_delete, name="testdrive_delete"),
    path("back/testdrive/add/", admin_testdrive_add, name="admin_testdrive_add"),
    path("back/testdrive/<int:pk>/predict/", admin_predict_testdrive, name="testdrive_predict"),
]
