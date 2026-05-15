from sqlalchemy.orm import declarative_base


Base = declarative_base()


from app.models import auth, generation, progress, story, vocabulary  # noqa: E402,F401
