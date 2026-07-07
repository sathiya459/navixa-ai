import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import require_role
from app.collectors.job_service import get_audit_job, get_job_network_resources
from app.database.session import get_db
from app.graph_engine.queries import get_job_topology, get_node_neighbors, get_shortest_paths
from app.graph_engine.session import get_driver
from app.graph_engine.writer import resources_to_graph_inputs, sync_job_to_graph
from app.models.role import ADMIN, READER
from app.models.user import User
from app.schemas.graph import PathResponse, SubgraphResponse, TopologyResponse

router = APIRouter(prefix="/graph", tags=["Graph"])


@router.get("/jobs/{job_id}/topology", response_model=TopologyResponse)
def get_topology(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_role(ADMIN, READER)),
) -> TopologyResponse:
    if get_audit_job(db, job_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return get_job_topology(get_driver(), job_id)


@router.post("/jobs/{job_id}/sync", response_model=TopologyResponse)
def sync_topology(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_role(ADMIN)),
) -> TopologyResponse:
    """Re-pushes this job's already-collected Postgres inventory into
    Neo4j. Lets jobs synced before graph_engine changes (or never synced
    at all) get their topology backfilled without re-running Discover.
    """
    audit_job = get_audit_job(db, job_id)
    if audit_job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    resources = get_job_network_resources(db, job_id)
    graph_inputs = resources_to_graph_inputs(resources)
    hub_ids = (audit_job.hub_selection or {}).get("hub_ids", [])
    try:
        sync_job_to_graph(graph_inputs, job_id, audit_job.tenant_id, hub_ids)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    return get_job_topology(get_driver(), job_id)


@router.get("/jobs/{job_id}/nodes/{node_id}/neighbors", response_model=SubgraphResponse)
def get_neighbors(
    job_id: uuid.UUID,
    node_id: str,
    depth: int = 1,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_role(ADMIN, READER)),
) -> SubgraphResponse:
    if get_audit_job(db, job_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return get_node_neighbors(get_driver(), node_id, depth)


@router.get("/jobs/{job_id}/paths", response_model=list[PathResponse])
def get_paths(
    job_id: uuid.UUID,
    source_id: str,
    target_id: str,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_role(ADMIN, READER)),
) -> list[PathResponse]:
    if get_audit_job(db, job_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    paths = get_shortest_paths(get_driver(), source_id, target_id)
    return [PathResponse(nodes=path) for path in paths]
