from django.urls import path

from . import views

app_name = "todos"
urlpatterns = [
    path("", views.list_index, name="list_index"),
    path("<int:list_id>/", views.list_detail, name="list_detail"),
    path("<int:list_id>/edit/", views.list_edit, name="list_edit"),
    path("<int:list_id>/delete/", views.list_delete, name="list_delete"),
    path("<int:list_id>/todos/", views.todo_panel, name="todo_panel"),
    path("<int:list_id>/todos/<int:todo_id>/edit/", views.todo_edit, name="todo_edit"),
    path("<int:list_id>/todos/<int:todo_id>/toggle/", views.todo_toggle, name="todo_toggle"),
    path("<int:list_id>/todos/<int:todo_id>/delete/", views.todo_delete, name="todo_delete"),
]
