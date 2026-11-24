from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from apps.todos.models import Todo, TodoList
from apps.users.models import CustomUser


class TodoModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = CustomUser.objects.create_user(username="todos@example.com")
        cls.todo_list = TodoList.objects.create(user=cls.user, name="Chores")
        cls.today = timezone.localdate()

    def _todo(self, **kwargs) -> Todo:
        return Todo.objects.create(todo_list=self.todo_list, title="Take out the trash", **kwargs)

    def test_toggle_complete(self):
        todo = self._todo()
        self.assertFalse(todo.is_complete)
        todo.toggle_complete()
        todo.refresh_from_db()
        self.assertTrue(todo.is_complete)
        todo.toggle_complete()
        todo.refresh_from_db()
        self.assertFalse(todo.is_complete)

    def test_overdue_and_due_today(self):
        overdue = self._todo(due_date=self.today - timedelta(days=1))
        due_today = self._todo(due_date=self.today)
        undated = self._todo()
        self.assertTrue(overdue.is_overdue)
        self.assertFalse(overdue.is_due_today)
        self.assertFalse(due_today.is_overdue)
        self.assertTrue(due_today.is_due_today)
        self.assertFalse(undated.is_overdue)
        self.assertFalse(undated.is_due_today)

    def test_completed_todos_are_never_overdue(self):
        todo = self._todo(due_date=self.today - timedelta(days=1), completed_at=timezone.now())
        self.assertFalse(todo.is_overdue)
        self.assertEqual(0, Todo.objects.overdue(self.today).count())

    def test_default_ordering_puts_soonest_first_and_undated_last(self):
        undated = self._todo()
        later = self._todo(due_date=self.today + timedelta(days=5))
        sooner = self._todo(due_date=self.today)
        self.assertEqual([sooner, later, undated], list(Todo.objects.all()))

    def test_due_by_includes_overdue_but_not_completed_or_later(self):
        overdue = self._todo(due_date=self.today - timedelta(days=3))
        soon = self._todo(due_date=self.today + timedelta(days=2))
        self._todo(due_date=self.today + timedelta(days=30))
        self._todo(due_date=self.today, completed_at=timezone.now())
        self.assertEqual([overdue, soon], list(Todo.objects.due_by(self.today + timedelta(days=7))))

    def test_list_counts(self):
        self._todo()
        self._todo()
        self._todo(completed_at=timezone.now())
        TodoList.objects.create(user=self.user, name="Empty")
        counts = {
            todo_list.name: (todo_list.todo_count, todo_list.open_count, todo_list.completed_count)
            for todo_list in TodoList.objects.with_counts()
        }
        self.assertEqual({"Chores": (3, 2, 1), "Empty": (0, 0, 0)}, counts)
