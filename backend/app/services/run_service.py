"""生成任务服务 — 创建、状态流转、后台执行。"""

from sqlalchemy.orm import Session

from app.models.generation_run import GenerationRun
from app.schemas.requirement import AnalysisPayload
from app.services.agent_gateway import AgentGateway


class RunService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_run(self, project_id: str, task_type: str) -> GenerationRun:
        run = GenerationRun(
            project_id=project_id,
            task_type=task_type,
            status="pending",
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run

    def get_run(self, run_id: str) -> GenerationRun | None:
        return self.db.query(GenerationRun).filter(GenerationRun.id == run_id).first()

    def get_runs(self, project_id: str) -> list[GenerationRun]:
        return (
            self.db.query(GenerationRun)
            .filter(GenerationRun.project_id == project_id)
            .order_by(GenerationRun.created_at.desc())
            .all()
        )

    def start_run(self, run_id: str) -> None:
        run = self.get_run(run_id)
        if run:
            run.status = "running"
            self.db.commit()

    def complete_run(self, run_id: str, analysis_payload: AnalysisPayload | None = None, pricing_payload: dict | None = None) -> None:
        run = self.get_run(run_id)
        if run:
            run.status = "succeeded"
            if analysis_payload:
                run.analysis_payload = analysis_payload.model_dump()
            if pricing_payload:
                run.pricing_payload = pricing_payload
            self.db.commit()

    def fail_run(self, run_id: str, error: str) -> None:
        run = self.get_run(run_id)
        if run:
            run.status = "failed"
            run.error_message = error
            self.db.commit()

    def run_analysis(
        self,
        run_id: str,
        agent: AgentGateway,
        blocks: list | None = None,
        supplement: str | None = None,
    ) -> None:
        """执行分析任务（在后台线程中调用）。"""
        try:
            self.start_run(run_id)
            from app.schemas.requirement import SourceBlock
            source_blocks = [SourceBlock(**b) for b in blocks] if blocks else []
            payload = agent.analyze(source_blocks, supplement)
            self.complete_run(run_id, analysis_payload=payload)
        except Exception as exc:
            self.fail_run(run_id, error=str(exc))
