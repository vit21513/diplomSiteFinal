import json
import logging
import os
import random
import string
from datetime import datetime
from threading import Thread

from PIL import Image, ImageDraw, ImageFont
from flask import Flask, render_template, request, redirect, url_for, flash, make_response
from flask import send_file
from flask_bcrypt import Bcrypt
from flask_mail import Mail, Message
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField
from wtforms.validators import DataRequired, Email

from content_site import cadastre_dom, cadaste_zem, cadaste_act, invent_text, geo_site, project_site, gal_content
from models import db, Order, Gallery, ContentSite

MAILPASS = 'password_hidden'
FILENAMELOG = "/home/ustlabRoscadastr/email_errors.log"
FILENAMEORDER = "/home/ustlabRoscadastr/orders.json"
FILE_CAPTCHA = '/home/ustlabRoscadastr/mysite/static/captcha.png'
SENDER_MAIL = 'testroscadastr@mail.ru'
REPICIENT_MAIL = 'vit21513@yandex.ru'
ADMIN_PASSWORD_HASH = bcrypt.generate_password_hash('password_hidden').decode('utf-8')
# Настройки логирования
logging.basicConfig(filename='email_errors.log', level=logging.ERROR,
                    format='%(asctime)s - %(levelname)s - %(message)s')
app = Flask(__name__)
app.config[
    'SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://ustlabRoscadastr:password_hidden@ustlabRoscadastr.mysql.pythonanywhere-services.com/ustlabRoscadastr$default'
db.init_app(app)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.urandom(24)
app.config['MAIL_SERVER'] = 'smtp.mail.ru'
app.config['MAIL_PORT'] = 465  # Порт SMTP-сервера
app.config['MAIL_USE_SSL'] = True  # Использовать TLS
app.config['MAIL_USERNAME'] = 'testroscadastr@mail.ru'
app.config['MAIL_PASSWORD'] = MAILPASS
mail = Mail(app)
bcrypt = Bcrypt(app)


@app.cli.command("init-db")
def init_db():
    db.create_all()
    print('OK')


@app.cli.command("fill-db")
def fill_tables():
    names = ['cadaste_zem', 'cadastre_dom', 'cadaste_act', 'invent_text', 'geo_site', 'project_site']
    index = 0
    for item in [cadaste_zem, cadastre_dom, cadaste_act, invent_text, geo_site, project_site]:
        for content in item:
            new_content = ContentSite(name=str(names[index]), content=content)
            db.session.add(new_content)
        index += 1
        db.session.commit()
    for item in gal_content:
        new_content = Gallery(title=item['text'], url=item['path_img'])
        db.session.add(new_content)
    db.session.commit()


@app.route('/')
@app.route('/index/')
def index():
    return render_template('index.html')


# панель администратора
@app.route('/admin/', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        password = request.form['password']
        if bcrypt.check_password_hash(ADMIN_PASSWORD_HASH, password):
            return render_template('admin_panel.html')
        else:
            flash('Incorrect password', 'danger')
    return render_template('admin_login.html')


# скачать log files
@app.route('/download/log')
def download_log():
    try:
        send_file(FILENAMELOG, as_attachment=True)
    except Exception:
        return "file not found"
    return send_file(FILENAMELOG, as_attachment=True)


# скачать список заказов
@app.route('/download/orders')
def download_orders():
    try:
        send_file(FILENAMEORDER, as_attachment=True)
    except Exception:
        return f"file not found"
    return send_file(FILENAMEORDER, as_attachment=True)


# удалить логи
@app.route('/delete/log')
def delete_log():
    try:
        os.remove(FILENAMELOG)

    except Exception as e:
        return e
    return "file is deleted"


# удалить заказы
@app.route('/delete/orders')
def delete_orders():
    try:
        os.remove(FILENAMEORDER)
    except Exception:
        return f"file not found"
    return "file is deleted"


# страница геодезические работы
@app.route('/geo/')
def geo():
    geo = ContentSite.query.filter(ContentSite.name == 'geo_site').all()
    return render_template('geodesia.html', geo_site=geo)


# страница галерея
@app.route('/galereia/')
def galereia():
    objects = Gallery.query.all()
    return render_template('galerey.html', gal_content=objects)


# страница техническая инвентаризация
@app.route('/invent/')
def invent():
    invent_content = ContentSite.query.filter(ContentSite.name == 'invent_text').all()
    return render_template('invent.html', invent_text=invent_content)


# страница кадастровые работы
@app.route('/cadastr/')
def cadastr():
    zem = ContentSite.query.filter(ContentSite.name == 'cadaste_zem').all()
    dom = ContentSite.query.filter(ContentSite.name == 'cadastre_dom').all()
    act = ContentSite.query.filter(ContentSite.name == 'cadaste_act').all()
    return render_template('cadastr.html', cadaste_zem=zem, cadastre_dom=dom, cadaste_act=act)


# страница проектные работы
@app.route('/project/')
def project():
    site = ContentSite.query.filter(ContentSite.name == 'project_site').all()
    return render_template('project.html', project_site=site)


# страница контакты
@app.route('/contacts/')
def contacts():
    return render_template('contacts.html')


def generate_captcha():
    width, height = 200, 100
    image = Image.new('RGB', (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(image)
    captcha_text = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
    font = ImageFont.truetype('OpenSans-BoldItalic.ttf', size=30)
    text_width = 100
    text_height = 50
    x = (width - text_width) // 2
    y = (height - text_height) // 2
    # Рисуем текст на изображении
    draw.text((x, y), captcha_text, font=font, fill=(0, 0, 0))
    # Добавляем небольшой шум к изображению
    for _ in range(100):
        x = random.randint(0, width - 1)
        y = random.randint(0, height - 1)
        draw.point((x, y), fill=(0, 0, 0))
    image.save(FILE_CAPTCHA)
    return captcha_text


# форма заказа
class OrderForm(FlaskForm):
    selected_option = SelectField('Выберите опцию', choices=[
        ('Земельный участок', 'Земельный участок'),
        ('Жилой дом', 'Жилой дом'),
        ('Квартира', 'Квартира'),
        ('Иное', 'Иное'),
        ('Задать вопрос', 'Задать вопрос')
    ], validators=[DataRequired()])
    last_name = StringField('Фамилия', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Телефон', validators=[DataRequired()])
    message = StringField('Сообщение', validators=[DataRequired()])
    captcha = StringField('Проверочный код', validators=[DataRequired()])
    submit = SubmitField('Отправить')


def send_email_in_thread(text):
    try:
        msg = Message('Форма заказа', sender=SENDER_MAIL, recipients=[REPICIENT_MAIL])
        msg.body = text
        with app.app_context():
            mail.send(msg)
    except Exception as e:
        # Записываем событие и время в лог файл
        logging.error(f'Ошибка отправки электронной почты: {str(e)}')


# страница заказа
@app.route('/order/', methods=['GET', 'POST'])
def order():
    options = ['Земельный участок', 'Жилой дом, Квартира', 'Иное', 'Задать вопрос']
    form = OrderForm()
    if form.validate_on_submit():
        captcha = form.captcha.data
        if captcha == request.cookies.get('captcha'):
            # Получаем данные из формы
            selected_option = form.selected_option.data
            last_name = form.last_name.data
            email = form.email.data
            phone = form.phone.data
            message = form.message.data
            order = Order(last_name=last_name, email=email, phone=phone, message=message)
            db.session.add(order)
            db.session.commit()
            # Создаем словарь с данными, включая выбранный элемент списка
            data = {
                'Выбранный элемент': selected_option,
                'Имя Фамилия': last_name,
                'Email адрес': email,
                'Номер телефона': phone,
                'Сообщение': message,
                'Дата создания': str(datetime.now())
            }
            flash('Ваше обращение отправлено', "success")
            save_to_json(data)
            # Отправка письма в отдельном потоке
            thread = Thread(target=send_email_in_thread, args=(str(data)[1:-1],))
            thread.start()
            response = make_response(redirect(url_for('order')))
            response.set_cookie('captcha', '', expires=0)  # Удаляем куку с капчей
            return response
        else:
            flash('Неправильный проверочный код', "warning")
    # Генерируем капчу и сохраняем в куки
    captcha = generate_captcha()
    response = make_response(render_template('orders.html', form=form, options=options, captcha=captcha))
    response.set_cookie('captcha', captcha)
    return response


def save_to_json(data):
    # Загружаем текущие заказы (если есть)
    try:
        with open('orders.json', 'r', encoding="UTF-8") as f:
            orders = json.load(f)
    except FileNotFoundError:
        orders = []
    # Добавляем новый заказ
    orders.append(data)
    # Сохраняем заказы обратно в файл
    with open('orders.json', 'w', encoding="UTF-8") as f:
        json.dump(orders, f, ensure_ascii=False, indent=1)


if __name__ == '__main__':
    app.run(debug=True)
