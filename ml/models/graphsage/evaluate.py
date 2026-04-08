from __future__ import annotations


def compute_metrics(y_true, y_pred_proba, threshold: float = 0.5) -> dict:
    """Compute AUC, Precision, Recall, F1, AP, Confusion Matrix."""
    raise NotImplementedError()


def plot_roc_curve(y_true, y_pred_proba, save_path: str):
    """Plot and save ROC curve."""
    raise NotImplementedError()


def plot_precision_recall_curve(y_true, y_pred_proba, save_path: str):
    """Plot and save PR curve."""
    raise NotImplementedError()


def plot_confusion_matrix(y_true, y_pred, save_path: str):
    """Plot and save confusion matrix."""
    raise NotImplementedError()


def generate_model_card(metrics: dict, training_config: dict) -> dict:
    """Generate model card with all metadata."""
    raise NotImplementedError()
