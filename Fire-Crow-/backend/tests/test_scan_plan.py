import os
import shutil
import tempfile
import pytest
from app.orchestrator.scan_plan import generate_scan_plan

@pytest.fixture
def temp_repo():
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)

def test_scan_plan_passive_only_missing_attestation(temp_repo):
    # Create a python project structure
    with open(os.path.join(temp_repo, "requirements.txt"), "w") as f:
        f.write("fastapi\n")
    
    # Generate plan with attestation_accepted = False
    plan = generate_scan_plan(
        clone_path=temp_repo,
        attestation_accepted=False,
        authorization_scope="full_active",
        docker_available=True
    )
    
    assert "python" in plan.tech_stack
    assert not plan.active_testing_allowed
    assert plan.active_testing_skip_reason is not None
    assert "attestation" in plan.active_testing_skip_reason.lower()
    assert plan.execution_depth == "passive-only"
    assert "dependency" in plan.enabled_scanners
    assert "sandbox" not in plan.enabled_scanners

def test_scan_plan_passive_only_restricted_scope(temp_repo):
    with open(os.path.join(temp_repo, "package.json"), "w") as f:
        f.write('{"name": "test"}')
        
    plan = generate_scan_plan(
        clone_path=temp_repo,
        attestation_accepted=True,
        authorization_scope="passive_only",
        docker_available=True
    )
    
    assert "node" in plan.tech_stack
    assert not plan.active_testing_allowed
    assert plan.active_testing_skip_reason is not None
    assert "scope" in plan.active_testing_skip_reason.lower()
    assert plan.execution_depth == "passive-only"

def test_scan_plan_active_testing_allowed(temp_repo):
    with open(os.path.join(temp_repo, "requirements.txt"), "w") as f:
        f.write("fastapi\n")
        
    plan = generate_scan_plan(
        clone_path=temp_repo,
        attestation_accepted=True,
        authorization_scope="full_active",
        docker_available=True
    )
    
    assert "python" in plan.tech_stack
    assert plan.active_testing_allowed
    assert plan.active_testing_skip_reason is None
    assert plan.execution_depth == "deep-active"
    assert "sandbox" in plan.enabled_scanners
    assert "network" in plan.enabled_scanners
    assert "attack" in plan.enabled_scanners
    assert "exploit" in plan.enabled_scanners
