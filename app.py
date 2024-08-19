from flask import Flask, jsonify, render_template, request, redirect, url_for, session, flash
from flask_wtf import FlaskForm

from wtforms import StringField, PasswordField, SubmitField, TextAreaField, DateTimeField
from wtforms.validators import DataRequired, Email, ValidationError
import bcrypt
from flask_mysqldb import MySQL

app = Flask(__name__)

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'event'
app.secret_key = 'your_secret_key_here'

mysql = MySQL(app)

class RegisterForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired()])
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Register")

    def validate_email(self, field):
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM users WHERE email=%s", (field.data,))
        user = cursor.fetchone()
        cursor.close()
        if user:
            raise ValidationError('Email already taken.')

class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Login")

class EventForm(FlaskForm):
    name = StringField("Event Name", validators=[DataRequired()])
    location = StringField("Location", validators=[DataRequired()])
    date_time = DateTimeField("Date and Time", validators=[DataRequired()], format='%d/%m/%Y at %I:%M %p')
    category = StringField("Category", validators=[DataRequired()])
    description = TextAreaField("Description", validators=[DataRequired()])
    submit = SubmitField("Create Event")

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        username = form.username.data
        email = form.email.data
        password = form.password.data

        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        cursor = mysql.connection.cursor()
        cursor.execute("INSERT INTO users (username, email, password) VALUES (%s, %s, %s)", 
                       (username, email, hashed_password))
        mysql.connection.commit()
        cursor.close()

        flash("Registration successful! Please login.")
        return redirect(url_for('login'))

    return render_template('register.html', form=form)


@app.route('/rsvp/<int:event_id>/<string:status>', methods=['POST'])
def rsvp(event_id, status):
    if 'user_id' not in session:
        return jsonify(success=False, message="You need to log in to RSVP.")
    
    try:
        cursor = mysql.connection.cursor()
        
        cursor.execute("SELECT id FROM rsvps WHERE event_id=%s AND user_id=%s", (event_id, session['user_id']))
        rsvp = cursor.fetchone()
        
        if rsvp:
            cursor.execute("UPDATE rsvps SET status=%s WHERE id=%s", (status, rsvp[0]))
        else:
            cursor.execute("INSERT INTO rsvps (event_id, user_id, status) VALUES (%s, %s, %s)", 
                           (event_id, session['user_id'], status))
        
        mysql.connection.commit()
        cursor.close()
        return jsonify(success=True, message="RSVP status updated successfully.")
    
    except Exception as e:
        print(f"Error: {e}")
        return jsonify(success=False, message="An error occurred while processing your RSVP.")

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data

        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cursor.fetchone()
        cursor.close()

        if user and bcrypt.checkpw(password.encode('utf-8'), user[3].encode('utf-8')):
            session['user_id'] = user[0]  
            return redirect(url_for('main'))  
        else:
            flash("Login failed. Please check your email and password.", "error")
            return redirect(url_for('login'))

    return render_template('login.html', form=form)

@app.route('/main', methods=['GET', 'POST'])
def main():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    query = request.args.get('query')
    cursor = mysql.connection.cursor()

    if query:
        sql_query = """
            SELECT * FROM newevent 
            WHERE name LIKE %s 
            OR location LIKE %s 
            OR category LIKE %s
        """
        like_query = f"%{query}%"
        params = (like_query, like_query, like_query)
        cursor.execute(sql_query, params)
    else:
        cursor.execute("SELECT * FROM newevent ORDER BY created_at DESC")

    events = cursor.fetchall()
    events_with_rsvp_counts = []

    for event in events:
        event_id = event[0]
        
        cursor.execute("SELECT COUNT(*) FROM rsvps WHERE event_id=%s AND status='Going'", (event_id,))
        going_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM rsvps WHERE event_id=%s AND status='Maybe'", (event_id,))
        maybe_count = cursor.fetchone()[0]

        events_with_rsvp_counts.append({
            'event': event,
            'going_count': going_count,
            'maybe_count': maybe_count
        })

    cursor.close()

    return render_template('main.html', events=events_with_rsvp_counts)
@app.route('/edit_event/<int:event_id>', methods=['GET', 'POST'])
def edit_event(event_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM newevent WHERE id=%s", (event_id,))
    event = cursor.fetchone()

    if event is None or event[8] != session['user_id']:
        flash("You are not authorized to edit this event.")
        return redirect(url_for('main'))

    form = EventForm()

    if request.method == 'GET':
        form.name.data = event[1]
        form.location.data = event[2]
        form.date_time.data = event[3]
        form.description.data = event[4]
        form.category.data = event[7]

    if form.validate_on_submit():
        image_path = event[5]  
        if 'predefined_image' in request.form:
            image_path = request.form['predefined_image']

        try:
            query = """
                UPDATE newevent 
                SET name=%s, location=%s, date_time=%s, category=%s, description=%s, image_path=%s
                WHERE id=%s AND created_by=%s
            """
            params = (
                form.name.data, 
                form.location.data, 
                form.date_time.data, 
                form.category.data, 
                form.description.data, 
                image_path, 
                event_id, 
                session['user_id']
            )
            cursor.execute(query, params)
            mysql.connection.commit()
            cursor.close()

            flash("Event updated successfully!")
            return redirect(url_for('main'))

        except Exception as e:
            flash("An error occurred while updating the event. Please try again.")
            mysql.connection.rollback()

    return render_template('edit_event.html', form=form, event=event)

@app.route('/delete_event/<int:event_id>', methods=['POST'])
def delete_event(event_id):
    if 'user_id' in session:
        cursor = mysql.connection.cursor()
        cursor.execute("DELETE FROM newevent WHERE id=%s", (event_id,))
        mysql.connection.commit()
        cursor.close()
        flash("Event deleted successfully!")
        return redirect(url_for('main'))
    return redirect(url_for('login'))
@app.route('/add_comment/<int:event_id>', methods=['POST'])
def add_comment(event_id):
    if 'user_id' not in session:
        flash("You need to log in to comment.", "error")
        return redirect(url_for('event_detail', event_id=event_id))

    comment_text = request.form['comment']

    if not comment_text:
        flash("Comment cannot be empty.", "error")
        return redirect(url_for('event_detail', event_id=event_id))

    try:
        cursor = mysql.connection.cursor()
        cursor.execute("INSERT INTO comments (event_id, user_id, comment, created_at) VALUES (%s, %s, %s, NOW())", 
                       (event_id, session['user_id'], comment_text))
        mysql.connection.commit()
        cursor.close()
        flash("Comment added successfully!")
    except Exception as e:
        print(f"An error occurred: {e}")
        flash("An error occurred while adding your comment. Please try again.")
    
    return redirect(url_for('event_detail', event_id=event_id))

@app.route('/my_events')
def my_events():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM newevent WHERE created_by=%s", (session['user_id'],))
    events = cursor.fetchall()
    cursor.close()
    
    return render_template('my_events.html', events=events)  


@app.route('/event/<int:event_id>', methods=['GET', 'POST'])
def event_detail(event_id):
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM newevent WHERE id=%s", (event_id,))
    event = cursor.fetchone()

    cursor.execute("SELECT c.comment, c.created_at, u.username FROM comments c JOIN users u ON c.user_id = u.id WHERE event_id=%s ORDER BY c.created_at DESC", (event_id,))
    comments = cursor.fetchall()

    cursor.close()

    return render_template('event_detail.html', event=event, comments=comments)

@app.route('/create_event', methods=['GET', 'POST'])
def create_event():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    form = EventForm()
    if form.validate_on_submit():
        image_path = None
        if 'predefined_image' in request.form:
            image_path = request.form['predefined_image']

        try:
            cursor = mysql.connection.cursor()
            query = """
                INSERT INTO newevent (name, location, date_time, category, description, image_path, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            params = (form.name.data, form.location.data, form.date_time.data, form.category.data, form.description.data, image_path, session['user_id'])
            cursor.execute(query, params)
            mysql.connection.commit()
            cursor.close()

            flash("Event created successfully!")
            return redirect(url_for('main'))

        except Exception as e:
            flash("An error occurred while saving the event. Please try again.")
            mysql.connection.rollback()

    return render_template('create_event.html', form=form)

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash("You have been logged out successfully.")
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
