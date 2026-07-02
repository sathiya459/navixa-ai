import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.audit_job import AuditJobScope
from app.models.network_resource import NetworkResource
from app.models.resource_change import ResourceChange
from app.models.scheduled_discovery import ScheduledDiscovery
from app.watch.diff import ResourceSnapshot, compute_resource_diff


def _snapshots_for_job(db: Session, audit_job_id: uuid.UUID) -> list[ResourceSnapshot]:
    resources = (
        db.query(NetworkResource)
        .join(AuditJobScope, NetworkResource.audit_job_scope_id == AuditJobScope.id)
        .filter(AuditJobScope.audit_job_id == audit_job_id)
        .all()
    )
    return [
        ResourceSnapshot(resource_type=r.resource_type, native_id=r.native_id, attributes=r.attributes)
        for r in resources
    ]


def run_change_detection(
    db: Session, current_job_id: uuid.UUID, previous_job_id: uuid.UUID
) -> list[ResourceChange]:
    previous_snapshots = _snapshots_for_job(db, previous_job_id)
    current_snapshots = _snapshots_for_job(db, current_job_id)

    diff_entries = compute_resource_diff(previous_snapshots, current_snapshots)

    changes = [
        ResourceChange(
            audit_job_id=current_job_id,
            compared_to_audit_job_id=previous_job_id,
            resource_type=entry.resource_type,
            native_id=entry.native_id,
            change_type=entry.change_type,
            previous_attributes=entry.previous_attributes,
            current_attributes=entry.current_attributes,
        )
        for entry in diff_entries
    ]
    db.add_all(changes)
    db.commit()
    for change in changes:
        db.refresh(change)

    return changes


def list_changes(db: Session, audit_job_id: uuid.UUID) -> list[ResourceChange]:
    return db.query(ResourceChange).filter(ResourceChange.audit_job_id == audit_job_id).all()


def create_scheduled_discovery(
    db: Session,
    tenant_id: uuid.UUID,
    scope_ids: list[uuid.UUID],
    interval_minutes: int,
    hub_selection: list[str] | None,
    created_by: uuid.UUID,
) -> ScheduledDiscovery:
    schedule = ScheduledDiscovery(
        tenant_id=tenant_id,
        scope_ids=[str(s) for s in scope_ids],
        interval_minutes=interval_minutes,
        hub_selection=hub_selection,
        created_by=created_by,
        next_run_at=datetime.now(timezone.utc) + timedelta(minutes=interval_minutes),
    )
    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    return schedule


def list_scheduled_discoveries(db: Session, tenant_id: uuid.UUID | None = None) -> list[ScheduledDiscovery]:
    query = db.query(ScheduledDiscovery)
    if tenant_id:
        query = query.filter(ScheduledDiscovery.tenant_id == tenant_id)
    return query.all()


def delete_scheduled_discovery(db: Session, schedule_id: uuid.UUID) -> bool:
    schedule = db.get(ScheduledDiscovery, schedule_id)
    if schedule is None:
        return False
    db.delete(schedule)
    db.commit()
    return True


def get_due_schedules(db: Session) -> list[ScheduledDiscovery]:
    now = datetime.now(timezone.utc)
    return (
        db.query(ScheduledDiscovery)
        .filter(ScheduledDiscovery.is_active.is_(True), ScheduledDiscovery.next_run_at <= now)
        .all()
    )


def mark_schedule_run(db: Session, schedule: ScheduledDiscovery) -> None:
    now = datetime.now(timezone.utc)
    schedule.last_run_at = now
    schedule.next_run_at = now + timedelta(minutes=schedule.interval_minutes)
    db.commit()
