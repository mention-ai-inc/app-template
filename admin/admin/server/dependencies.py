from admin.server.audit import AdminAuditor
from admin.server.jobs import JobLauncher
from library.infrastructure.audit.publisher import AuditEventPublisher
from library.providers.registry import get_cloud_provider


def get_auditor() -> AdminAuditor:
    return AdminAuditor(publisher=AuditEventPublisher())


def get_job_launcher() -> JobLauncher:
    return JobLauncher(job_runner=get_cloud_provider().job_runner())
