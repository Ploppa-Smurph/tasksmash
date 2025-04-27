import os
from app import app, db
from app.models import Achievement
from flask_migrate import upgrade

if __name__ == '__main__':
    with app.app_context():
        # Run migrations to update the database schema to the latest revision.
        upgrade()
        
        # Seed achievements if they do not already exist.
        achievements = [
            Achievement(name='Task Initiator', description='Created 10 tasks'),
            Achievement(name='Goal Crusher', description='Completed 5 tasks'),
            Achievement(name='Comment Commander', description='Posted your first comment'),
            Achievement(name='Task Master', description='Created 50 tasks'),
            Achievement(name='Finisher', description='Completed 25 tasks'),
            Achievement(name='Perfectionist', description='Completed all your tasks'),
            Achievement(name='Chatterbox', description='Left 10 comments'),
            Achievement(name='Reply Ruler', description='Left 5 replies'),
            Achievement(name='Friendly Follower', description='Followed 1 user'),
            Achievement(name='Social Butterfly', description='Followed 5 users'),
            Achievement(name='Popular Pick', description='A task of yours got 5 comments'),
            Achievement(name='Empty Inbox', description='You have no incomplete tasks'),
            Achievement(name='Procrastinator', description='You edited the same task 3 times')
        ]
        for achievement in achievements:
            if not Achievement.query.filter_by(name=achievement.name).first():
                db.session.add(achievement)
        db.session.commit()
        print("Achievements seeded!")

    # Use Railway's environment variable for the port (Railway sets PORT automatically).
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)