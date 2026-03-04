"""
Web panel for viewing and managing the blacklist.
Run separately: python web_panel.py
"""

from flask import Flask, render_template_string, request, redirect, url_for, session, flash
import sqlite3
from functools import wraps
from config import WEB_HOST, WEB_PORT, WEB_SECRET, DB_PATH if hasattr(__import__('config'), 'DB_PATH') else None

try:
    from config import DB_PATH
except ImportError:
    DB_PATH = "bot_data.db"

app = Flask(__name__)
app.secret_key = WEB_SECRET

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Панель управления каналом</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0f0f1a; color: #e0e0e0; }
        .header { background: linear-gradient(135deg, #1a1a2e, #16213e); padding: 20px 30px; border-bottom: 1px solid #2a2a4a; display: flex; align-items: center; gap: 15px; }
        .header h1 { font-size: 22px; color: #7c6af7; }
        .header .logo { font-size: 28px; }
        .nav { display: flex; gap: 10px; padding: 15px 30px; background: #0f0f1a; border-bottom: 1px solid #1e1e3a; }
        .nav a { color: #aaa; text-decoration: none; padding: 7px 16px; border-radius: 8px; font-size: 14px; transition: all 0.2s; }
        .nav a:hover, .nav a.active { background: #7c6af7; color: white; }
        .container { max-width: 1100px; margin: 30px auto; padding: 0 20px; }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 15px; margin-bottom: 30px; }
        .stat-card { background: #1a1a2e; border: 1px solid #2a2a4a; border-radius: 12px; padding: 20px; text-align: center; }
        .stat-card .num { font-size: 36px; font-weight: bold; color: #7c6af7; }
        .stat-card .label { color: #888; font-size: 13px; margin-top: 5px; }
        .card { background: #1a1a2e; border: 1px solid #2a2a4a; border-radius: 12px; overflow: hidden; }
        .card-header { padding: 16px 20px; border-bottom: 1px solid #2a2a4a; display: flex; justify-content: space-between; align-items: center; }
        .card-header h2 { font-size: 16px; color: #ccc; }
        table { width: 100%; border-collapse: collapse; }
        th { text-align: left; padding: 12px 16px; font-size: 12px; color: #666; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 1px solid #1e1e3a; }
        td { padding: 12px 16px; border-bottom: 1px solid #1a1a2e; font-size: 14px; }
        tr:hover td { background: #1e1e3a; }
        .badge { display: inline-block; padding: 3px 10px; border-radius: 20px; font-size: 12px; font-weight: 500; }
        .badge-banned { background: #3d1515; color: #ff6b6b; }
        .badge-active { background: #0f2d1a; color: #51cf66; }
        .badge-pending { background: #2d2500; color: #ffd43b; }
        .btn { padding: 6px 14px; border-radius: 8px; border: none; cursor: pointer; font-size: 13px; transition: all 0.2s; }
        .btn-unban { background: #1e3a2e; color: #51cf66; }
        .btn-unban:hover { background: #2a5a3e; }
        .btn-ban { background: #3a1e1e; color: #ff6b6b; }
        .btn-ban:hover { background: #5a2a2a; }
        .search-box { padding: 8px 14px; background: #0f0f1a; border: 1px solid #2a2a4a; border-radius: 8px; color: #eee; font-size: 14px; width: 250px; }
        .search-box:focus { outline: none; border-color: #7c6af7; }
        .alert { padding: 12px 16px; border-radius: 8px; margin-bottom: 20px; font-size: 14px; }
        .alert-success { background: #0f2d1a; border: 1px solid #2a5a3a; color: #51cf66; }
        .alert-error { background: #2d0f0f; border: 1px solid #5a2a2a; color: #ff6b6b; }
        .user-id { font-family: monospace; color: #888; font-size: 13px; }
        .empty { text-align: center; padding: 40px; color: #555; }
        .tabs { display: flex; gap: 0; margin-bottom: 0; }
        .tab { padding: 10px 20px; cursor: pointer; font-size: 14px; color: #888; border-bottom: 2px solid transparent; }
        .tab.active { color: #7c6af7; border-bottom-color: #7c6af7; }
        /* Login */
        .login-wrap { display: flex; align-items: center; justify-content: center; min-height: 100vh; }
        .login-box { background: #1a1a2e; border: 1px solid #2a2a4a; border-radius: 16px; padding: 40px; width: 360px; }
        .login-box h2 { color: #7c6af7; margin-bottom: 25px; text-align: center; }
        .form-group { margin-bottom: 16px; }
        .form-group label { display: block; color: #888; font-size: 13px; margin-bottom: 6px; }
        .form-group input { width: 100%; padding: 10px 14px; background: #0f0f1a; border: 1px solid #2a2a4a; border-radius: 8px; color: #eee; font-size: 15px; }
        .form-group input:focus { outline: none; border-color: #7c6af7; }
        .btn-primary { width: 100%; padding: 12px; background: #7c6af7; color: white; border: none; border-radius: 8px; font-size: 15px; cursor: pointer; margin-top: 8px; }
        .btn-primary:hover { background: #6a58e0; }
    </style>
</head>
<body>
{% if not logged_in %}
<div class="login-wrap">
  <div class="login-box">
    <h2>🔐 Вход в панель</h2>
    {% for msg in get_flashed_messages() %}
    <div class="alert alert-error">{{ msg }}</div>
    {% endfor %}
    <form method="POST" action="/login">
      <div class="form-group">
        <label>Пароль</label>
        <input type="password" name="password" placeholder="Введите пароль" autofocus>
      </div>
      <button type="submit" class="btn btn-primary">Войти</button>
    </form>
  </div>
</div>
{% else %}
<div class="header">
  <span class="logo">📡</span>
  <h1>Панель управления каналом</h1>
</div>
<div class="nav">
  <a href="/" class="{{ 'active' if page == 'all' }}">👥 Все пользователи</a>
  <a href="/banned" class="{{ 'active' if page == 'banned' }}">⛔️ Чёрный список</a>
  <a href="/logout" style="margin-left:auto">Выйти</a>
</div>
<div class="container">
  {% for msg in get_flashed_messages() %}
    {% if 'успешно' in msg or 'разбанен' in msg %}
    <div class="alert alert-success">{{ msg }}</div>
    {% else %}
    <div class="alert alert-error">{{ msg }}</div>
    {% endif %}
  {% endfor %}

  {% if page == 'all' %}
  <div class="stats">
    <div class="stat-card">
      <div class="num">{{ total_users }}</div>
      <div class="label">Всего пользователей</div>
    </div>
    <div class="stat-card">
      <div class="num" style="color:#51cf66">{{ active_users }}</div>
      <div class="label">Активных</div>
    </div>
    <div class="stat-card">
      <div class="num" style="color:#ff6b6b">{{ banned_users }}</div>
      <div class="label">В чёрном списке</div>
    </div>
  </div>
  {% endif %}

  <div class="card">
    <div class="card-header">
      <h2>{% if page == 'banned' %}⛔️ Чёрный список{% else %}👥 Все пользователи{% endif %}</h2>
      <input class="search-box" type="text" id="search" placeholder="🔍 Поиск..." oninput="filterTable()">
    </div>
    <table id="userTable">
      <thead>
        <tr>
          <th>Пользователь</th>
          <th>Telegram ID</th>
          <th>Username</th>
          <th>Дата регистрации</th>
          {% if page == 'banned' %}<th>Дата бана</th><th>Причина</th>{% endif %}
          <th>Статус</th>
          <th>Действие</th>
        </tr>
      </thead>
      <tbody>
        {% for user in users %}
        <tr>
          <td>{{ user.full_name or '—' }}</td>
          <td><span class="user-id">{{ user.user_id }}</span></td>
          <td>{% if user.username %}<span style="color:#7c6af7">@{{ user.username }}</span>{% else %}—{% endif %}</td>
          <td style="color:#666;font-size:13px">{{ user.joined_at[:16] if user.joined_at else '—' }}</td>
          {% if page == 'banned' %}
          <td style="color:#666;font-size:13px">{{ user.banned_at[:16] if user.banned_at else '—' }}</td>
          <td style="color:#888;font-size:13px">{{ user.ban_reason or '—' }}</td>
          {% endif %}
          <td>
            {% if user.is_banned %}
              <span class="badge badge-banned">Забанен</span>
            {% elif user.has_joined_channel %}
              <span class="badge badge-active">В канале</span>
            {% else %}
              <span class="badge badge-pending">Не зашёл</span>
            {% endif %}
          </td>
          <td>
            {% if user.is_banned %}
            <form method="POST" action="/unban" style="display:inline">
              <input type="hidden" name="user_id" value="{{ user.user_id }}">
              <button type="submit" class="btn btn-unban">✅ Разбанить</button>
            </form>
            {% else %}
            <form method="POST" action="/ban" style="display:inline">
              <input type="hidden" name="user_id" value="{{ user.user_id }}">
              <button type="submit" class="btn btn-ban">⛔️ Забанить</button>
            </form>
            {% endif %}
          </td>
        </tr>
        {% else %}
        <tr><td colspan="8" class="empty">Список пуст</td></tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
</div>
<script>
function filterTable() {
  const q = document.getElementById('search').value.toLowerCase();
  const rows = document.querySelectorAll('#userTable tbody tr');
  rows.forEach(row => {
    row.style.display = row.textContent.toLowerCase().includes(q) ? '' : 'none';
  });
}
</script>
{% endif %}
</body>
</html>
"""


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@app.route('/login', methods=['GET', 'POST'])
def login_page():
    if request.method == 'POST':
        if request.form.get('password') == WEB_SECRET:
            session['logged_in'] = True
            return redirect('/')
        flash('Неверный пароль')
    return render_template_string(HTML_TEMPLATE, logged_in=False, page='login')


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')


@app.route('/')
@login_required
def index():
    conn = get_db()
    users = conn.execute("SELECT * FROM users ORDER BY joined_at DESC").fetchall()
    users = [dict(u) for u in users]
    total = len(users)
    banned = sum(1 for u in users if u['is_banned'])
    conn.close()
    return render_template_string(HTML_TEMPLATE,
        logged_in=True, page='all', users=users,
        total_users=total, banned_users=banned, active_users=total-banned)


@app.route('/banned')
@login_required
def banned():
    conn = get_db()
    users = conn.execute("SELECT * FROM users WHERE is_banned=1 ORDER BY banned_at DESC").fetchall()
    users = [dict(u) for u in users]
    conn.close()
    return render_template_string(HTML_TEMPLATE,
        logged_in=True, page='banned', users=users,
        total_users=0, banned_users=len(users), active_users=0)


@app.route('/unban', methods=['POST'])
@login_required
def unban():
    user_id = request.form.get('user_id')
    if user_id:
        conn = get_db()
        conn.execute("UPDATE users SET is_banned=0, banned_at=NULL, ban_reason=NULL WHERE user_id=?", (user_id,))
        conn.commit()
        conn.close()
        flash(f'✅ Пользователь {user_id} успешно разбанен. Разбаньте его в Telegram вручную или через /unban в боте.')
    return redirect(request.referrer or '/')


@app.route('/ban', methods=['POST'])
@login_required
def ban():
    user_id = request.form.get('user_id')
    if user_id:
        from datetime import datetime
        conn = get_db()
        conn.execute("UPDATE users SET is_banned=1, banned_at=?, ban_reason=? WHERE user_id=?",
                     (datetime.now().isoformat(), 'Ручной бан через панель', user_id))
        conn.commit()
        conn.close()
        flash(f'⛔️ Пользователь {user_id} добавлен в чёрный список.')
    return redirect(request.referrer or '/')


if __name__ == '__main__':
    app.run(host=WEB_HOST, port=WEB_PORT, debug=False)
