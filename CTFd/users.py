from flask import Blueprint, render_template, request, url_for

from CTFd.models import Users
from CTFd.models.user_fields import UserFields
from CTFd.utils import config
from CTFd.utils.decorators import authed_only
from CTFd.utils.decorators.visibility import (
    check_account_visibility,
    check_score_visibility,
)
from CTFd.utils.helpers import get_errors, get_infos
from CTFd.utils.user import get_current_user

users = Blueprint("users", __name__)


@users.route("/users")
@check_account_visibility
def listing():
    q = request.args.get("q")
    field = request.args.get("field", "name")
    if field not in ("name", "affiliation", "website"):
        field = "name"

    filters = []
    if q:
        filters.append(getattr(Users, field).like(f"%{q}%"))

    users_pagination = (
        Users.query
        .filter_by(banned=False, hidden=False)
        .filter(*filters)
        .order_by(Users.id.asc())
        .paginate(per_page=50, error_out=False)
    )

    # 🔹 Load Branch custom field safely
    user_ids = [u.id for u in users_pagination.items]

    branches = {
        uf.user_id: uf.value
        for uf in UserFields.query
        .filter(
            UserFields.name == "Branch",
            UserFields.user_id.in_(user_ids),
        )
        .all()
    }

    for user in users_pagination.items:
        user.branch = branches.get(user.id, "-")

    args = dict(request.args)
    args.pop("page", 1)

    return render_template(
        "users/users.html",
        users=users_pagination,
        prev_page=url_for(request.endpoint, page=users_pagination.prev_num, **args),
        next_page=url_for(request.endpoint, page=users_pagination.next_num, **args),
        q=q,
        field=field,
    )


@users.route("/profile")
@users.route("/user")
@authed_only
def private():
    infos = get_infos()
    errors = get_errors()

    user = get_current_user()

    if config.is_scoreboard_frozen():
        infos.append("Scoreboard has been frozen")

    return render_template(
        "users/private.html",
        user=user,
        account=user.account,
        infos=infos,
        errors=errors,
    )


@users.route("/users/<int:user_id>")
@check_account_visibility
@check_score_visibility
def public(user_id):
    infos = get_infos()
    errors = get_errors()

    user = Users.query.filter_by(
        id=user_id,
        banned=False,
        hidden=False,
    ).first_or_404()

    branch = (
        UserFields.query
        .filter_by(user_id=user.id, name="Branch")
        .first()
    )
    user.branch = branch.value if branch else "-"

    if config.is_scoreboard_frozen():
        infos.append("Scoreboard has been frozen")

    return render_template(
        "users/public.html",
        user=user,
        account=user.account,
        infos=infos,
        errors=errors,
    )
