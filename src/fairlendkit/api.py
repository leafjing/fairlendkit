"""Package composition root and pandas adapter for the public convenience API."""

import hashlib
import pandas as pd

from fairlendkit.application import PreparedAuditData, RunAudit
from fairlendkit.config import AuditConfig, DuplicatePolicy, ScoreDirection
from fairlendkit.data.validation import validate_audit_data
from fairlendkit.metrics.bootstrap import Sha256PercentileBootstrap
from fairlendkit.metrics.group import NormalizedAuditData
from fairlendkit.report.models import AuditResultV2


class PandasAuditDataAdapter:
    def prepare(self, data: object, config: AuditConfig) -> PreparedAuditData:
        if not isinstance(data, pd.DataFrame):
            raise TypeError("data must be a pandas DataFrame")
        validation = validate_audit_data(data, config)
        eligible = _eligible_frame(data, config)
        outcomes = tuple(_typed_equal(value, config.favorable_label) for value in eligible[config.outcome_column])
        decisions = (
            tuple(config.is_favorable_decision_score(value) for value in eligible[config.score_column])
            if config.decision_column is None
            else tuple(_typed_equal(value, config.favorable_decision_label) for value in eligible[config.decision_column])
        )
        raw_scores = tuple(float(value) for value in eligible[config.score_column])
        scores = raw_scores if config.score_direction == ScoreDirection.HIGHER_IS_MORE_FAVORABLE else tuple(1.0 - value for value in raw_scores)
        normalized = NormalizedAuditData(
            favorable_outcome=outcomes, favorable_decision=decisions, favorable_score=scores,
            protected_values={name: tuple(eligible[name]) for name in config.protected_attributes},
            weights=None if config.sample_weight_column is None else tuple(float(value) for value in eligible[config.sample_weight_column]),
        )
        return PreparedAuditData(validation, normalized, _fingerprint(data))


def run_audit(data: pd.DataFrame, config: AuditConfig) -> AuditResultV2:
    """Validate one dataframe and assemble one deterministic Schema 2.0 result."""

    return RunAudit(PandasAuditDataAdapter(), Sha256PercentileBootstrap())(data, config)


def _eligible_frame(data: pd.DataFrame, config: AuditConfig) -> pd.DataFrame:
    required = {config.outcome_column, config.score_column, *config.protected_attributes}
    required.update(x for x in (config.decision_column, config.sample_weight_column, config.record_id_column) if x)
    excluded = pd.Series(False, index=data.index)
    if config.missing_value_policy == "exclude":
        excluded |= data[list(required)].isna().any(axis=1)
    if config.unknown_group_policy == "exclude":
        for attribute in config.protected_attributes:
            excluded |= ~data[attribute].map(lambda value: any(_typed_equal(value, allowed) for allowed in config.allowed_groups[attribute]))
    if config.duplicate_policy == DuplicatePolicy.EXCLUDE:
        subset = [config.record_id_column] if config.record_id_column else list(data.columns)
        excluded |= data.duplicated(subset=subset, keep=False)
    return data.loc[~excluded].copy(deep=True)


def _typed_equal(left: object, right: object) -> bool:
    return type(left) is type(right) and left == right


def _fingerprint(data: pd.DataFrame) -> str:
    digest = hashlib.sha256()
    digest.update(repr(tuple(data.columns)).encode())
    digest.update(repr(tuple(str(dtype) for dtype in data.dtypes)).encode())
    digest.update(pd.util.hash_pandas_object(data, index=True).values.tobytes())
    return f"sha256:{digest.hexdigest()}"
