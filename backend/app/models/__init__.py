"""Importing this package (which happens automatically whenever any
`app.models.<module>` submodule is imported, since Python must import the
parent package first) registers every model with SQLAlchemy's declarative
registry. Several models reference each other via string-based
relationship() targets (e.g. UserRole.user = relationship("User", ...)),
which only resolve if the referenced class has actually been imported
somewhere by the time the mapper configures itself - so partial imports
(e.g. `from app.models.role import Role` alone) previously failed with
"failed to locate a name" errors for models like AuditJob, Finding, etc.
that aren't imported by every entrypoint that touches the ORM.
"""

from app.models.ai_insight import AIInsight  # noqa: F401
from app.models.audit_job import AuditJob, AuditJobScope, ResourceCollectionStatusRow  # noqa: F401
from app.models.cloud_tenant import CloudScope, CloudTenant  # noqa: F401
from app.models.finding import Finding  # noqa: F401
from app.models.network_resource import NetworkResource  # noqa: F401
from app.models.report import Report  # noqa: F401
from app.models.resource_change import ResourceChange  # noqa: F401
from app.models.role import Role, UserRole  # noqa: F401
from app.models.scheduled_discovery import ScheduledDiscovery  # noqa: F401
from app.models.user import User  # noqa: F401
