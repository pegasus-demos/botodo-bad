from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

from apps.users.models import CustomUser

from .forms import QuickTodoForm, TodoForm, TodoListForm
from .models import Todo, TodoList

DUE_SOON_DAYS = 7
MAX_DUE_SOON_TODOS = 10


def dashboard(request) -> HttpResponse:
    """The signed-in home page. Routed through `apps.web.views.home`, which handles anonymous users."""
    today = timezone.localdate()
    todos = Todo.objects.for_user(request.user)
    due_soon = todos.due_by(today + timedelta(days=DUE_SOON_DAYS)).select_related("todo_list")
    return render(
        request,
        "todos/dashboard.html",
        {
            "active_tab": "dashboard",
            "page_title": _("Dashboard"),
            "form": TodoListForm(),
            "todo_lists": TodoList.objects.filter(user=request.user).with_counts(),
            "due_soon_todos": due_soon[:MAX_DUE_SOON_TODOS],
            "open_count": todos.open().count(),
            "due_today_count": todos.open().filter(due_date=today).count(),
            "overdue_count": todos.overdue(today).count(),
            "completed_count": todos.completed().count(),
        },
    )


@login_required
def list_index(request) -> HttpResponse:
    form = TodoListForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        todo_list = form.save(commit=False)
        todo_list.user = request.user
        todo_list.save()
        return redirect("todos:list_detail", todo_list.pk)
    return render(
        request,
        "todos/list_index.html",
        {
            "active_tab": "lists",
            "page_title": _("My Lists"),
            "form": form,
            "todo_lists": TodoList.objects.filter(user=request.user).with_counts(),
        },
    )


@login_required
def list_detail(request, list_id: int) -> HttpResponse:
    todo_list = _get_list(request.user, list_id)
    return render(
        request,
        "todos/list_detail.html",
        {
            "active_tab": "lists",
            "page_title": todo_list.name,
            **_panel_context(todo_list),
        },
    )


@login_required
def list_edit(request, list_id: int) -> HttpResponse:
    todo_list = _get_list(request.user, list_id)
    form = TodoListForm(request.POST or None, instance=todo_list)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("todos:list_detail", todo_list.pk)
    return render(
        request,
        "todos/list_edit.html",
        {
            "active_tab": "lists",
            "page_title": _("Rename list"),
            "form": form,
            "todo_list": todo_list,
        },
    )


@login_required
@require_POST
def list_delete(request, list_id: int) -> HttpResponse:
    todo_list = _get_list(request.user, list_id)
    todo_list.delete()
    messages.success(request, _("Deleted “%(name)s”.") % {"name": todo_list.name})
    return redirect("todos:list_index")


@login_required
def todo_panel(request, list_id: int) -> HttpResponse:
    """GET renders a list's todos; POST adds a todo to the list first."""
    todo_list = _get_list(request.user, list_id)
    if request.method != "POST":
        return _render_panel(request, todo_list)
    form = QuickTodoForm(request.POST)
    if not form.is_valid():
        return _render_panel(request, todo_list, add_form=form)
    todo = form.save(commit=False)
    todo.todo_list = todo_list
    todo.save()
    return _render_panel(request, todo_list, focus_add_form=True)


@login_required
def todo_edit(request, list_id: int, todo_id: int) -> HttpResponse:
    """GET renders the list with this todo swapped for an edit form; POST saves it."""
    todo = _get_todo(request.user, list_id, todo_id)
    form = TodoForm(request.POST or None, instance=todo)
    if request.method == "POST" and form.is_valid():
        form.save()
        return _render_panel(request, todo.todo_list)
    return _render_panel(request, todo.todo_list, edit_form=form)


@login_required
@require_POST
def todo_toggle(request, list_id: int, todo_id: int) -> HttpResponse:
    todo = _get_todo(request.user, list_id, todo_id)
    todo.toggle_complete()
    return _render_panel(request, todo.todo_list)


@login_required
@require_POST
def todo_delete(request, list_id: int, todo_id: int) -> HttpResponse:
    todo = _get_todo(request.user, list_id, todo_id)
    todo.delete()
    return _render_panel(request, todo.todo_list)


def _get_list(user: CustomUser, list_id: int) -> TodoList:
    return get_object_or_404(TodoList, pk=list_id, user=user)


def _get_todo(user: CustomUser, list_id: int, todo_id: int) -> Todo:
    return get_object_or_404(Todo.objects.select_related("todo_list"), pk=todo_id, todo_list=_get_list(user, list_id))


def _render_panel(request, todo_list: TodoList, **context) -> HttpResponse:
    return render(request, "todos/components/todo_panel.html", _panel_context(todo_list, **context))


def _panel_context(
    todo_list: TodoList,
    add_form: QuickTodoForm | None = None,
    edit_form: TodoForm | None = None,
    focus_add_form: bool = False,
) -> dict:
    todos = Todo.objects.filter(todo_list=todo_list)
    add_form = add_form or QuickTodoForm()
    if focus_add_form:
        add_form.fields["title"].widget.attrs["autofocus"] = True
    return {
        "todo_list": todo_list,
        "open_todos": todos.open(),
        "completed_todos": todos.completed().order_by("-completed_at"),
        "add_form": add_form,
        "edit_form": edit_form,
    }
