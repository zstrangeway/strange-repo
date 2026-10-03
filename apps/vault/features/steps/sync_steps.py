import contextlib
import io
import stat
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from behave import given, then, when
from support_repos import git, laptop_push, show

from vault_sync.sync import run


def write(repo, name, text):
    path = repo / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


@given("a vault repository shared with Zac's devices")
def step_vault(context):
    assert (context.laptop / "README.md").exists()


@given("a working copy of it beside the MCP server")
def step_worker(context):
    assert (context.worker / "README.md").exists()


@given('an agent has written "{name}"')
def step_agent_wrote(context, name):
    text = f"agent memory for {name}\n"
    write(context.worker, name, text)
    context.written[name] = text


@given("no file has changed since the last sync")
def step_nothing(context):
    assert git(context.worker, "status", "--porcelain") == ""


@given('Zac has pushed a change to "{name}" from his laptop')
def step_zac_pushed(context, name):
    text = f"Zac's note in {name}\n"
    laptop_push(context.laptop, name, text)
    context.written[name] = text


@given('"{name}" has been changed in the working copy')
def step_stray(context, name):
    write(context.worker, name, "a change that isn't an agent's\n")


@given('Zac pushes a change to "{name}" just before the sync pushes')
def step_race(context, name):
    # A pre-push hook in the server's copy: Zac's push lands first, so the
    # sync's push is rejected for real. It removes itself after one go.
    # No apostrophes: this text goes through a shell.
    text = f"Zac racing note in {name}\n"
    hook = context.worker / ".git" / "hooks" / "pre-push"
    hook.write_text(
        "#!/bin/sh\n"
        # Git sets GIT_DIR and friends for hooks; without clearing them, the
        # "laptop" commands below would act on the server's copy instead.
        "unset $(git rev-parse --local-env-vars)\n"
        f"cd '{context.laptop}' && mkdir -p \"$(dirname '{name}')\" && printf '%s' '{text}' > '{name}' "
        f"&& git add --all && git commit --quiet -m race && git push --quiet origin main\n"
        # By absolute path: the hook has cd'd into the laptop's copy by now.
        f"rm -- '{hook}'\n"
    )
    hook.chmod(hook.stat().st_mode | stat.S_IEXEC)
    context.written[name] = text


@given('Zac and an agent have both changed "{name}" in different ways')
def step_conflict(context, name):
    context.zac_text, context.agent_text = "Zac's version\n", "the agent's version\n"
    laptop_push(context.laptop, name, context.zac_text)
    write(context.worker, name, context.agent_text)
    context.conflict_name = name


@when("the sync runs")
def step_sync(context):
    context.origin_before = git(context.origin, "rev-parse", "HEAD").strip()
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        context.exit_code = run(context.worker, interval=0, once=True)
    context.output = out.getvalue() + err.getvalue()


@then('the repository has a commit adding "{name}"')
def step_has_commit(context, name):
    assert show(context.origin, name) == context.written[name], context.output
    assert name in git(context.origin, "show", "--name-only", "--format=", "HEAD")


@then('the commit is authored by "{author}"')
def step_author(context, author):
    assert git(context.origin, "log", "-1", "--format=%an").strip() == author


@then("the commit message names the files it changed")
def step_message(context):
    message = git(context.origin, "log", "-1", "--format=%B")
    for name in context.written:
        assert name in message, message


@then("no commit is made")
def step_no_commit(context):
    assert git(context.origin, "rev-parse", "HEAD").strip() == context.origin_before


@then("the sync reports that there was nothing to commit")
def step_reports_nothing(context):
    assert "nothing to commit" in context.output, context.output


@then('the working copy has Zac\'s change to "{name}"')
def step_worker_has(context, name):
    assert (context.worker / name).read_text() == context.written[name]


@then("the repository has both changes")
def step_both(context):
    for name, text in context.written.items():
        assert show(context.origin, name) == text, name


@then('the commit contains only "{name}"')
def step_only(context, name):
    files = git(context.origin, "show", "--name-only", "--format=", "HEAD").split()
    assert files == [name], files


@then('the sync reports that it left "{name}" uncommitted')
def step_reports_left(context, name):
    assert "left uncommitted" in context.output and name in context.output, context.output


@then("the agent's change reaches the repository")
def step_agent_reached(context):
    for name, text in context.written.items():
        if name.startswith("Agents/"):
            assert show(context.origin, name) == text, context.output


@then("Zac's change is not lost")
def step_zac_kept(context):
    for name, text in context.written.items():
        if not name.startswith("Agents/"):
            assert show(context.origin, name) == text, context.output


@then("nothing is pushed")
def step_nothing_pushed(context):
    assert git(context.origin, "log", "-1", "--format=%an").strip() == "Zac"


@then("neither version is overwritten")
def step_both_kept(context):
    assert show(context.origin, context.conflict_name) == context.zac_text
    assert (context.worker / context.conflict_name).read_text() == context.agent_text


@then("the sync reports the conflict and exits with a failure")
def step_conflict_reported(context):
    assert context.exit_code == 1
    assert "conflict in" in context.output and context.conflict_name in context.output, context.output
