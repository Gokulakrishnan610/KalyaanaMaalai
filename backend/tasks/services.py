from datetime import timedelta

from django.db import transaction
from rest_framework.exceptions import NotFound

from tasks.models import Stage, Task
from tasks.template import TEMPLATE, TaskDraft
from weddings.models import TeamMember, Wedding


def _drafts_for(items) -> list[TaskDraft]:
    """`items` may be None (the whole template), template titles, or TaskDrafts."""
    if items is None:
        return list(TEMPLATE)
    by_title = {draft.title.lower(): draft for draft in TEMPLATE}
    drafts = []
    for item in items:
        draft = item if isinstance(item, TaskDraft) else by_title.get(str(item).strip().lower())
        if draft is not None:
            drafts.append(draft)
    return drafts


def _plan_template(wedding: Wedding, items) -> list[dict]:
    """The tasks that are still missing, as dicts ready for Task(...). Writes nothing."""
    taken = {title.lower() for title in Task.objects.filter(wedding=wedding).values_list("title", flat=True)}
    assignees: dict[str, int] = {}
    for member in TeamMember.objects.filter(wedding=wedding).order_by("id"):
        assignees.setdefault(member.role_label, member.user_id)

    plan = []
    for draft in _drafts_for(items):
        if draft.title.lower() in taken:
            continue
        taken.add(draft.title.lower())
        plan.append(dict(
            title=draft.title, description=draft.description, category=draft.category,
            priority=draft.priority, stage=Stage.TO_PLAN,
            due_date=wedding.start_date + timedelta(days=draft.due_offset_days),
            assigned_to_id=assignees.get(draft.default_role),
        ))
    return plan


def preview_tasks_from_template(wedding_id: int, items=None) -> list[dict]:
    """What `create_tasks_from_template` would create right now (dry run)."""
    try:
        wedding = Wedding.objects.get(pk=wedding_id)
    except Wedding.DoesNotExist:
        raise NotFound("Wedding not found.") from None
    return _plan_template(wedding, items)


@transaction.atomic
def create_tasks_from_template(wedding_id: int, items=None) -> list[Task]:
    """Add the template tasks this wedding does not have yet (matched by title, ignoring case).
    Safe to call again: it only creates what is missing. Returns the tasks it created."""
    # locking the wedding makes two simultaneous calls take turns instead of both creating tasks
    try:
        wedding = Wedding.objects.select_for_update().get(pk=wedding_id)
    except Wedding.DoesNotExist:
        raise NotFound("Wedding not found.") from None
    next_position = _next_position(wedding.id, Stage.TO_PLAN)
    created = []
    for offset, fields in enumerate(_plan_template(wedding, items)):
        created.append(Task.objects.create(wedding=wedding, position=next_position + offset, **fields))
    return created


def _next_position(wedding_id: int, stage: str) -> int:
    last = (Task.objects.filter(wedding_id=wedding_id, stage=stage).order_by("-position")
            .values_list("position", flat=True).first())
    return 0 if last is None else last + 1


def next_position(wedding_id: int, stage: str) -> int:
    return _next_position(wedding_id, stage)


def _renumber(tasks: list[Task]) -> None:
    changed = []
    for index, task in enumerate(tasks):
        if task.position != index:
            task.position = index
            changed.append(task)
    if changed:
        Task.objects.bulk_update(changed, ["position", "stage"])


@transaction.atomic
def move_task(task_id: int, stage: str, position: int | None = None) -> Task:
    """Put a task in `stage` at `position` (0 = top; None = bottom) and keep both columns numbered 0..n."""
    task = Task.objects.select_for_update().get(pk=task_id)
    # lock every task in this wedding's affected columns so two drags cannot interleave
    columns = list(
        Task.objects.select_for_update()
        .filter(wedding_id=task.wedding_id, stage__in={task.stage, stage})
        .order_by("position", "id")
    )
    source = [t for t in columns if t.stage == task.stage and t.id != task.id]
    target = source if stage == task.stage else [t for t in columns if t.stage == stage]

    moving = next(t for t in columns if t.id == task.id)
    moving.stage = stage
    index = len(target) if position is None else max(0, min(position, len(target)))
    target.insert(index, moving)

    _renumber(source)
    if target is not source:
        _renumber(target)
    # the moved task is always written, even if its number did not change
    Task.objects.filter(pk=moving.pk).update(stage=stage, position=moving.position)
    moving.refresh_from_db()
    return moving
