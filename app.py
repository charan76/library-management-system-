from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import sqlite3
import hashlib

app = Flask(__name__)
app.secret_key = "secret_key_for_session"  # Used for managing session data

DATABASE = 'E-library.db'


# Database Initialization
def init_db():
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        # Create members table
        cursor.execute('''CREATE TABLE IF NOT EXISTS members (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            username TEXT NOT NULL UNIQUE,
                            password TEXT NOT NULL)''')
        # Create books table
        cursor.execute('''CREATE TABLE IF NOT EXISTS books (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            title TEXT NOT NULL,
                            author TEXT NOT NULL,
                            quantity INTEGER NOT NULL)''')
        # Create transactions table
        cursor.execute('''CREATE TABLE IF NOT EXISTS transactions (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            member_id INTEGER,
                            book_id INTEGER,
                            status TEXT CHECK(status IN ('Borrowed', 'Returned')),
                            FOREIGN KEY (member_id) REFERENCES members(id),
                            FOREIGN KEY (book_id) REFERENCES books(id))''')

        # Insert 10 sample books if none exist
        cursor.execute('SELECT COUNT(*) FROM books')
        if cursor.fetchone()[0] == 0:  # If no books exist
            sample_books = [
                ('The Great Gatsby', 'F. Scott Fitzgerald', 5),
                ('To Kill a Mockingbird', 'Harper Lee', 3),
                ('1984', 'George Orwell', 4),
                ('Pride and Prejudice', 'Jane Austen', 6),
                ('The Catcher in the Rye', 'J.D. Salinger', 4),
                ('Moby Dick', 'Herman Melville', 2),
                ('War and Peace', 'Leo Tolstoy', 3),
                ('The Hobbit', 'J.R.R. Tolkien', 7),
                ('Harry Potter and the Philosopher\'s Stone', 'J.K. Rowling', 10),
                ('The Lord of the Rings', 'J.R.R. Tolkien', 5)
            ]
            cursor.executemany('INSERT INTO books (title, author, quantity) VALUES (?, ?, ?)', sample_books)
        conn.commit()


# Route: Home Page
@app.route('/')
def home():
    return render_template('home.html')


# Route: Register New User
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = hashlib.sha256(request.form['password'].encode()).hexdigest()

        try:
            with sqlite3.connect(DATABASE) as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO members (username, password) VALUES (?, ?)", (username, password))
                conn.commit()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            return "Username already exists. Please try again with a different username."

    return render_template('register.html')


# Route: Login User
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = hashlib.sha256(request.form['password'].encode()).hexdigest()

        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM members WHERE username=? AND password=?", (username, password))
            member = cursor.fetchone()
            if member:
                session['member_id'] = member[0]
                return redirect(url_for('books'))
            else:
                return "Invalid credentials. Please try again."

    return render_template('login.html')


# Route: View All Books
@app.route('/books')
def books():
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM books")
        books = cursor.fetchall()
    return render_template('books.html', books=books)


# Route: Borrow or Return Books
@app.route('/borrow_return', methods=['GET', 'POST'])
def borrow_return():
    if 'member_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        action = request.form['action']
        book_id = request.form['book_id']
        member_id = session['member_id']

        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            if action == 'borrow':
                cursor.execute("SELECT quantity FROM books WHERE id=?", (book_id,))
                result = cursor.fetchone()
                if result and result[0] > 0:
                    cursor.execute("INSERT INTO transactions (member_id, book_id, status) VALUES (?, ?, 'Borrowed')",
                                   (member_id, book_id))
                    cursor.execute("UPDATE books SET quantity = quantity - 1 WHERE id=?", (book_id,))
                    conn.commit()
                    return "Book successfully borrowed."
                else:
                    return "Book is not available."
            elif action == 'return':
                cursor.execute('''SELECT id FROM transactions 
                                  WHERE member_id=? AND book_id=? AND status='Borrowed' ''', (member_id, book_id))
                transaction = cursor.fetchone()
                if transaction:
                    cursor.execute("UPDATE transactions SET status='Returned' WHERE id=?", (transaction[0],))
                    cursor.execute("UPDATE books SET quantity = quantity + 1 WHERE id=?", (book_id,))
                    conn.commit()
                    return "Book successfully returned."
                else:
                    return "No borrowed record found for this book."
    return render_template('borrow_return.html')


# Route: Logout
@app.route('/logout')
def logout():
    session.pop('member_id', None)
    return redirect(url_for('home'))


# Route: Admin to Add Books
@app.route('/add_book', methods=['GET', 'POST'])
def add_book():
    if 'member_id' not in session:
        return redirect(url_for('login'))  # Ensure only logged-in users can access

    if request.method == 'POST':
        title = request.form['title']
        author = request.form['author']
        quantity = int(request.form['quantity'])

        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO books (title, author, quantity) VALUES (?, ?, ?)", (title, author, quantity))
            conn.commit()
        return "Book added successfully!"

    return render_template('add_book.html')

    # return '''
    #     <form method="POST">
    #         <input type="text" name="title" placeholder="Book Title" required><br>
    #         <input type="text" name="author" placeholder="Author" required><br>
    #         <input type="number" name="quantity" placeholder="Quantity" required><br>
    #         <button type="submit">Add Book</button>
    #     </form>
    # '''


if __name__ == '__main__':
    init_db()
    app.run(debug=True)
