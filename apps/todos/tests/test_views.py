from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.todos.models import Todo, TodoList
from apps.users.models import CustomUser


class TodoViewTestBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = CustomUser.objects.create_user(username="me@example.com")
        cls.todo_list = TodoList.objects.create(user=cls.user, name="Chores")
        cls.todo = Todo.objects.create(todo_list=cls.todo_list, title="Water the plants")

    def setUp(self):
        self.client.force_login(self.user)

    def _url(self, name: str, *args) -> str:
        return reverse(f"todos:{name}", args=args)


class TodoListViewTest(TodoViewTestBase):
    def test_login_required(self):
        self.client.logout()
        for url in [self._url("list_index"), self._url("list_detail", self.todo_list.pk)]:
            self.assertRedirects(self.client.get(url), f"/accounts/login/?next={url}")

    def test_index_shows_only_my_lists(self):
        TodoList.objects.create(user=CustomUser.objects.create_user(username="other@example.com"), name="Secrets")
        response = self.client.get(self._url("list_index"))
        self.assertContains(response, "Chores")
        self.assertNotContains(response, "Secrets")

    def test_create_list(self):
        response = self.client.post(self._url("list_index"), {"name": "Groceries"})
        todo_list = TodoList.objects.get(name="Groceries")
        self.assertEqual(self.user, todo_list.user)
        self.assertRedirects(response, self._url("list_detail", todo_list.pk))

    def test_detail(self):
        response = self.client.get(self._url("list_detail", self.todo_list.pk))
        self.assertContains(response, "Chores")
        self.assertContains(response, "Water the plants")

    def test_rename_list(self):
        response = self.client.post(self._url("list_edit", self.todo_list.pk), {"name": "Housework"})
        self.assertRedirects(response, self._url("list_detail", self.todo_list.pk))
        self.todo_list.refresh_from_db()
        self.assertEqual("Housework", self.todo_list.name)

    def test_delete_list(self):
        response = self.client.post(self._url("list_delete", self.todo_list.pk))
        self.assertRedirects(response, self._url("list_index"))
        self.assertFalse(TodoList.objects.exists())
        self.assertFalse(Todo.objects.exists())

    def test_delete_requires_post(self):
        response = self.client.get(self._url("list_delete", self.todo_list.pk))
        self.assertEqual(405, response.status_code)
        self.assertTrue(TodoList.objects.exists())


class TodoViewTest(TodoViewTestBase):
    def test_add_todo(self):
        due_date = timezone.localdate() + timedelta(days=1)
        response = self.client.post(
            self._url("todo_panel", self.todo_list.pk), {"title": "Mow the lawn", "due_date": due_date.isoformat()}
        )
        self.assertContains(response, "Mow the lawn")
        todo = Todo.objects.get(title="Mow the lawn")
        self.assertEqual(self.todo_list, todo.todo_list)
        self.assertEqual(due_date, todo.due_date)

    def test_add_todo_requires_title(self):
        response = self.client.post(self._url("todo_panel", self.todo_list.pk), {"title": ""})
        self.assertContains(response, "This field is required")
        self.assertEqual(1, Todo.objects.count())

    def test_toggle_todo(self):
        url = self._url("todo_toggle", self.todo_list.pk, self.todo.pk)
        self.client.post(url)
        self.todo.refresh_from_db()
        self.assertTrue(self.todo.is_complete)
        self.client.post(url)
        self.todo.refresh_from_db()
        self.assertFalse(self.todo.is_complete)

    def test_edit_todo(self):
        url = self._url("todo_edit", self.todo_list.pk, self.todo.pk)
        self.assertContains(self.client.get(url), 'value="Water the plants"')
        self.client.post(url, {"title": "Water the ferns", "notes": "Not the cactus", "due_date": ""})
        self.todo.refresh_from_db()
        self.assertEqual("Water the ferns", self.todo.title)
        self.assertEqual("Not the cactus", self.todo.notes)

    def test_delete_todo(self):
        response = self.client.post(self._url("todo_delete", self.todo_list.pk, self.todo.pk))
        self.assertEqual(200, response.status_code)
        self.assertFalse(Todo.objects.exists())


class TodoPermissionTest(TodoViewTestBase):
    """Another user's lists and todos should look like they don't exist."""

    def setUp(self):
        self.client.force_login(CustomUser.objects.create_user(username="intruder@example.com"))

    def test_cannot_view_or_change_list(self):
        for name in ["list_detail", "list_edit", "todo_panel"]:
            self.assertEqual(404, self.client.get(self._url(name, self.todo_list.pk)).status_code, name)
        for name in ["list_edit", "list_delete", "todo_panel"]:
            response = self.client.post(self._url(name, self.todo_list.pk), {"name": "Mine now", "title": "Hi"})
            self.assertEqual(404, response.status_code, name)
        self.todo_list.refresh_from_db()
        self.assertEqual("Chores", self.todo_list.name)
        self.assertEqual(1, Todo.objects.count())

    def test_cannot_change_todo(self):
        for name in ["todo_edit", "todo_toggle", "todo_delete"]:
            response = self.client.post(self._url(name, self.todo_list.pk, self.todo.pk), {"title": "Hacked"})
            self.assertEqual(404, response.status_code, name)
        self.todo.refresh_from_db()
        self.assertEqual("Water the plants", self.todo.title)
        self.assertFalse(self.todo.is_complete)

    def test_cannot_reach_todo_through_own_list(self):
        my_list = TodoList.objects.create(user=CustomUser.objects.get(username="intruder@example.com"), name="Mine")
        response = self.client.post(self._url("todo_toggle", my_list.pk, self.todo.pk))
        self.assertEqual(404, response.status_code)


class DashboardTest(TodoViewTestBase):
    def test_empty_dashboard_prompts_for_first_list(self):
        self.client.force_login(CustomUser.objects.create_user(username="new@example.com"))
        response = self.client.get(reverse("web:home"))
        self.assertContains(response, "Create your first list")

    def test_dashboard_counts_only_my_todos(self):
        today = timezone.localdate()
        Todo.objects.create(todo_list=self.todo_list, title="Pay rent", due_date=today)
        Todo.objects.create(todo_list=self.todo_list, title="File taxes", due_date=today - timedelta(days=2))
        Todo.objects.create(todo_list=self.todo_list, title="Plan trip", due_date=today + timedelta(days=60))
        Todo.objects.create(todo_list=self.todo_list, title="Buy stamps", completed_at=timezone.now())
        other_list = TodoList.objects.create(user=CustomUser.objects.create_user(username="other@example.com"))
        Todo.objects.create(todo_list=other_list, title="Not mine", due_date=today)

        response = self.client.get(reverse("web:home"))
        self.assertEqual(4, response.context["open_count"])
        self.assertEqual(1, response.context["due_today_count"])
        self.assertEqual(1, response.context["overdue_count"])
        self.assertEqual(1, response.context["completed_count"])
        self.assertEqual(["File taxes", "Pay rent"], [todo.title for todo in response.context["due_soon_todos"]])
        self.assertNotContains(response, "Not mine")
