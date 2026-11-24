from django import forms
from django.utils.translation import gettext_lazy as _

from .models import Todo, TodoList


class DateInput(forms.DateInput):
    """A native browser date picker, which requires ISO-formatted values."""

    input_type = "date"

    def __init__(self, attrs: dict | None = None) -> None:
        super().__init__(attrs=attrs, format="%Y-%m-%d")


class TodoListForm(forms.ModelForm):
    class Meta:
        model = TodoList
        fields = ["name"]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "placeholder": _("List name, e.g. Groceries"),
                    "aria-label": _("List name"),
                    "class": "join-item",
                }
            ),
        }


class QuickTodoForm(forms.ModelForm):
    """The one-line form used to add a todo to a list."""

    class Meta:
        model = Todo
        fields = ["title", "due_date"]
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": _("What needs doing?"), "aria-label": _("Title")}),
            "due_date": DateInput(attrs={"aria-label": _("Due date")}),
        }


class TodoForm(forms.ModelForm):
    class Meta:
        model = Todo
        fields = ["title", "notes", "due_date"]
        widgets = {
            "title": forms.TextInput(attrs={"aria-label": _("Title"), "autofocus": True}),
            "notes": forms.Textarea(attrs={"rows": 2, "placeholder": _("Notes"), "aria-label": _("Notes")}),
            "due_date": DateInput(attrs={"aria-label": _("Due date")}),
        }
