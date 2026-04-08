from __future__ import annotations

from torch import nn
from torch.utils.data import DataLoader


def train_graphsage(
    data_path: str,
    neo4j_uri: str,
    output_dir: str,
    config: dict,
):
    """
    1. Load graph data from Neo4j (2-hop subgraphs around labeled nodes)
    2. Build PyG Data objects
    3. Split train/val/test (70/15/15, stratified by fraud label)
    4. Train GraphSAGE model
    5. Evaluate: AUC, Precision, Recall, F1, AP
    6. Save model + metadata to output_dir
    7. Log to MLflow
    """
    raise NotImplementedError()


def load_graph_data(neo4j_uri: str, account_ids: list, label_col: str):
    """Load 2-hop subgraphs from Neo4j as PyG Data object."""
    raise NotImplementedError()


def create_dataloaders(data, batch_size: int = 256) -> tuple:
    """Create train/val/test DataLoaders with NeighborSampler."""
    raise NotImplementedError()


def evaluate_model(model: nn.Module, loader: DataLoader) -> dict:
    """Evaluate model and return metrics dict."""
    raise NotImplementedError()
