"""Generate current HTTP contract and web types from actual API Pydantic models."""

import json

from generate_schemas import ROOT, write_types
from originproof_api.accounts import AccountView, LoginInput, LogoutView
from originproof_api.applications import ApplicationInput, ApplicationView, DecisionInput
from originproof_api.chain_management import IssuerView, KeyInput, KeyView, MutationInput
from originproof_api.finals_proofs import (
    ComparisonInput,
    DocumentIssue,
    IssueInput,
    PaymentIssue,
    ProofContent,
    ProofView,
    RecipientView,
    VerifyInput,
)
from originproof_api.main import create_app
from originproof_api.operations import AuditView, OperationView

OUTPUT = ROOT / "packages/schemas/generated"


def main():
    (OUTPUT / "openapi.json").write_text(
        json.dumps(create_app().openapi(), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    schemas = {
        model.__name__: model.model_json_schema()
        for model in (
            AccountView,
            LoginInput,
            LogoutView,
            ApplicationInput,
            ApplicationView,
            DecisionInput,
            MutationInput,
            KeyInput,
            KeyView,
            IssuerView,
            OperationView,
            AuditView,
            PaymentIssue,
            DocumentIssue,
            IssueInput,
            ProofView,
            ProofContent,
            RecipientView,
            ComparisonInput,
            VerifyInput,
        )
    }
    write_types(schemas, OUTPUT / "types/api.ts")


if __name__ == "__main__":
    main()
