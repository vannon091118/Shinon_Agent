"""Provider deployment registry with capability-gated multi-candidate resolution."""

from __future__ import annotations

from dataclasses import dataclass, field

from limen.adapters.openai import OpenAICompatibleAdapter
from limen.config import LimenConfig, ModelConfig, ProviderConfig  # noqa: TC001
from limen.routing.key_pool import KeyPool


@dataclass
class ProviderDeployment:
    """Resolved deployment binding used by the dispatcher.

    Unlike Phase 1 this is **not** frozen — the ``pool`` mutates at
    runtime as keys enter/leave cooldown.
    """

    provider: str
    deployment: str
    base_url: str
    model: str
    adapter: OpenAICompatibleAdapter
    priority: int
    capabilities: tuple[str, ...] = field(default_factory=tuple)
    free: bool = False
    max_context_tokens: int = 128_000
    escalation_group: str = "default"
    limit_scope: str = "unknown"
    account_id: str = ""
    pool: KeyPool = field(default_factory=lambda: KeyPool("", []))

    @property
    def aggregated_status(self) -> str:
        """Aggregate deployment status: active | cooldown | dead."""
        if self.pool.active_count > 0 or self.pool.total_count == 0:
            return "active"
        if self.pool.cooldown_count > 0:
            return "cooldown"
        if self.pool.dead_count > 0:
            return "dead"
        return "dead"


class ProviderRegistry:
    """Single source of truth for enabled deployments, sorted by priority."""

    def __init__(self, config: LimenConfig) -> None:
        self._config = config
        deployments: list[ProviderDeployment] = []
        for name, provider_config in config.providers.items():
            if not provider_config.enabled:
                continue
            configured_models = [
                (model_name, model_config)
                for model_name, model_config in config.models.items()
                if model_config.enabled and model_config.provider == name
            ]
            if configured_models:
                for model_name, model_config in configured_models:
                    deployments.append(
                        self._build_deployment(
                            name,
                            provider_config,
                            model_config.model_id,
                            model_config=model_config,
                            model_name=model_name,
                        )
                    )
            else:
                models = provider_config.models if provider_config.models else [""]
                for model in models:
                    deployments.append(self._build_deployment(name, provider_config, model))
        self._deployments: tuple[ProviderDeployment, ...] = tuple(
            sorted(deployments, key=lambda d: (d.priority, d.deployment))
        )

    @staticmethod
    def _build_deployment(
        name: str,
        provider: ProviderConfig,
        model: str = "",
        *,
        model_config: ModelConfig | None = None,
        model_name: str | None = None,
    ) -> ProviderDeployment:
        deployment_name = (
            f"{name}#{model_name}"
            if model_name
            else f"{name}#{model}" if model else name
        )
        priority = (
            model_config.priority
            if model_config and model_config.priority is not None
            else provider.priority
        )
        capabilities = (
            model_config.capabilities
            if model_config and model_config.capabilities
            else provider.capabilities
        )
        return ProviderDeployment(
            provider=name,
            deployment=deployment_name,
            base_url=provider.base_url,
            model=model,
            adapter=OpenAICompatibleAdapter(
                provider=name,
                deployment_name=deployment_name,
                model=model,
                base_url=provider.base_url,
                api_keys=list(provider.keys),
                capabilities=list(capabilities),
            ),
            priority=priority,
            capabilities=tuple(capabilities),
            free=model_config.free if model_config else False,
            max_context_tokens=(
                model_config.max_context_tokens if model_config else 128_000
            ),
            escalation_group=(
                model_config.escalation_group if model_config else "default"
            ),
            limit_scope=provider.limit_scope,
            account_id=provider.account_id,
            pool=KeyPool(deployment_name, provider.keys),
        )

    @property
    def deployments(self) -> tuple[ProviderDeployment, ...]:
        return self._deployments

    def resolve(
        self,
        requested_model: str,
        *,
        required_capabilities: tuple[str, ...] = ("chat",),
        min_context_tokens: int = 0,
    ) -> list[ProviderDeployment]:
        """Return enabled candidate deployments matching model and capabilities.

        When *requested_model* is ``"auto"``, all capability-matching
        deployments are returned in priority order.  Any model that no
        deployment advertises is also treated as ``auto`` — this lets CLI
        agents send arbitrary model IDs (Claude, GPT, …) without LIMEN
        needing a hardcoded alias list.

        Deployments whose ``max_context_tokens`` < *min_context_tokens* are
        skipped.  Free deployments are sorted before paid ones.
        """
        auto = requested_model == "auto"
        if not auto:
            has_exact = any(
                d.model == requested_model for d in self._deployments
            )
            auto = not has_exact
        candidates: list[ProviderDeployment] = []
        for deployment in self._deployments:
            if not deployment.model and not auto:
                continue
            if not auto and deployment.model != requested_model:
                continue
            if not set(required_capabilities).issubset(set(deployment.capabilities)):
                continue
            if min_context_tokens > 0 and deployment.max_context_tokens < min_context_tokens:
                continue
            candidates.append(deployment)
        # Sort free deployments first (free=True before free=False), then by priority
        candidates.sort(key=lambda d: (not d.free, d.priority, d.deployment))
        if not candidates:
            raise NoMatchingDeployment(requested_model)
        return candidates


class NoMatchingDeployment(Exception):  # noqa: N818 — internal sentinel.
    """Raised when no enabled deployment advertises the requested model."""

    def __init__(self, requested_model: str) -> None:
        super().__init__(f"no enabled deployment for model {requested_model!r}")
        self.requested_model = requested_model
