from django.contrib import admin

from .models import Todo, TodoList


@admin.register(TodoList)
class TodoListAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "created_at")
    search_fields = ("name", "user__email")
    autocomplete_fields = ("user",)


@admin.register(Todo)
class TodoAdmin(admin.ModelAdmin):
    list_display = ("title", "todo_list", "due_date", "completed_at", "created_at")
    list_filter = ("due_date", "completed_at")
    search_fields = ("title", "notes")
    autocomplete_fields = ("todo_list",)
