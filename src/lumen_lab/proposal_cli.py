from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .mission_radar import load_missions
from .profile import load_profile
from .proposal import (
    OpenAICompatibleProposalGenerator,
    accept_proposal,
    evidence_index,
    generate_proposals,
    load_proposal_batch,
    validate_evidence,
)
from .store import LabStore

DEFAULT_REVIEW_PATH = Path(".lumen/proposals.json")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lumen-propose",
        description="Generate reviewable experiment proposals without executing them.",
    )
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--profile", type=Path)
    parser.add_argument("--missions", type=Path)
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--write-review",
        type=Path,
        help="Explicitly write the current proposal batch to a review snapshot.",
    )
    parser.add_argument("--endpoint", help="Optional OpenAI-compatible chat completions endpoint.")
    parser.add_argument("--model", help="Model name for optional LLM proposal enrichment.")
    parser.add_argument(
        "--token-env",
        default="LUMEN_LLM_TOKEN",
        help="Environment variable containing an optional bearer token.",
    )
    parser.add_argument("--accept-file", type=Path, help="Reviewed proposal snapshot to accept from.")
    parser.add_argument("--accept", help="Proposal ID to accept from --accept-file.")
    parser.add_argument("--experiment-id", help="New normal backlog experiment ID for acceptance.")
    return parser


def _paths(args: argparse.Namespace) -> tuple[Path, Path]:
    state = args.root / "state"
    profile = args.profile or state / "profile.json"
    missions = args.missions or state / "missions.json"
    return profile, missions


def _adapter(args: argparse.Namespace, profile) -> OpenAICompatibleProposalGenerator | None:
    policy = profile.candidate_generation_policy
    if policy.mode != "optional-llm" or not policy.allow_llm:
        return None
    if bool(args.endpoint) != bool(args.model):
        raise ValueError("--endpoint and --model must be supplied together")
    if not args.endpoint:
        return None
    return OpenAICompatibleProposalGenerator(
        endpoint=args.endpoint,
        model=args.model,
        token=os.environ.get(args.token_env, ""),
    )


def _accept(args: argparse.Namespace, profile, missions, store: LabStore) -> int:
    if not args.accept_file or not args.accept or not args.experiment_id:
        raise ValueError("acceptance requires --accept-file, --accept, and --experiment-id")
    batch = load_proposal_batch(args.accept_file.read_text(encoding="utf-8"))
    proposal = next((item for item in batch.proposals if item.id == args.accept), None)
    if proposal is None:
        raise ValueError(f"proposal not found in review snapshot: {args.accept}")
    experiments = store.load()
    validate_evidence(proposal, evidence_index(profile, missions, experiments))
    experiment = accept_proposal(
        proposal,
        args.experiment_id,
        profile,
        missions,
        experiments,
    )
    store.save(experiments + [experiment])
    print(f"Accepted {proposal.id} as backlog experiment {experiment.id}.")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        profile_path, missions_path = _paths(args)
        profile = load_profile(profile_path)
        missions = load_missions(missions_path)
        store = LabStore(args.root)

        accepting = any((args.accept_file, args.accept, args.experiment_id))
        if accepting:
            if args.write_review or args.endpoint or args.model:
                raise ValueError("acceptance cannot be combined with generation options")
            return _accept(args, profile, missions, store)

        experiments = store.load()
        batch = generate_proposals(
            profile,
            missions,
            experiments,
            adapter=_adapter(args, profile),
        )
        if args.write_review:
            args.write_review.parent.mkdir(parents=True, exist_ok=True)
            args.write_review.write_text(
                json.dumps(batch.to_dict(), indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )

        if args.json:
            print(json.dumps(batch.to_dict(), indent=2, ensure_ascii=False))
            return 0

        if not batch.proposals:
            print("No proposals produced by the current profile policy and evidence.")
        for index, proposal in enumerate(batch.proposals, start=1):
            print(f"{index}. {proposal.title} [{proposal.id}] ({proposal.source})")
            print(
                f"   score inputs: impact={proposal.impact} learning={proposal.learning} "
                f"feasibility={proposal.feasibility} novelty={proposal.novelty} risk={proposal.risk}"
            )
            print(f"   rationale: {proposal.rationale}")
            print(f"   evidence: {', '.join(proposal.evidence)}")
        for warning in batch.warnings:
            print(f"Warning: {warning}")
        if args.write_review:
            print(f"Review snapshot written to {args.write_review}")
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"proposal error: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
