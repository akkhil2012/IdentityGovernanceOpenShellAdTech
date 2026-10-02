from pydantic_settings import BaseSettings, SettingsConfigDict


AGENTS = ("intent", "profile", "propensity", "audience", "consent", "activation")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    run_mode: str = "simulation"
    database_url: str = "sqlite:///./governed_audience.db"
    governance_signing_key: str = "development-only-change-me"
    broker_shared_secret: str = ""
    policy_version: str = "2026-01"
    intent_worker_url: str = ""
    intent_sandbox_id: str = "sim-intent"
    profile_worker_url: str = ""
    profile_sandbox_id: str = "sim-profile"
    propensity_worker_url: str = ""
    propensity_sandbox_id: str = "sim-propensity"
    audience_worker_url: str = ""
    audience_sandbox_id: str = "sim-audience"
    consent_worker_url: str = ""
    consent_sandbox_id: str = "sim-consent"
    activation_worker_url: str = ""
    activation_sandbox_id: str = "sim-activation"

    def validate_runtime(self) -> None:
        if self.run_mode not in {"simulation", "openshell"}:
            raise RuntimeError("RUN_MODE must be simulation or openshell")
        if self.run_mode == "openshell":
            missing = ["BROKER_SHARED_SECRET"] if not self.broker_shared_secret else []
            for agent in AGENTS:
                if not getattr(self, f"{agent}_worker_url"):
                    missing.append(f"{agent.upper()}_WORKER_URL")
                sandbox = getattr(self, f"{agent}_sandbox_id")
                if not sandbox or sandbox.startswith("sim-"):
                    missing.append(f"{agent.upper()}_SANDBOX_ID")
            if missing:
                raise RuntimeError("OpenShell mode unavailable; missing: " + ", ".join(missing))
