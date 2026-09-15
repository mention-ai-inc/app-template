from collections.abc import Callable
from datetime import UTC, datetime

from library.application.ports.taskqueue import ITaskQueue
from tests.application.ports.conformance.providers import RecordedTask

SERVICE = "notes"
TASK = "reindex"
SCHEDULED_TIME = datetime(2026, 1, 1, tzinfo=UTC)


class TestTaskUrls:
    def test_the_url_names_the_service_and_the_task(self, task_queue: ITaskQueue) -> None:
        url = task_queue.get_url(service=SERVICE, task=TASK)

        assert SERVICE in url
        assert url.endswith(TASK)

    def test_params_become_a_query_string_on_the_same_url(self, task_queue: ITaskQueue) -> None:
        without_params = task_queue.get_url(service=SERVICE, task=TASK)

        with_params = task_queue.get_url(service=SERVICE, task=TASK, params={"page": "2"})

        assert with_params == f"{without_params}?page=2"


class TestEnqueueing:
    async def test_add_task_records_the_task(
        self, task_queue: ITaskQueue, read_recorded_tasks: Callable[[], list[RecordedTask]]
    ) -> None:
        await task_queue.add_task(service=SERVICE, task=TASK, body={"note_id": "note_1"})

        recorded = read_recorded_tasks()
        assert [(task.service, task.task) for task in recorded] == [(SERVICE, TASK)]
        assert recorded[0].body == {"note_id": "note_1"}

    async def test_add_task_records_params_headers_and_schedule(
        self, task_queue: ITaskQueue, read_recorded_tasks: Callable[[], list[RecordedTask]]
    ) -> None:
        await task_queue.add_task(
            service=SERVICE,
            task=TASK,
            body={},
            params={"page": "2"},
            headers={"x-request-id": "req_1"},
            scheduled_time=SCHEDULED_TIME,
        )

        recorded = read_recorded_tasks()[0]
        assert recorded.params == {"page": "2"}
        assert recorded.headers == {"x-request-id": "req_1"}
        assert recorded.scheduled_time == SCHEDULED_TIME

    async def test_every_task_is_recorded_in_the_order_it_was_added(
        self, task_queue: ITaskQueue, read_recorded_tasks: Callable[[], list[RecordedTask]]
    ) -> None:
        await task_queue.add_task(service=SERVICE, task=TASK, body={"order": 1})
        await task_queue.add_task(service=SERVICE, task=TASK, body={"order": 2})

        assert [task.body["order"] for task in read_recorded_tasks()] == [1, 2]
