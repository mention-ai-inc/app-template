from typing import Annotated

from fastapi import Depends

from admin.server.audit import AdminAuditor
from admin.server.catalogue import BackfillCatalogue
from admin.server.jobs import JobLauncher
from control_plane.application.ports.logs import ILogReader
from control_plane.infrastructure.audit.publisher import AuditEventPublisher
from control_plane.providers.registry import get_cloud_provider


def get_auditor() -> AdminAuditor:
    return AdminAuditor(publisher=AuditEventPublisher())


def get_job_launcher() -> JobLauncher:
    return JobLauncher(job_runner=get_cloud_provider().job_runner())


def get_log_reader() -> ILogReader:
    return get_cloud_provider().log_reader()


def get_backfill_catalogue(
    launcher: Annotated[JobLauncher, Depends(get_job_launcher)],
    log_reader: Annotated[ILogReader, Depends(get_log_reader)],
) -> BackfillCatalogue:
    return BackfillCatalogue(launcher=launcher, log_reader=log_reader)
