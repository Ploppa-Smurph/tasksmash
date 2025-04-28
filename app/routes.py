from flask import abort, render_template, request, redirect, url_for, flash, session, current_app
from app import app, db
from app.models import User, Todo, Comment, Follow, Achievement, UserAchievement
from app.mail import send_mailgun_email
from flask_login import login_user, login_required, current_user, logout_user
import jwt
from datetime import datetime, timedelta
from app.forms import LoginForm, RegisterForm, EditTaskForm
from sqlalchemy import func

# -----------------------------
# Password Reset Routes
# -----------------------------
@app.route("/reset_request", methods=["GET", "POST"])
def reset_request():
    if request.method == "POST":
        email = request.form.get("email")
        user = User.query.filter_by(email=email).first()
        if user:
            token = jwt.encode(
                {"user_id": user.id, "exp": datetime.utcnow() + timedelta(hours=1)},
                current_app.config["SECRET_KEY"],
                algorithm="HS256"
            )
            reset_url = url_for("reset_password", token=token, _external=True)
            send_mailgun_email(
                recipient=email,
                subject="Password Reset Request",
                body=f"Click the link to reset your password: {reset_url}"
            )
            flash("Password reset link sent!", "success")
        else:
            flash("No user found with that email address.", "error")
    return render_template("resetRequest.html")

@app.route("/reset_password/<token>", methods=["GET", "POST"])
def reset_password(token):
    try:
        payload = jwt.decode(token, current_app.config["SECRET_KEY"], algorithms=["HS256"])
        user_id = payload.get("user_id")
    except jwt.ExpiredSignatureError:
        flash("The reset link has expired.")
        return redirect(url_for("reset_request"))
    except jwt.InvalidTokenError:
        flash("Invalid reset link.")
        return redirect(url_for("reset_request"))

    user = User.query.get_or_404(user_id)
    if request.method == "POST":
        new_password = request.form.get("password")
        user.set_password(new_password)
        db.session.commit()
        flash("Your password has been reset successfully!")
        return redirect(url_for("landing_page"))
    return render_template("resetPassword.html", token=token)

# -----------------------------
# To-Do Routes
# -----------------------------
@app.route("/add", methods=["POST"])
@login_required
def add_todo():
    content = request.form.get("content")
    new_todo = Todo(content=content, user_id=current_user.id)
    db.session.add(new_todo)
    db.session.commit()
    evaluate_achievements(current_user)
    return redirect(url_for("dashboard"))


@app.route("/edit/<int:id>", methods=["GET", "POST"])
@login_required
def edit_todo(id):
    task = Todo.query.get_or_404(id)
    if task.user_id != current_user.id:
        flash("You do not have permission to edit this to-do.", "error")
        return redirect(url_for("dashboard"))
    form = EditTaskForm(obj=task)
    if form.validate_on_submit():
        task.content = form.content.data
        task.edit_count += 1
        db.session.commit()
        if task.edit_count >= 3:
            award_achievement(current_user, 'Procrastinator')
        return redirect(url_for("dashboard"))
    return render_template("edit.html", task=task, form=form)


@app.route("/delete/<int:id>", methods=["POST"])
@login_required
def delete_todo(id):
    todo = Todo.query.get_or_404(id)
    if todo.user_id != current_user.id:
        flash("You do not have permission to delete this to-do.", "error")
        return redirect(url_for("dashboard"))
    db.session.delete(todo)
    db.session.commit()
    return redirect(url_for("dashboard"))


@app.route('/complete_task/<int:task_id>', methods=['POST'])
@login_required
def complete_task(task_id):
    task = Todo.query.get_or_404(task_id)
    if task.user_id != current_user.id:
        abort(403)
    task.completed = True
    db.session.commit()
    evaluate_achievements(current_user)
    return redirect(url_for('dashboard'))

# -----------------------------
# Comment Routes
# -----------------------------
@app.route("/comment/<int:task_id>", methods=["POST"])
@login_required
def add_comment(task_id):
    content = request.form.get("comment")
    new_comment = Comment(content=content, task_id=task_id, user_id=current_user.id)
    db.session.add(new_comment)
    db.session.commit()
    evaluate_achievements(current_user)
    return redirect(url_for("dashboard"))


@app.route("/task/<int:task_id>")
@login_required
def view_task(task_id):
    task = Todo.query.get_or_404(task_id)
    comments = Comment.query.filter_by(task_id=task_id).all()
    return render_template("task.html", task=task, comments=comments)

# -----------------------------
# Home, Login & Register Routes
# -----------------------------
@app.route("/")
def landing_page():
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    login_form = LoginForm()
    register_form = RegisterForm()

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            flash("You have been logged in successfully!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid username or password.", "error")
            return render_template("login.html", login_form=login_form, register_form=register_form, show_create_account=True)

    return render_template("login.html", login_form=login_form, register_form=register_form, show_create_account=False)


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        logout_user()
        session.pop("username", None)
        session.pop("user_id", None)

    if request.method == "GET" and "keep_flash" not in request.args:
        session.pop('_flashes', None)

    form = RegisterForm()

    if form.validate_on_submit():
        username = form.username.data
        email = form.email.data
        password = form.password.data

        existing_user_by_username = User.query.filter_by(username=username).first()
        existing_user_by_email = User.query.filter_by(email=email).first()

        if existing_user_by_username or existing_user_by_email:
            flash("Username or email already exists.", "error")
            return redirect(url_for("register", keep_flash=1))
        else:
            new_user = User(username=username, email=email)
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()

            flash("Account created successfully!", "success")
            return redirect(url_for("login"))

    return render_template("register.html", form=form)

# -----------------------------
# Miscellaneous Routes
# -----------------------------
@app.after_request
def add_header(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@app.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return redirect(url_for("landing_page"))

@app.route("/add_comment_reply/<int:comment_id>", methods=["POST"])
@login_required
def add_comment_reply(comment_id):
    parent_comment = Comment.query.get_or_404(comment_id)
    reply_content = request.form.get("reply")
    if not reply_content:
        flash("Reply cannot be empty.", "error")
        return redirect(url_for("dashboard"))
    reply = Comment(
        content=reply_content,
        user_id=current_user.id,
        task_id=parent_comment.task_id,
        parent_id=parent_comment.id
    )
    db.session.add(reply)
    db.session.commit()
    flash("Your reply has been added.", "success")
    evaluate_achievements(current_user)
    return redirect(url_for("dashboard"))

# -----------------------------
# Follow/Unfollow Routes
# -----------------------------
@app.route("/follow/<int:user_id>", methods=["POST"])
@login_required
def follow_user(user_id):
    user_to_follow = User.query.get_or_404(user_id)
    existing_follow = Follow.query.filter_by(follower_id=current_user.id, followee_id=user_id).first()
    if not existing_follow:
        follow = Follow(follower_id=current_user.id, followee_id=user_id)
        db.session.add(follow)
        db.session.commit()
        flash(f"You are now following {user_to_follow.username}!", "success")
    else:
        flash(f"You are already following {user_to_follow.username}.", "info")
    evaluate_achievements(current_user)
    return redirect(url_for("dashboard"))


@app.route("/unfollow/<int:user_id>", methods=["POST"])
@login_required
def unfollow_user(user_id):
    follow = Follow.query.filter_by(follower_id=current_user.id, followee_id=user_id).first()
    if follow:
        db.session.delete(follow)
        db.session.commit()
        flash("You have unfollowed the user.", "success")
    else:
        flash("You were not following this user.", "info")
    return redirect(url_for("dashboard"))

# -----------------------------
# Dashboard Route
# -----------------------------
@app.route('/dashboard')
@login_required
def dashboard():
    # User's own tasks
    tasks = Todo.query.filter_by(user_id=current_user.id).order_by(Todo.created_at.desc()).all()

    # Tasks from followed users
    followed_ids = [follow.followee_id for follow in current_user.followed_users]
    followed_users_tasks = []
    if followed_ids:
        followed_users_tasks = Todo.query.filter(Todo.user_id.in_(followed_ids)).order_by(Todo.created_at.desc()).all()

    # Recently posted tasks, excluding those by the current user
    recent_tasks = Todo.query.filter(Todo.user_id != current_user.id).order_by(Todo.created_at.desc()).limit(10).all()

    # Popular tasks: tasks sorted by the number of comments
    popular_tasks = db.session.query(
        Todo, func.count(Comment.id).label('comments_count')
    ).join(Comment, Todo.id == Comment.task_id)\
     .group_by(Todo.id).order_by(func.count(Comment.id).desc()).limit(10).all()

    # User achievements
    achievements = UserAchievement.query.filter_by(user_id=current_user.id).all()

    return render_template(
        "dashboard.html",
        tasks=tasks,
        followed_users_tasks=followed_users_tasks,
        recent_tasks=recent_tasks,
        popular_tasks=popular_tasks,
        achievements=achievements
    )
# -----------------------------
# Achievement Helpers
# -----------------------------
def award_achievement(user, name):
    achievement = Achievement.query.filter_by(name=name).first()
    if achievement and not user.has_achievement(name):
        new_award = UserAchievement(user_id=user.id, achievement_id=achievement.id)
        db.session.add(new_award)
        db.session.commit()

        flash(f'Achievement Unlocked: {achievement.name} — {achievement.description}', 'achievement')


def evaluate_achievements(user):
    task_count = Todo.query.filter_by(user_id=user.id).count()
    completed_count = Todo.query.filter_by(user_id=user.id, completed=True).count()
    incomplete_count = Todo.query.filter_by(user_id=user.id, completed=False).count()
    comment_count = Comment.query.filter_by(user_id=user.id).count()
    reply_count = Comment.query.filter_by(user_id=user.id).filter(Comment.parent_id.isnot(None)).count()
    followers_count = Follow.query.filter_by(follower_id=user.id).count()

    if task_count >= 10:
        award_achievement(user, 'Task Initiator')
    if task_count >= 50:
        award_achievement(user, 'Task Master')
    if completed_count >= 5:
        award_achievement(user, 'Goal Crusher')
    if completed_count >= 25:
        award_achievement(user, 'Finisher')
    if task_count > 0 and completed_count == task_count:
        award_achievement(user, 'Perfectionist')
    if incomplete_count == 0 and task_count > 0:
        award_achievement(user, 'Empty Inbox')

    if comment_count >= 1:
        award_achievement(user, 'Comment Commander')
    if comment_count >= 10:
        award_achievement(user, 'Chatterbox')
    if reply_count >= 5:
        award_achievement(user, 'Reply Ruler')

    if followers_count >= 1:
        award_achievement(user, 'Friendly Follower')
    if followers_count >= 5:
        award_achievement(user, 'Social Butterfly')

    user_tasks = Todo.query.filter_by(user_id=user.id).all()
    for task in user_tasks:
        if len(task.comments) >= 5:
            award_achievement(user, 'Popular Pick')
            break

@app.route("/about")
def about():
    return render_template("about.html")
