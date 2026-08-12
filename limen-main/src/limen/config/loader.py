"""Validated TOML configuration for the local LIMEN process."""

from __future__ import annotations

import json
import os
import re
import stat
import tomllib
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from os import PathLike

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

_ENV_VAR_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


def _resolve_env_vars(value: str) -> str:
    """Replace ``${VAR_NAME}`` placeholders with environment variable values.

    Falls back to ``~/.limen/keys.json`` if the env var is not set.
    Unknown variables are left verbatim.
    """
    def _lookup(match: re.Match[str]) -> str:
        var_name = match.group(1)
        env_value = os.environ.get(var_name)
        if env_value:
            return env_value
        # Fallback: ~/.limen/keys.json — derive provider from env var name
        # e.g. OPENROUTER_API_KEY → openrouter
        provider = var_name.lower().replace("_nim", "").replace("_api_key", "")
        try:
            raw = json.loads(Path("~/.limen/keys.json").expanduser().read_text())
            store: dict[str, str] = raw if isinstance(raw, dict) else {}
            return store.get(provider, match.group(0))
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return match.group(0)
    return _ENV_VAR_PATTERN.sub(_lookup, value)


class ConfigError(ValueError):
    """Raised when a LIMEN configuration cannot be loaded safely."""


class ServerConfig(BaseModel):
    """HTTP server settings."""

    model_config = ConfigDict(extra="ignore")

    host: str = "127.0.0.1"
    port: int = Field(default=8000, ge=1, le=65535)
    worker_count: int = Field(
        default=1,
        ge=1,
        le=1,
        description="Phase 0 supports one Uvicorn worker; multi-worker startup is not implemented.",
    )
    log_level: str = "info"
    max_body_size_kb: int = Field(default=256, ge=1, le=10240)

    @field_validator("host")
    @classmethod
    def validate_localhost(cls, value: str) -> str:
        if value != "127.0.0.1":
            raise ValueError("LIMEN accepts only 127.0.0.1; LAN exposure is disabled")
        return value


class DatabaseConfig(BaseModel):
    """SQLite persistence settings."""

    model_config = ConfigDict(extra="ignore")

    path: Path = Path("~/.limen/state.db").expanduser()
    wal_mode: bool = True
    busy_timeout_ms: int = Field(default=30_000, ge=100, le=120_000)
    sync_mode: str = Field(default="normal", pattern="^(normal|full|off)$")

    @field_validator("path", mode="before")
    @classmethod
    def expand_path(cls, value: str | PathLike[str]) -> Path:
        return Path(value).expanduser()


class SecurityConfig(BaseModel):
    """Filesystem and redaction policy."""

    model_config = ConfigDict(extra="ignore")

    reject_non_localhost: bool = True
    config_mode: str = Field(default="owner-only", pattern="^owner-only$")
    database_mode: str = Field(default="owner-only", pattern="^owner-only$")
    redact_provider_bodies: bool = True
    redact_authorization_headers: bool = True


class AuditConfig(BaseModel):
    """Audit authentication and event policy."""

    model_config = ConfigDict(extra="ignore")

    audit_token_secret: str = Field(
        default="",
        description="Bearer token for /v1/_internal endpoints; load from env or TOML",
    )


class ModelConfig(BaseModel):
    """One independently configured model exposed by a provider."""

    model_config = ConfigDict(extra="ignore")

    provider: str = Field(min_length=1)
    model_id: str = Field(min_length=1)

    @field_validator("provider", "model_id")
    @classmethod
    def validate_names(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("model provider and model_id must not be empty")
        return cleaned
    enabled: bool = True
    free: bool = False
    priority: int | None = Field(default=None, ge=0)
    max_context_tokens: int = Field(default=128_000, ge=1)
    capabilities: list[str] = Field(default_factory=list)
    escalation_group: str = "default"
    source_url: str = ""
    verified_at: str = ""


class ProviderConfig(BaseModel):
    """Minimal declarative provider entry retained for later phases."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = False
    base_url: str = ""
    priority: int = Field(default=100, ge=0)
    limit_scope: str = Field(default="unknown", pattern="^(key|account|provider|model|unknown)$")
    account_id: str = ""
    keys: list[str] = Field(default_factory=list)
    models: list[str] = Field(default_factory=list)

    @field_validator("models")
    @classmethod
    def validate_models(cls, values: list[str]) -> list[str]:
        cleaned = [value.strip() for value in values]
        if any(not value for value in cleaned):
            raise ValueError("provider models must not contain empty names")
        return cleaned
    capabilities: list[str] = Field(default_factory=list)
    soft_rpm: int | None = Field(default=None, ge=0)
    soft_itpm: int | None = Field(default=None, ge=0)
    soft_otpm: int | None = Field(default=None, ge=0)


class QueueConfig(BaseModel):
    """Admission control settings for the durable queue."""

    model_config = ConfigDict(extra="ignore")

    max_pending: int = Field(default=500, ge=1, le=100_000)
    max_wait_seconds: float = Field(default=30, ge=0.5, le=3600)
    lease_seconds: int = Field(default=60, ge=10, le=600)


class LimenConfig(BaseModel):
    """Validated application configuration used by CLI and API."""

    model_config = ConfigDict(extra="ignore")

    server: ServerConfig = Field(default_factory=ServerConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    audit: AuditConfig = Field(default_factory=AuditConfig)
    queue: QueueConfig = Field(default_factory=QueueConfig)
    anthropic: dict[str, str] = Field(default_factory=dict)
    providers: dict[str, ProviderConfig] = Field(default_factory=dict)
    models: dict[str, ModelConfig] = Field(default_factory=dict)
    raw: dict[str, Any] = Field(default_factory=dict, exclude=True)

    @property
    def enabled_models(self) -> list[str]:
        """Return unique enabled model IDs in stable priority order."""
        models: list[str] = []
        configured = sorted(
            (
                (name, model)
                for name, model in self.models.items()
                if model.enabled
                and model.provider in self.providers
                and self.providers[model.provider].enabled
            ),
            key=lambda item: (
                item[1].priority
                if item[1].priority is not None
                else self.providers[item[1].provider].priority,
                item[0],
            ),
        )
        for _, model_config in configured:
            if model_config.model_id not in models:
                models.append(model_config.model_id)
        for provider in sorted(self.providers.values(), key=lambda item: item.priority):
            if provider.enabled:
                for provider_model in provider.models:
                    if provider_model not in models:
                        models.append(provider_model)
        return models


def _validate_owner_only(path: Path, *, label: str) -> None:
    """Reject group/world-readable existing secret-bearing configuration files."""
    if not path.exists():
        return
    mode = stat.S_IMODE(path.stat().st_mode)
    other_permissions = stat.S_IRGRP | stat.S_IWGRP | stat.S_IXGRP
    other_permissions |= stat.S_IROTH | stat.S_IWOTH | stat.S_IXOTH
    if mode & other_permissions:
        raise ConfigError(f"{label} must be owner-only (mode 600 or stricter): {path}")


def _read_toml(path: Path) -> dict[str, Any]:
    try:
        with path.open("rb") as config_file:
            return tomllib.load(config_file)
    except FileNotFoundError as exc:
        raise ConfigError(f"Configuration file not found: {path}") from exc
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"Invalid TOML in {path}: {exc}") from exc
    except OSError as exc:
        raise ConfigError(f"Cannot read configuration {path}: {exc}") from exc


def load_config(path: Path | str, *, validate_permissions: bool = True) -> LimenConfig:
    """Load and validate one TOML configuration file."""
    config_path = Path(path).expanduser()
    if validate_permissions:
        _validate_owner_only(config_path, label="Configuration")

    raw = _read_toml(config_path)
    provider_values = raw.get("providers", {})
    if not isinstance(provider_values, dict):
        raise ConfigError("[providers] must be a TOML table")

    # Resolve ${ENV_VAR} placeholders in provider keys.
    resolved_providers: dict[str, Any] = {}
    for name, entry in provider_values.items():
        if isinstance(entry, dict):
            resolved = dict(entry)
            if "keys" in resolved and isinstance(resolved["keys"], list):
                resolved["keys"] = [_resolve_env_vars(k) for k in resolved["keys"]]
            resolved_providers[name] = resolved
        else:
            resolved_providers[name] = entry

    try:
        config = LimenConfig(
            server=raw.get("server", {}),
            database=raw.get("database", {}),
            security=raw.get("security", {}),
            audit=raw.get("audit", {}),
            queue=raw.get("queue", {}),
            anthropic=raw.get("anthropic", {}),
            providers=resolved_providers,
            models=raw.get("models", {}),
            raw=raw,
        )
    except ValidationError as exc:
        raise ConfigError(f"Invalid LIMEN configuration in {config_path}: {exc}") from exc

    for model_name, model_config in config.models.items():
        if model_config.provider not in config.providers:
            raise ConfigError(
                f"Model {model_name!r} references unknown provider "
                f"{model_config.provider!r}"
            )

    if config.security.reject_non_localhost and config.server.host != "127.0.0.1":
        raise ConfigError("LIMEN accepts only 127.0.0.1; LAN exposure is disabled")
    return config
