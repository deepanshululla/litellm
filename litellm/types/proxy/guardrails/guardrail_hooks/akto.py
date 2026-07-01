from typing import Literal, Optional

from pydantic import Field

from .base import GuardrailConfigModel


class AktoConfigModel(GuardrailConfigModel):
    """
    Config for the Akto guardrail.

    Use two separate config entries to control behaviour:
      akto-validate (mode: pre_call)  -> check guardrails, block if flagged
      akto-ingest   (mode: post_call) -> ingest request+response data
    """

    akto_base_url: Optional[str] = Field(
        default=None,
        description="Akto Guardrail API Base URL. Env: AKTO_GUARDRAIL_API_BASE.",
        json_schema_extra={
            "examples": [
                "http://localhost:9090",
                "https://akto-ingestion.example.com",
            ]
        },
    )

    akto_api_key: Optional[str] = Field(
        default=None,
        description="API key for Akto. Env: AKTO_API_KEY.",
    )

    akto_account_id: Optional[str] = Field(
        default=None,
        description="Akto account ID for multi-tenant deployments. Env: AKTO_ACCOUNT_ID. Default: '1000000'.",
    )

    akto_vxlan_id: Optional[str] = Field(
        default=None,
        description="Akto VXLAN ID. Env: AKTO_VXLAN_ID. Default: '0'.",
    )

    unreachable_fallback: Literal["fail_closed", "fail_open"] = Field(
        default="fail_closed",
        description="What to do when Akto is unreachable. 'fail_open' = allow, 'fail_closed' = block.",
    )

    guardrail_timeout: Optional[int] = Field(
        default=None,
        description="HTTP timeout in seconds. Default: 5.",
    )

    streaming_end_of_stream_only: bool = Field(
        default=True,
        description=(
            "When True, the post_call streaming hook calls apply_guardrail once at "
            "end-of-stream rather than on every sampled chunk. Defaults to True because "
            "Akto's ingest endpoint only needs the complete response."
        ),
    )

    apply_guardrail_to_model_groups: Optional[list[str]] = Field(
        default=None,
        description=(
            "If set, run Akto only for requests whose requested model group is in "
            "this list (matched case-insensitively against the request's model / "
            "model_group). Empty/None = all model groups."
        ),
    )

    @staticmethod
    def ui_friendly_name() -> str:
        return "Akto"
