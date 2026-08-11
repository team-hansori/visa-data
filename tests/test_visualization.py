"""시각화 유틸리티 스모크 테스트."""

import matplotlib

matplotlib.use("Agg")  # 헤드리스 환경에서 렌더링

import numpy as np
import pandas as pd
import pytest

from src.visualization.plots import plot_correlation_heatmap, plot_distribution, save_figure

# ── 픽스처 ─────────────────────────────────────────────────────────────────────


@pytest.fixture
def sample_df() -> pd.DataFrame:
    """수치형 컬럼 샘플 데이터."""
    np.random.seed(42)
    n = 100
    return pd.DataFrame(
        {
            "feature_a": np.random.randn(n),
            "feature_b": np.random.randn(n) * 2 + 1,
        }
    )


# ── 시각화 함수 테스트 ─────────────────────────────────────────────────────────


class TestPlotDistribution:
    def test_returns_figure_with_axes_per_column(self, sample_df):
        fig = plot_distribution(sample_df, ["feature_a", "feature_b"])
        assert len(fig.axes) >= 2


class TestPlotCorrelationHeatmap:
    def test_returns_figure(self, sample_df):
        fig = plot_correlation_heatmap(sample_df)
        assert len(fig.axes) >= 1


class TestSaveFigure:
    def test_creates_default_formats(self, sample_df, tmp_path):
        fig = plot_distribution(sample_df, ["feature_a"])
        out_path = tmp_path / "dist"
        save_figure(fig, out_path)
        assert (tmp_path / "dist.png").exists()
        assert (tmp_path / "dist.pdf").exists()

    def test_creates_requested_format_only(self, sample_df, tmp_path):
        fig = plot_distribution(sample_df, ["feature_a"])
        out_path = tmp_path / "dist_png_only"
        save_figure(fig, out_path, formats=["png"])
        assert (tmp_path / "dist_png_only.png").exists()
        assert not (tmp_path / "dist_png_only.pdf").exists()
