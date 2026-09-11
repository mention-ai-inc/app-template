from admin.server.audit import AdminAuditor
from admin.server.jobs import JobLauncher
from library.infrastructure.audit.publisher import AuditEventPublisher
from library.infrastructure.cloud.run import CloudRun


def get_auditor() -> AdminAuditor:
    return AdminAuditor(publisher=AuditEventPublisher())


def get_job_launcher() -> JobLauncher:
    return JobLauncher(cloud_run=CloudRun())
