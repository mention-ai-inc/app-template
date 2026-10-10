from admin.server.audit import AdminAuditor
from admin.server.jobs import JobLauncher
from control_plane.infrastructure.audit.publisher import AuditEventPublisher
from control_plane.providers.registry import get_cloud_provider


def get_auditor() -> AdminAuditor:
    return AdminAuditor(publisher=AuditEventPublisher())


def get_job_launcher() -> JobLauncher:
    return JobLauncher(job_runner=get_cloud_provider().job_runner())
