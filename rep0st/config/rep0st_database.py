from absl import flags
from injector import Module
from sqlalchemy.engine.url import make_url

from rep0st.db import Base
from rep0st.framework.data.database import DatabaseModule

FLAGS = flags.FLAGS
flags.DEFINE_string('rep0st_database_uri', '',
                    'Database URI used by rep0st to store data.')
flags.DEFINE_string(
    'rep0st_database_password_file', '',
    'Path to the file containing the password for the database. The password will replace the password in '
    'the rep0st_database_uri flag.')


class Rep0stDatabaseModule(Module):

  def configure(self, binder):
    url = make_url(FLAGS.rep0st_database_uri)
    if FLAGS.rep0st_database_password_file:
      with open(FLAGS.rep0st_database_password_file) as f:
        url = url.set(password=f.read().strip())
    binder.install(DatabaseModule(url, Base))
