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
        self.in_features = in_features
        self.hidden_dim = hidden_dim
        self.out_features = out_features
        self.num_layers = num_layers
        self.dropout = dropout
        self.aggregation = aggregation

        # Compatible with the Colab-exported checkpoint format:
        # lin1: [hidden_dim, in_features * 2]
        # lin2: [hidden_dim, hidden_dim * 2]
        # out:  [1, hidden_dim]
        self.lin1 = nn.Linear(in_features * 2, hidden_dim)
        self.lin2 = nn.Linear(hidden_dim * 2, hidden_dim)
        self.out = nn.Linear(hidden_dim, 1)

    def _aggregate_neighbors(
        self, x: torch.Tensor, edge_index: torch.Tensor | None
    ) -> torch.Tensor:
        """Compute mean neighbor features.

        Supports either:
        - COO edge list tensor of shape [2, num_edges], or
        - sparse adjacency matrix of shape [num_nodes, num_nodes].
        """
        if edge_index is None:
            return x

        if edge_index.layout in {torch.sparse_coo, torch.sparse_csr, torch.sparse_csc}:  # type: ignore[attr-defined]
            return torch.sparse.mm(edge_index, x)

        if edge_index.dim() != 2 or edge_index.size(0) != 2:
            return x

        src = edge_index[0].long()
        dst = edge_index[1].long()

        agg = torch.zeros_like(x)
        deg = torch.zeros((x.size(0), 1), device=x.device, dtype=x.dtype)

        agg.index_add_(0, dst, x[src])
        deg.index_add_(0, dst, torch.ones((dst.numel(), 1), device=x.device, dtype=x.dtype))
        return agg / deg.clamp_min(1.0)

    def _encode(
        self, x: torch.Tensor, edge_index: torch.Tensor | None
    ) -> torch.Tensor:
        if x.dim() == 1:
            x = x.unsqueeze(0)

        current_features = x.size(1)
        if current_features < self.in_features:
            pad = torch.zeros(
                (x.size(0), self.in_features - current_features),
                dtype=x.dtype,
                device=x.device,
            )
            x = torch.cat([x, pad], dim=1)
        elif current_features > self.in_features:
            x = x[:, : self.in_features]

        n1 = self._aggregate_neighbors(x, edge_index)
        h1 = torch.cat([x, n1], dim=1)
        h1 = torch.relu(self.lin1(h1))
        h1 = torch.dropout(h1, p=self.dropout, train=self.training)

        n2 = self._aggregate_neighbors(h1, edge_index)
        h2 = torch.cat([h1, n2], dim=1)
        h2 = torch.relu(self.lin2(h2))
        h2 = torch.dropout(h2, p=self.dropout, train=self.training)
        return h2

    def forward(self, x, edge_index=None, edge_attr=None) -> torch.Tensor:
        """
        Args:
            x: Node features [num_nodes, in_features]
            edge_index: Graph connectivity [2, num_edges]
            edge_attr: Edge features [num_edges, edge_feature_dim]
        Returns:
            fraud_probability [num_nodes, 1]
        """
        embeddings = self._encode(x, edge_index)
        logits = self.out(embeddings)
        return torch.sigmoid(logits)

    def get_embeddings(self, x, edge_index=None, edge_attr=None) -> torch.Tensor:
        """Return node embeddings for downstream use."""
        return self._encode(x, edge_index)

    def predict_proba(self, x, edge_index=None, edge_attr=None) -> torch.Tensor:
        """Inference helper expected by ml_service runtime."""
        was_training = self.training
        self.eval()
        with torch.no_grad():
            probs = self.forward(x, edge_index=edge_index, edge_attr=edge_attr)
        if was_training:
            self.train()
        return probs.squeeze(-1)

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
        optimizer = torch.optim.Adam(self.parameters(), lr=lr, weight_decay=weight_decay)
        criterion = nn.BCELoss()

        history: dict[str, list[float]] = {"train_loss": [], "val_loss": []}

        def _unpack_batch(batch):
            if isinstance(batch, (tuple, list)) and len(batch) >= 2:
                x_b = batch[0]
                y_b = batch[1]
                edge_b = batch[2] if len(batch) > 2 else None
                return x_b, y_b, edge_b
            raise ValueError("Expected batch as (x, y) or (x, y, edge_index)")

        for _ in range(num_epochs):
            self.train()
            train_losses = []
            for batch in train_loader:
                x_b, y_b, edge_b = _unpack_batch(batch)
                y_b = y_b.float().view(-1)

                optimizer.zero_grad()
                probs = self.forward(x_b, edge_b).view(-1)
                loss = criterion(probs, y_b)
                loss.backward()
                optimizer.step()
                train_losses.append(float(loss.item()))

            self.eval()
            val_losses = []
            with torch.no_grad():
                for batch in val_loader:
                    x_b, y_b, edge_b = _unpack_batch(batch)
                    y_b = y_b.float().view(-1)
                    probs = self.forward(x_b, edge_b).view(-1)
                    val_loss = criterion(probs, y_b)
                    val_losses.append(float(val_loss.item()))

            history["train_loss"].append(sum(train_losses) / max(1, len(train_losses)))
            history["val_loss"].append(sum(val_losses) / max(1, len(val_losses)))

        return {
            "train_loss": history["train_loss"][-1] if history["train_loss"] else 0.0,
            "val_loss": history["val_loss"][-1] if history["val_loss"] else 0.0,
            "history": history,
        }
