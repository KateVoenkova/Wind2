from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_migrate import Migrate
from models import db, Book, Character, CharacterRelationship
from name_parser import get_names_from_file
from relationships import find_relationships
import os
import uuid
import logging
import chardet

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///library.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.secret_key = 'super-secret-key'

db.init_app(app)
migrate = Migrate(app, db)


@app.route('/', methods=['GET', 'POST'])
def index():
    try:
        if request.method == 'POST':
            file = request.files.get('file')
            title = request.form.get('title', 'Без названия')

            if not file or file.filename == '':
                return "Файл не выбран", 400

            filename = f"{uuid.uuid4()}.txt"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            with open(filepath, 'rb') as f:
                result = chardet.detect(f.read())
                encoding = result['encoding'] or 'utf-8'

            try:
                names = get_names_from_file(filepath)
                logger.debug(f"Найдены имена: {names}")
                if not names:
                    raise ValueError("Не найдено ни одного имени")
            except Exception as e:
                logger.error(f"Ошибка парсинга: {str(e)}")
                return f"Ошибка обработки файла: {str(e)}", 500

            new_book = Book(title=title)
            db.session.add(new_book)
            db.session.commit()

            for name in names:
                normalized_name = name.lower().strip()
                character = Character(
                    name=name,
                    normalized_name=normalized_name,
                    book_id=new_book.id
                )
                db.session.add(character)

            db.session.commit()

            try:
                find_relationships(new_book.id, filepath)
                logger.debug("Связи успешно сохранены")
            except Exception as e:
                logger.error(f"Ошибка поиска связей: {str(e)}")
                return "Ошибка обработки связей", 500

            return redirect(url_for('book_page', book_id=new_book.id))

        books = Book.query.all()
        return render_template('index.html', books=books)

    except Exception as e:
        logger.error(f"Ошибка: {str(e)}", exc_info=True)
        return "Internal Server Error", 500


@app.route('/books/<int:book_id>')
def book_page(book_id):
    book = Book.query.get_or_404(book_id)
    return render_template('book.html', book=book)


@app.route('/books/<int:book_id>/delete', methods=['POST'])
def delete_book(book_id):
    try:
        book = Book.query.get_or_404(book_id)
        db.session.delete(book)
        db.session.commit()
        return redirect(url_for('index'))
    except Exception as e:
        logger.error(f"Ошибка удаления: {str(e)}", exc_info=True)
        return "Internal Server Error", 500


@app.route('/books/<int:book_id>/edit', methods=['GET', 'POST'])
def edit_book(book_id):
    try:
        book = Book.query.get_or_404(book_id)

        if request.method == 'POST':
            new_title = request.form.get('title')
            if not new_title:
                return "Название не может быть пустым", 400

            book.title = new_title
            db.session.commit()
            return redirect(url_for('book_page', book_id=book.id))

        return render_template('edit_book.html', book=book)

    except Exception as e:
        logger.error(f"Ошибка редактирования: {str(e)}")
        return "Internal Server Error", 500


@app.route('/books/<int:book_id>/characters')
def manage_characters(book_id):
    book = Book.query.get_or_404(book_id)
    characters = Character.query.filter_by(book_id=book_id).all()
    return render_template('characters.html', book=book, characters=characters)


@app.route('/characters/<int:character_id>/delete', methods=['POST'])
def delete_character(character_id):
    character = Character.query.get_or_404(character_id)
    db.session.delete(character)
    db.session.commit()
    return redirect(url_for('manage_characters', book_id=character.book_id))


@app.route('/characters/<int:character_id>/edit', methods=['POST'])
def edit_character(character_id):
    character = Character.query.get_or_404(character_id)
    new_name = request.form.get('name')
    character.name = new_name
    db.session.commit()
    return redirect(url_for('manage_characters', book_id=character.book_id))


@app.route('/books/<int:book_id>/graph')
def show_graph(book_id):
    book = Book.query.get_or_404(book_id)
    return render_template('graph.html', book=book)


@app.route('/api/books/<int:book_id>/graph')
def get_graph_data(book_id):
    characters = Character.query.filter_by(book_id=book_id).all()
    relationships = CharacterRelationship.query.filter_by(book_id=book_id).all()

    nodes = [{
        "id": char.id,
        "name": char.name
    } for char in characters]

    links = [{
        "source": rel.character1_id,
        "target": rel.character2_id,
        "value": rel.weight
    } for rel in relationships]

    return jsonify({"nodes": nodes, "links": links})


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(debug=True)