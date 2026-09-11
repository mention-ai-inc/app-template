from library.presentation.dependencies import get_unit_of_work, get_users_client
from library.presentation.jobs import run_job
from notes_service.presentation.dependencies.repositories import get_note_repository
from notes_service.presentation.dependencies.use_cases.notes import get_purge_notes_use_case


async def main_async() -> None:
    purge_notes_use_case = get_purge_notes_use_case(
        note_repository=get_note_repository(),
        users_client=get_users_client(),
        unit_of_work=get_unit_of_work(),
    )

    await purge_notes_use_case.execute()


def main() -> None:
    run_job(main_async)
