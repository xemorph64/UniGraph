import structlog
from fastapi import APIRouter, Depends, HTTPException, Request

from ..auth.jwt_rbac import User, require_permission
from ..services.neo4j_service import neo4j_service

router = APIRouter()
logger = structlog.get_logger()


@router.post("/run")
async def run_graph_analytics(
    request: Request,
    user: User = Depends(require_permission("run:graph-analytics")),
):
    """Manually trigger Neo4j GDS analytics jobs."""
    logger.info(
        "graph_analytics_run_requested",
        actor_id=user.user_id,
        actor_role=user.role,
        client_host=request.client.host if request.client else None,
    )
    try:
        result = await neo4j_service.run_gds_analytics()
        await neo4j_service.create_audit_event(
            event_type="GRAPH_ANALYTICS_RUN",
            actor_id=user.user_id,
            actor_role=user.role,
            action="run_gds_analytics",
            status="SUCCESS",
            metadata={
                "graph": result.get("graph", {}),
                "pagerank": result.get("pagerank", {}),
                "louvain": result.get("louvain", {}),
                "betweenness": result.get("betweenness", {}),
            },
        )
        logger.info(
            "graph_analytics_run_succeeded",
            actor_id=user.user_id,
            actor_role=user.role,
            graph=result.get("graph", {}),
        )
        return {"status": "ok", "analytics_run": result}
    except Exception as exc:
        await neo4j_service.create_audit_event(
            event_type="GRAPH_ANALYTICS_RUN",
            actor_id=user.user_id,
            actor_role=user.role,
            action="run_gds_analytics",
            status="FAILED",
            metadata={"error": str(exc)},
        )
        logger.warning(
            "graph_analytics_run_failed",
            actor_id=user.user_id,
            actor_role=user.role,
            error=str(exc),
        )
        raise HTTPException(status_code=500, detail=f"GDS run failed: {exc}")


@router.get("/status")
async def get_graph_analytics_status(
    user: User = Depends(require_permission("read:graph-analytics")),
):
    """Return current coverage of PageRank/Louvain/Betweenness outputs."""
    try:
        logger.debug(
            "graph_analytics_status_requested",
            actor_id=user.user_id,
            actor_role=user.role,
        )
        status = await neo4j_service.get_gds_status()
        patterns = await neo4j_service.get_pattern_overview()
        return {
            "status": "ok",
            "gds": status,
            "patterns": patterns,
            "algorithms": ["PageRank", "Louvain", "Betweenness Centrality"],
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"GDS status fetch failed: {exc}")
