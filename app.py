from flask import Flask,render_template as rt,request,redirect,url_for,flash,Blueprint,current_app,session
from classes import Person,Admin,Librarian,User
import os
from dotenv import load_dotenv
from db import get_db_connection
import bcrypt
from datetime import datetime
from book import Book, BookType
from libcat import LibCat


load_dotenv()
app=Flask(__name__) #I'm creating an instance of Flask class
app.secret_key=os.getenv("SECRET_KEY",'thisisasecretkey')

@app.route("/") #listening for root
def home():
    return rt("home.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        role = request.form.get("role")
        
        pwd_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        if Person.check_user_exists(username, email):
            flash("Username or email already exists")
            return redirect(url_for("register"))
        human=None
        if role == "Admin":
            salary = request.form.get("salary")
            admin_level = request.form.get("admin_level")
            human = Admin(first_name, last_name, username, email, pwd_hash, salary, admin_level)
            
        elif role == "Librarian":
            salary = request.form.get("salary")
            employment_date = request.form.get("employment_date")
            human = Librarian(first_name, last_name, username, email, pwd_hash, salary, employment_date)

        elif role == "User":
            membership_start_date_str = request.form.get("membership_start_date")
            membership_end_date_str = request.form.get("membership_end_date")
            membership_start_date = datetime.strptime(membership_start_date_str, '%Y-%m-%d').date()
            membership_end_date = datetime.strptime(membership_end_date_str, '%Y-%m-%d').date()
            human = User(first_name, last_name, username, email, pwd_hash, membership_start_date, membership_end_date)

        try:
            human.save_to_db()
            flash("User registered successfully")
            return redirect(url_for("login"))
        except ValueError as e:
            flash(str(e))
            return redirect(url_for("register"))

    return rt("register.html")

            
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        cursor = conn.cursor()
        q = "SELECT * FROM Person WHERE username = %s"
        cursor.execute(q, (username,))
        person = cursor.fetchone()
        conn.close()
        
        if person and bcrypt.checkpw(password.encode('utf-8'), person[5].encode('utf-8')):
            role = person[6]  # Assuming the role is in the 6th column
            if role == "User":
                return redirect(url_for('user_home', user_id=person[0]))
            elif role == "Librarian":
                return redirect(url_for('librarian_home', librarian_id=person[0]))
            elif role == "Admin":
                return redirect(url_for('admin_home', admin_id=person[0]))
        else:
            flash('Invalid username or password!')
            return redirect(url_for('login'))
    return rt('login.html')

def getPersonByID(human_id):
    con=get_db_connection()
    cur=con.cursor()
    q="SELECT * FROM Person WHERE person_id = %s"
    values=(human_id,)
    cur.execute(q,values)
    human=cur.fetchone()
    cur.close()
    con.close()
    return human

@app.route("/user_home/<int:user_id>")
def user_home(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    q = "SELECT * FROM Person WHERE person_id = %s"
    cursor.execute(q, (user_id,))
    user = cursor.fetchone()
    conn.close()
    
    if user:
        return rt('user_home.html', user=user)
    else:
        flash('User not found!')
        return redirect(url_for('login'))
    
@app.route("/admin_home/<int:admin_id>") 
def admin_home(admin_id):
    admin=getPersonByID(admin_id)
    return rt('admin_home.html',admin=admin)



@app.route('/librarian_home/<int:librarian_id>', methods=['GET', 'POST'])
def librarian_home(librarian_id):
    librarian = getPersonByID(librarian_id)
    if not librarian:
        flash('Librarian not found!')
        return redirect(url_for('login'))
         
    if request.method == 'POST':
        return place_order(librarian_id)
    
    # Render the librarian homepage template with librarian data
    return rt('librarian_homepage.html', librarian=librarian, librarian_id=librarian_id)

@app.route('/librarian_home/<int:librarian_id>/place_order', methods=['POST'])
def place_order(librarian_id):
    if request.method == 'POST':
        book_title = request.form['bookTitle']
        author = request.form['author']
        quantity = request.form['quantity']
        
        # Currently this method will check in the books table if the entry is present will increase the permanent copies by 1 
        
        con = get_db_connection()
        cur = con.cursor()
        q = "UPDATE book SET NumberOfCopies=NumberOfCopies+%s where author= %s and title=%s;"
        values = (quantity, author,book_title)
        cur.execute(q, values)
        con.commit()
        cur.close()
        con.close()
    
       
        print(f"Order placed by Librarian ID {librarian_id}: {quantity} of '{book_title}' by {author}")
        
        flash('Order placed successfully!')
        return redirect(url_for('librarian_home', librarian_id=librarian_id))

@app.route('/librarian_home/<int:librarian_id>/edit', methods=['POST'])
def update_librarian_profile(librarian_id):
    # Retrieve form data from POST request
    first_name = request.form['first_name']
    last_name = request.form['last_name']
    username = request.form['username']
    email = request.form['email']
    
    con = get_db_connection()
    cur = con.cursor()
    q = "UPDATE Person SET first_name=%s, last_name=%s, username=%s, email=%s WHERE person_id=%s"
    values = (first_name, last_name, username, email, librarian_id)
    cur.execute(q, values)
    con.commit()
    cur.close()
    con.close()
    
    flash("Profile Updated")
    return redirect(url_for('librarian_home', librarian_id=librarian_id))


@app.route('/librarian_home/<int:librarian_id>/edit', methods=['GET', 'POST'])
def edit_librarian_profile(librarian_id):
    librarian = getPersonByID(librarian_id)
    if not librarian:
        flash('Something went wrong')
        return redirect(url_for('login'))  # Redirect to login if librarian not found
    
    if request.method == 'POST':
        return update_librarian_profile(librarian_id)
        
    
    # Render the edit librarian profile template with librarian data
    return rt('edit_librarian_profile.html', librarian=librarian,librarian_id=librarian_id)



@app.route('/manage_users')
def manage_users():
    return "Manage Users Page"

@app.route('/view_reports')
def view_reports():
    return "View Reports Page"

@app.route('/manage_books')
def manage_books():
    return "Manage Books Page"

@app.route('/view_borrowed_books')
def view_borrowed_books():
    return "View Borrowed Books Page" 
    
@app.route('/add_book', methods=['GET', 'POST'])
def add_book():
    if request.method == 'POST':
        data = request.form
        book = Book(
            book_id=None,
            title=data['title'],
            author=data['author'],
            isbn=data['isbn'],
            genre=data['genre'],
            publication_date=data['publication_date'],
            book_type=BookType[data['book_type'].upper()]
        )
        number_of_books_added = int(data['number_of_books_added'])
        libcat = LibCat(current_app.config['DB_CONNECTION'])
        libcat.add_new_book(book, number_of_books_added)
        flash("Book added successfully")
        return redirect(url_for('book_routes.add_book'))
    
    return rt('add_book.html')

@app.route('/delete_book', methods=['GET', 'POST'])
def delete_book():
    if request.method == 'POST':
        data = request.form
        isbn = data['isbn']
        libcat = LibCat(current_app.config['DB_CONNECTION'])
        book_details = libcat.view_book_details(isbn)
        
        if book_details:
            book = Book(
                book_id=book_details['BookID'],
                title=book_details['Title'],
                author=book_details['Author'],
                isbn=book_details['ISBN'],
                genre=book_details['Genre'],
                publication_date=book_details['PublicationDate'],
                book_type=BookType[book_details['BookType']]
            )
            libcat.delete_book(book)
            flash("Book deleted successfully")
        else:
            flash("Book not found")
        
        return redirect(url_for('book_routes.delete_book'))
    
    return rt('delete_book.html')

@app.route('/borrow_book', methods=['GET', 'POST'])
def borrow_book():
    if request.method == 'POST':
        data = request.form
        isbn = data['isbn']
        
        libcat = LibCat(current_app.config['DB_CONNECTION'])
        book_details = libcat.view_book_details(isbn)
        
        if book_details:
            book = Book(
                book_id=book_details['BookID'],
                title=book_details['Title'],
                author=book_details['Author'],
                isbn=book_details['ISBN'],
                genre=book_details['Genre'],
                publication_date=book_details['PublicationDate'],
                book_type=BookType[book_details['BookType']]
            )
            libcat.borrow_book(book)
            flash("Book borrowed successfully")
        else:
            flash("Book not found")
        
        return redirect(url_for('book_routes.borrow_book'))
    
    return rt('borrow_book.html')

@app.route('/return_book', methods=['GET', 'POST'])
def return_book():
    if request.method == 'POST':
        data = request.form
        isbn = data['isbn']
        
        libcat = LibCat(current_app.config['DB_CONNECTION'])
        book_details = libcat.view_book_details(isbn)
        
        if book_details:
            book = Book(
                book_id=book_details['BookID'],
                title=book_details['Title'],
                author=book_details['Author'],
                isbn=book_details['ISBN'],
                genre=book_details['Genre'],
                publication_date=book_details['PublicationDate'],
                book_type=BookType[book_details['BookType']]
            )
            libcat.return_book(book)
            flash("Book returned successfully")
        else:
            flash("Book not found")
        
        return redirect(url_for('book_routes.return_book'))
    
    return rt('return_book.html')

@app.route('/view_books')
def view_books():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
    
    q = """
    SELECT books.title, books.author, books.isbn, borrowed_books.borrow_date, borrowed_books.return_date
    FROM books
    JOIN borrowed_books ON books.book_id = borrowed_books.book_id
    WHERE borrowed_books.user_id = %s
    """
    cursor = current_app.config['DB_CONNECTION'].cursor(dictionary=True)
    cursor.execute(q, (user_id,))
    borrowed_books = cursor.fetchall()
    cursor.close()
    
    return rt("view_books.html", books=borrowed_books)


    
    

if __name__=="__main__":
    app.run(debug=True)