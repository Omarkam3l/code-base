"""Unit tests for PushController and GitSafetyValidator."""

from codegraph.git.safety import GitSafetyValidator, PushController


def test_push_controller_disabled_by_default() -> None:
    controller = PushController(push_authorized=False)
    assert controller.is_authorized() is False

    pushed, err = controller.push("examples/sample_project", "codegraph/fix/test")
    assert pushed is False
    assert "AUTHORIZATION" in err

    # Authorize explicitly
    controller.authorize_push()
    assert controller.is_authorized() is True


def test_git_safety_validator_blocks_destructive_commands() -> None:
    valid, err = GitSafetyValidator.validate_git_command("git reset --hard HEAD")
    assert valid is False
    assert "forbidden" in err.lower()

    valid2, err2 = GitSafetyValidator.validate_git_command("git push --force origin main")
    assert valid2 is False
