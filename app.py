from flask import Flask, render_template, request, session, redirect, url_for, flash
from flask_socketio import SocketIO, emit, join_room, leave_room
from models import db, Room, Message
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chat.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

active_users = {}

def create_tables():
    """Create database tables and add default room"""
    with app.app_context():
        db.create_all()
        
        if not Room.query.filter_by(name='General').first():
            general_room = Room(name='General')
            db.session.add(general_room)
            db.session.commit()

@app.route('/')
def index():
    """Landing page for username entry"""
    return render_template('index.html')

@app.route('/set_username', methods=['POST'])
def set_username():
    """Set username in session"""
    username = request.form.get('username', '').strip()
    if not username:
        flash('Please enter a valid username', 'error')
        return redirect(url_for('index'))
    
    session['username'] = username
    return redirect(url_for('room_list'))

@app.route('/rooms')
def room_list():
    """Display available chat rooms"""
    if 'username' not in session:
        return redirect(url_for('index'))
    
    rooms = Room.query.order_by(Room.created_at.desc()).all()
    return render_template('room_list.html', rooms=rooms, username=session['username'])

@app.route('/create_room', methods=['POST'])
def create_room():
    """Create a new chat room"""
    if 'username' not in session:
        return redirect(url_for('index'))
    
    room_name = request.form.get('room_name', '').strip()
    if not room_name:
        flash('Please enter a valid room name', 'error')
        return redirect(url_for('room_list'))
    
    if Room.query.filter_by(name=room_name).first():
        flash('Room already exists', 'error')
        return redirect(url_for('room_list'))
    
    new_room = Room(name=room_name)
    db.session.add(new_room)
    db.session.commit()
    
    flash(f'Room "{room_name}" created successfully!', 'success')
    return redirect(url_for('chat', room_id=new_room.id))

@app.route('/chat/<int:room_id>')
def chat(room_id):
    """Chat room interface"""
    if 'username' not in session:
        return redirect(url_for('index'))
    
    room = Room.query.get_or_404(room_id)
    
    messages = Message.query.filter_by(room_id=room_id)\
                          .order_by(Message.timestamp.desc())\
                          .limit(50)\
                          .all()
    messages.reverse()  
    
    return render_template('chat.html', room=room, messages=messages, username=session['username'])

@app.route('/logout')
def logout():
    """Clear session and redirect to home"""
    session.clear()
    return redirect(url_for('index'))

@socketio.on('join')
def handle_join(data):
    """Handle user joining a room"""
    username = session.get('username')
    room_id = data['room_id']
    room = Room.query.get(room_id)
    
    if not username or not room:
        return
    
    join_room(str(room_id))
    
    if str(room_id) not in active_users:
        active_users[str(room_id)] = set()
    active_users[str(room_id)].add(username)
    
    emit('status', {
        'msg': f'{username} has joined the room',
        'timestamp': datetime.now().strftime('%H:%M:%S')
    }, room=str(room_id))
    
    emit('user_count', {
        'count': len(active_users[str(room_id)])
    }, room=str(room_id))

@socketio.on('leave')
def handle_leave(data):
    """Handle user leaving a room"""
    username = session.get('username')
    room_id = data['room_id']
    
    if not username:
        return
    
    leave_room(str(room_id))
    
    if str(room_id) in active_users:
        active_users[str(room_id)].discard(username)
        if not active_users[str(room_id)]:
            del active_users[str(room_id)]
    
    emit('status', {
        'msg': f'{username} has left the room',
        'timestamp': datetime.now().strftime('%H:%M:%S')
    }, room=str(room_id))
    
    user_count = len(active_users.get(str(room_id), []))
    emit('user_count', {'count': user_count}, room=str(room_id))

@socketio.on('message')
def handle_message(data):
    """Handle new chat message"""
    username = session.get('username')
    room_id = data['room_id']
    message_content = data['message'].strip()
    
    if not username or not message_content:
        return
    
    # Save message to database
    new_message = Message(
        content=message_content,
        username=username,
        room_id=room_id
    )
    db.session.add(new_message)
    db.session.commit()
    
    # Broadcast message to room
    emit('message', {
        'message': message_content,
        'username': username,
        'timestamp': new_message.timestamp.strftime('%H:%M:%S')
    }, room=str(room_id))

@socketio.on('disconnect')
def handle_disconnect():
    """Handle user disconnect"""
    username = session.get('username')
    if username:
        # Remove from all rooms
        for room_id in list(active_users.keys()):
            if username in active_users[room_id]:
                active_users[room_id].discard(username)
                if not active_users[room_id]:
                    del active_users[room_id]
                else:
                    # Notify room about user leaving
                    emit('status', {
                        'msg': f'{username} has disconnected',
                        'timestamp': datetime.now().strftime('%H:%M:%S')
                    }, room=room_id)
                    emit('user_count', {
                        'count': len(active_users[room_id])
                    }, room=room_id)

if __name__ == '__main__':
    # Create tables before running the app
    create_tables()
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)