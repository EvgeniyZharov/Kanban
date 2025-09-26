from flask import Flask, render_template, request, jsonify
from datetime import datetime
from db_client import PostgresDB
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Конфигурация базы данных
DB_CONFIG = {
}

def get_db():
    return PostgresDB(**DB_CONFIG)

@app.route('/')
def index():
    db = get_db()
    assignees = db.fetch_all("SELECT name FROM assignees ORDER BY name")
    assignee_list = [assignee['name'] for assignee in assignees]
    return render_template('kanban.html', assignees=assignee_list)

@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    db = get_db()
    tasks = db.fetch_all("""
        SELECT id, title, description, status, assignee, priority, 
               due_date, created_at, updated_at
        FROM tasks 
        ORDER BY 
            CASE priority 
                WHEN 'high' THEN 1 
                WHEN 'medium' THEN 2 
                WHEN 'low' THEN 3 
                ELSE 4 
            END,
            created_at DESC
    """)
    return jsonify(tasks)

@app.route('/api/tasks/<int:task_id>', methods=['GET'])
def get_task(task_id):
    db = get_db()
    try:
        task = db.fetch_one("""
            SELECT id, title, description, status, assignee, priority, 
                   due_date, created_at, updated_at
            FROM tasks WHERE id = %s
        """, (task_id,))
        if task:
            return jsonify(task)
        else:
            return jsonify({'error': 'Task not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/assignees', methods=['GET'])
def get_assignees():
    db = get_db()
    assignees = db.fetch_all("SELECT name FROM assignees ORDER BY name")
    assignee_list = [assignee['name'] for assignee in assignees]
    return jsonify(assignee_list)

@app.route('/api/tasks', methods=['POST'])
def create_task():
    db = get_db()
    data = request.get_json()

    if not data.get('title'):
        return jsonify({'error': 'Title is required'}), 400

    # Корректная обработка даты
    due_date = data.get('due_date')
    if due_date == '' or due_date is None:
        due_date = None
    elif due_date:
        # Проверяем корректность формата даты
        try:
            datetime.strptime(due_date, '%Y-%m-%d')
        except ValueError:
            return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400

    task_data = {
        'title': data.get('title', '').strip(),
        'description': data.get('description', '').strip(),
        'status': data.get('status', 'backlog'),
        'assignee': data.get('assignee', ''),
        'priority': data.get('priority', 'medium'),
        'due_date': due_date,
        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }

    try:
        new_id = db.insert('tasks', task_data)
        if new_id:
            new_task = db.fetch_one("SELECT * FROM tasks WHERE id = %s", (new_id,))
            return jsonify(new_task), 201
        else:
            return jsonify({'error': 'Failed to create task'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/tasks/<int:task_id>', methods=['PUT'])
def update_task(task_id):
    db = get_db()
    data = request.get_json()
    print("FUCK")

    # Проверяем существование задачи
    existing_task = db.fetch_one("SELECT id FROM tasks WHERE id = %s", (task_id,))
    print(existing_task)
    if not existing_task:
        return jsonify({'error': 'Task not found'}), 404

    if not data.get('title'):
        return jsonify({'error': 'Title is required'}), 400

    # Корректная обработка даты
    due_date = data.get('due_date')
    print(due_date)
    if due_date == '' or due_date is None:
        due_date = None
    elif due_date:
        try:
            datetime.strptime(due_date, '%Y-%m-%d')
        except ValueError:
            return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
    print(data)
    # Подготавливаем данные для обновления
    update_data = {
        'title': data.get('title', '').strip(),
        'description': data.get('description', '').strip(),
        'status': data.get('status', 'backlog'),
        'assignee': data.get('assignee', ''),
        'priority': data.get('priority', 'medium'),
        'due_date': due_date,
    }

    # Формируем SQL запрос для обновления
    set_clause = ', '.join([f"{key} = %s" for key in update_data.keys()])
    values = list(update_data.values())
    values.append(task_id)

    sql = f"UPDATE tasks SET {set_clause} WHERE id = %s RETURNING *"
    print(sql)
    try:
        update_dd = db.execute(sql=sql, params=tuple(values))
        print(update_dd)
        updated_task = db.fetch_one(sql, tuple(values))
        print(updated_task)
        if updated_task:
            return jsonify(updated_task)
        else:
            return jsonify({'error': 'Failed to update task'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    db = get_db()

    existing_task = db.fetch_one("SELECT id FROM tasks WHERE id = %s", (task_id,))
    if not existing_task:
        return jsonify({'error': 'Task not found'}), 404

    try:
        db.execute_without_return("DELETE FROM tasks WHERE id = %s", (task_id,))
        return jsonify({'message': 'Task deleted successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/tasks/<int:task_id>/move', methods=['POST', 'PUT'])
def move_task(task_id):
    db = get_db()
    data = request.get_json()

    new_status = data.get('status')

    if not new_status:
        return jsonify({'error': 'Status not specified'}), 400

    valid_statuses = ['backlog', 'todo', 'in-progress', 'done']
    if new_status not in valid_statuses:
        return jsonify({'error': f'Invalid status. Must be one of: {valid_statuses}'}), 400

    existing_task = db.fetch_one("SELECT id FROM tasks WHERE id = %s", (task_id,))
    if not existing_task:
        return jsonify({'error': 'Task not found'}), 404

    try:
        sql = """
            UPDATE tasks 
            SET status = %s, updated_at = %s 
            WHERE id = %s 
            RETURNING *
        """
        updated_task = db.fetch_one(sql, (
            new_status,
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            task_id
        ))

        if updated_task:
            return jsonify(updated_task)
        else:
            return jsonify({'error': 'Failed to update task status'}), 500

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/tasks/<int:task_id>/status', methods=['PUT'])
def update_task_status(task_id):
    return move_task(task_id)

@app.route('/api/assignees', methods=['POST'])
def create_assignee():
    db = get_db()
    data = request.get_json()

    if not data.get('name'):
        return jsonify({'error': 'Name is required'}), 400

    try:
        db.upsert('assignees', {'name': data['name']}, 'name')
        return jsonify({'message': 'Assignee created successfully'}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats', methods=['GET'])
def get_stats():
    db = get_db()

    stats = db.fetch_all("""
        SELECT 
            status as status,
            COUNT(*) as count,
            COUNT(CASE WHEN due_date IS NOT NULL AND due_date < CURRENT_DATE THEN 1 END) as overdue
        FROM tasks 
        GROUP BY status
    """)

    return jsonify(stats)

if __name__ == '__main__':

    app.run(debug=True, host='0.0.0.0', port=5000)
