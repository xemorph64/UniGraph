from __future__ import annotations

import torch
import torch.nn as nn
from torch.utils.data import DataLoader


class GraphSAGEFraudDetector(nn.Module):
    def __init__(
        self,
        in_features: int = 32,
        hidden_dim: int = 128,
        out_features: int = 64,
        num_layers: int = 3,
        dropout: float = 0.3,
        aggregation: str = "mean",
    ):
        super().__init__()
        # 3-layer GraphSAGE with mean aggregation
        # Output: fraud probability (0-1)

    def forward(self, x, edge_index, edge_attr) -> torch.Tensor:
        """
        Args:
            x: Node features [num_nodes, in_features]
            edge_index: Graph connectivity [2, num_edges]
            edge_attr: Edge features [num_edges, edge_feature_dim]
        Returns:
            fraud_probability [num_nodes, 1]
        """
        raise NotImplementedError()

    def get_embeddings(self, x, edge_index, edge_attr) -> torch.Tensor:
        """Return node embeddings for downstream use."""
        raise NotImplementedError()

    def train_model(
        self,
        train_loader: DataLoader,
        val_loader: DataLoader,
        num_epochs: int = 50,
        lr: float = 0.001,
        weight_decay: float = 1e-5,
    ) -> dict:
        """
        Training loop with:
        - Focal loss (gamma=2) for class imbalance
        - Early stopping on validation AUC
        - Learning rate scheduling
        Returns training metrics dict.
        """
        raise NotImplementedError()
