import mlflow
from mlflow.entities import ViewType
from typing import Dict

from app.config.config import get_settings

settings = get_settings()

def log_evaluation_results(model_name: str, metrics: Dict[str, float]) -> None:
    print(f"🪵 Logging to MLflow: {model_name} with metrics {list(metrics.keys())}")

    if settings.MLFLOW_TRACKING_URI:
        mlflow.set_tracking_uri(settings.MLFLOW_TRACKING_URI)
    experiment_name = "model_evaluation"
    mlflow.set_experiment(experiment_name)

    experiment = mlflow.get_experiment_by_name(experiment_name)
    runs = mlflow.search_runs(
        experiment_ids=[experiment.experiment_id],
        filter_string=f"params.model_name = '{model_name}'",
        run_view_type=ViewType.ACTIVE_ONLY
    )

    if runs.empty:
        run = mlflow.start_run(run_name=model_name)
        mlflow.log_param("model_name", model_name)
    else:
        run_id = runs.iloc[0].run_id
        run = mlflow.start_run(run_id=run_id)

    for key, value in metrics.items():
        mlflow.log_metric(key, value)

    mlflow.end_run()

