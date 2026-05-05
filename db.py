import psycopg2, os

def get_conn():
    return psycopg2.connect(os.environ['DATABASE_URL'])

def init_db():
    with get_conn() as conn:
        conn.cursor().execute('''
            CREATE TABLE IF NOT EXISTS todos (
                id SERIAL PRIMARY KEY,
                text TEXT NOT NULL,
                done BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT NOW()
            )
        ''')
        conn.commit()

def add_todo(text):
    with get_conn() as conn:
        conn.cursor().execute('INSERT INTO todos (text) VALUES (%s)', (text,))
        conn.commit()

def get_todos():
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute('SELECT text FROM todos WHERE done=FALSE ORDER BY created_at')
        return [row[0] for row in cur.fetchall()]

def mark_done(text):
    with get_conn() as conn:
        conn.cursor().execute(
            'UPDATE todos SET done=TRUE WHERE text=%s AND done=FALSE', (text,))
        conn.commit()
