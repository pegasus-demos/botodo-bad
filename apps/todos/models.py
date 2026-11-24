from datetime import date

from django.db import models
from django.db.models import Count, F, Q
from django.utils import timezone

from apps.users.models import CustomUser
from apps.utils.models import BaseModel


class TodoListQuerySet(models.QuerySet["TodoList"]):
    def with_counts(self) -> TodoListQuerySet:
        """Annotate each list with `todo_count`, `completed_count` and `open_count`."""
        return self.annotate(
            todo_count=Count("todo"),
            completed_count=Count("todo", filter=Q(todo__completed_at__isnull=False)),
            open_count=Count("todo", filter=Q(todo__completed_at__isnull=True)),
        )


class TodoList(BaseModel):
    """
    A named collection of todos belonging to a single user.
    """

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)

    objects = TodoListQuerySet.as_manager()

    class Meta:
        ordering = ["name", "id"]

    def __str__(self) -> str:
        return self.name


class TodoQuerySet(models.QuerySet["Todo"]):
    def for_user(self, user: CustomUser) -> TodoQuerySet:
        return self.filter(todo_list__user=user)

    def open(self) -> TodoQuerySet:
        return self.filter(completed_at__isnull=True)

    def completed(self) -> TodoQuerySet:
        return self.filter(completed_at__isnull=False)

    def due_by(self, day: date) -> TodoQuerySet:
        """Open todos due on or before the given day (including overdue ones)."""
        return self.open().filter(due_date__lte=day)

    def overdue(self, today: date) -> TodoQuerySet:
        return self.open().filter(due_date__lt=today)


class Todo(BaseModel):
    """
    A single task on a todo list. A todo is complete when `completed_at` is set.
    """

    todo_list = models.ForeignKey(TodoList, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    notes = models.TextField(blank=True)
    due_date = models.DateField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    objects = TodoQuerySet.as_manager()

    class Meta:
        # soonest due date first, todos with no due date last
        ordering = [F("due_date").asc(nulls_last=True), "created_at", "id"]

    def __str__(self) -> str:
        return self.title

    @property
    def is_complete(self) -> bool:
        return self.completed_at is not None

    @property
    def is_overdue(self) -> bool:
        return not self.is_complete and self.due_date is not None and self.due_date < timezone.localdate()

    @property
    def is_due_today(self) -> bool:
        return not self.is_complete and self.due_date == timezone.localdate()

    def toggle_complete(self) -> None:
        self.completed_at = None if self.is_complete else timezone.now()
        self.save(update_fields=["completed_at", "updated_at"])
