# -*- coding: utf-8 -*-
from flask import Flask, render_template, request, redirect, json
from sqlalchemy import create_engine, MetaData
from wtforms import Form, SubmitField, TextAreaField
from wtforms.validators import DataRequired
from sqlalchemy.orm import sessionmaker
import re, pymarc, os, os.path, time, locale, datetime
import string
from flask import make_response
from titles import overwrite_author
import subprocess as sb
import hashlib
import logging

logging.basicConfig(format=u'%(filename)s# %(levelname)-4s [%(asctime)s]  %(message)s',
                    level=logging.DEBUG, filename=u'example.log')

locale.setlocale(locale.LC_ALL, 'ru_RU.UTF-8')

app = Flask(__name__)
sql = u"""INSERT IGNORE INTO aleph3 (id, author, title, field, info, info_text)
        VALUES (%(id)s, %(author)s, %(title)s,%(field)s,%(info)s,%(info_text)s)
        """


class MyForm(Form):
    card_lines = TextAreaField(validators=[DataRequired()])  # форма для отрисовки строк в карточках в базе aleph3
    submit = SubmitField('Submit', validators=[DataRequired()])
    copy = SubmitField('Copy card', validators=[DataRequired()])


def t(n):
    if n not in ('SID', '000', '001', '003', '005', '008', '017', '035', '040', '018', '019', '044', '020',
                 '336', '337', '338', '538', '852', '912', '979', '856', '533', 'SYS', 'OWN', 'UID', 'FMT', 'CAT',
                 'LKR', '954', '955', '956', '010', '011', '012', '013', '014', '015', '100', '700'):
        return True
    return False


def url_for_other_page(page):
    args = request.view_args.copy()
    args['page'] = page
    return url_for(request.endpoint, **args)


app.jinja_env.globals['url_for_other_page'] = url_for_other_page

engine = create_engine('mysql://marc:123@localhost/marc?charset=utf8',
                       encoding='utf-8', convert_unicode=True)  # подключение к БД
Session = sessionmaker(bind=engine)
metadata = MetaData(bind=engine)


@app.route('/')
def index():
    ip = request.environ['REMOTE_ADDR']
    user_client = request.user_agent.string
    t1 = os.path.getmtime('static/marc_cards.mrc')  # дата последнего изменения файла
    t2 = os.path.getmtime('static/marc_cards.txt')  # дата последнего изменения файла
    # напечатать дату в строковом формате:
    data_t1 = time.ctime(t1)
    data_t2 = time.ctime(t2)
    folder_size1 = os.path.getsize('static/marc_cards.mrc')
    folder_size2 = os.path.getsize('static/marc_cards.txt')
    f = open('num_file.txt', 'r')
    f = f.readlines()
    total = f[0]
    true_c = f[1]
    wrong_c = f[2]
    r = 4784
    last = int(r) - int(total)
    logging.info(u'%s зашел на главную страницу' % ip)
    logging.info(u'%s' % user_client)
    return render_template('index.html', data1=data_t1, data2=data_t2,
                           s1=folder_size1, s2=folder_size2, tc=true_c, wc=wrong_c, t=total,
                           r=r, last=last)


@app.route('/check_list')
def check():
    ip = request.environ['REMOTE_ADDR']
    connection = engine.connect()
    connection.execute("SET character_set_connection=utf8")
    books = []
    for number in xrange(0, 48):
        result = connection.execute('select id, title from parser_cards order by id limit %s00,100;' % number)
        excel = []
        check_lr_num = 0
        for row in result.fetchall():
            excel.append(row)
        for element in excel:
            element0 = element[0]
            litresnum = '%0.6i' % int(element0) + 'Ru-MoLR'
            result2 = connection.execute("select * from aleph3 where (id='%s');" % litresnum)
            l = []
            if result2.fetchall() != l:
                check_lr = (u'Книга обработана!',)
            else:
                check_lr = ('',)
                check_lr_num += 1
        books.append((check_lr_num, number))
    # print books
    logging.info(u'%s зашел на check' % ip)
    return render_template('check.html', books=books)


@app.route('/create_marc_card', methods=['POST', 'GET'])
def start_create_marc():
    ip = request.environ['REMOTE_ADDR']
    # d = ['python','run.sh']
    print "sstart "
    x = sb.Popen(['/bin/bash', '/home/helga/olgavr/marcapp/run.sh'], stdout=sb.PIPE, stderr=sb.PIPE)
    # line = x.stdout.readline()
    time.sleep(0.1)
    logging.info(u'%s скачал файл с главной' % ip)
    logging.info(x.poll())
    if x.poll() == 3:
        logging.debug(u'%s Слишком часто нажимает!1' % ip)
        return json.dumps({'success': 'already running'}), 200, {'ContentType': 'application/json'}
    return json.dumps({'success': True}), 200, {'ContentType': 'application/json'}


@app.route('/show/<number>')
def show_book(number):
    connection = engine.connect()
    connection.execute("SET character_set_connection=utf8")
    result = connection.execute("select * from parser_cards where (id='%s');" % number)  # забираем строчку задания
    excel = []
    form = MyForm(request.form)
    for row1 in result.fetchall():
        mystring = []  # собираем эти строки в список
        mystring.append(row1[0])  # номер
        mystring.append(row1[1])  # автор
        mystring.append(row1[2])  # название книги
        mystring.append(row1[3])  # издательство
        mystring.append(row1[4])  # ISBN
        mystring.append(row1[5])  # формат файла
        mystring.append(row1[6])  # название файла
        mystring.append(row1[7])  # размер файла
        excel.append(mystring)
    books = []  # в этом списке лежат id на все книги (001 и 003 поля)
    for element in excel:
        element = element[0]  # выделяем номер для поиска в базе excel2base
        result = connection.execute("SELECT * FROM marc.parse2base WHERE (number='%s');" % element)
        ids = []
        for row in result.fetchall():
            idaleph = row[0]  # из всех найденных строк выделяем idaleph и отправляем в список ids
            ids.append(idaleph)
        books.append(ids)
    # books = filter(None, books)  # чистим от пустых списков, которые появляются, если книга не была найдена
    mybooks = []  # тут лежат все карточки на все книги
    n = 0
    for book in books:
        mymulti_cards = []
        for one_card in book:
            result = connection.execute("SELECT * FROM marc.aleph3 WHERE (id='%s') ORDER BY FIELD " % one_card)
            myone_card = []
            for row in result.fetchall():  # делаем словарь - одна строка из таблицы aleph3
                row = dict(id=row[0], author=row[1], title=row[2], field='%-5s' % row[3], info=row[5], num=n)
                myone_card.append(row)  # словарь кладем в myone_card - это одна карточка на одну книгу
                n += 1
            mymulti_cards.append(myone_card)  # теперь mymulti_cards - это список карточек для каждой книги
        mybooks.append(mymulti_cards)  # теперь mybooks - это список из книг
        # в котором лежит список из карточек на книги
        # в котором лежат списки на каждую карточку
        # в которых словари-строчки каждой карточки
    litrescard = []  # из карточек для каждой книги находим самую длинную и сохраняем ее
    litresnum = '%0.6i' % int(number) + 'Ru-MoLR'
    result = connection.execute(
        "SELECT id, author, title, field, info_text FROM marc.aleph3 WHERE (id='%s') ORDER BY FIELD " % litresnum)
    for (id, author, title, field, info_text) in result.fetchall():
        litrescard.append(dict(field='%-5s' % field, info=info_text))
    (result_count,) = connection.execute("select count(*) from parser_cards e where e.id<=%s order by id" % number)
    my_list_int = (int(result_count[0]) - 1) / 100
    ip = request.environ['REMOTE_ADDR']
    user_client = request.user_agent.string
    logging.info(u'%s Страница show %s' % (ip, number))
    logging.info(u'%s' % user_client)
    h = hashlib.md5(number)
    md5 = h.hexdigest()
    user_client_info = request.user_agent.string
    user_client = hashlib.md5(user_client)
    user_client = user_client.hexdigest()
    iscookie = request.cookies.get('user')
    if iscookie is not None:
        logging.info(u'%s есть такая печенька!' % iscookie)
        connection.execute(
        "INSERT INTO ufollow(md5, ip, user_client, list_number, user_client_info, cookie) VALUES ('%s','%s', '%s', '%s', '%s', '%s')" % (
            md5, ip, user_client, number, user_client_info, iscookie))
        return render_template('show_entries.html', mybooks=zip(mybooks, excel),
                                             excel=excel, form=form, litrescard=litrescard, int_lst=my_list_int)
    else:
        connection.execute(
        "INSERT INTO ufollow(md5, ip, user_client, list_number, user_client_info, cookie) VALUES ('%s','%s', '%s', '%s', '%s', '%s')" % (
            md5, ip, user_client, number, user_client_info, iscookie))
        resp = make_response(render_template('show_entries.html', mybooks=zip(mybooks, excel),
                                             excel=excel, form=form, litrescard=litrescard, int_lst=my_list_int))
        resp.set_cookie('user', value='%s %s' % (datetime.datetime.now(), ip), max_age=84000000)
        return resp


@app.route('/update/<number>', methods=['POST'])
def update_book(number):
    connection = engine.connect()
    connection.execute("SET character_set_connection=utf8")
    r = connection.execute("select author,title from parser_cards where (id='%s');" % number)  # забираем строчку
    (author, name) = r.fetchone()
    form = MyForm(request.form)  # объявляем формы из класса выше
    if request.method == 'POST':
        litresnum = '%0.6i' % int(number) + 'Ru-MoLR'
        connection.execute("START TRANSACTION;")
        connection.execute("DELETE FROM aleph3 WHERE id=%(id)s",
                           {'id': litresnum})
        for line in form.card_lines.data.split('\n'):
            line = re.sub(u'\t', u'   ', line, 0)  # копипейст с сайта ргб могут быть табуляции
            tag = line[:5]
            info = line[5:250]
            info_text = line[5:]
            tag = re.sub(u'\s+$', '', tag, 0)
            info = re.sub(u'^\s+', '', info, 0)
            info_text = re.sub(u'^\s+', '', info_text, 0)
            if tag == '':
                continue
            r = connection.execute(sql,
                                   {'id': litresnum, 'author': author, 'title': name, 'field': tag, 'info': info,
                                    'info_text': info_text})
        connection.execute("COMMIT;")
    ip = request.environ['REMOTE_ADDR']
    logging.info(u'%s update %s' % (ip, number))
    return redirect('/show/' + number)


@app.route('/copy/<number>', methods=['POST'])
def copy_book(number):
    litres_special = [u'003     RU-MoLR',
                      u'005     20160201125050.0',
                      u'007     cr^cn^c|||a|cba',
                      u'040     |b rus |c rumolr |e rcr',
                      u'044     |a ru',
                      u'538     |a Системные требования: Adobe Digital Editions',
                      u'000     00000nmm^a2200000^i^4500',
                      u'979     |a dluniv |a dlopen']
    connection = engine.connect()
    connection.execute("SET character_set_connection=utf8")
    r = connection.execute(
        "select author, title, isbn from parser_cards where (id='%s');" % number)  # забираем строчку задания
    (author, name, isbn1) = r.fetchone()
    form = MyForm(request.form)  # объявляем формы из класса выше
    if request.method == 'POST':
        litresnum = '%0.6i' % int(number) + 'Ru-MoLR'
        connection.execute("START TRANSACTION;")
        connection.execute("DELETE FROM aleph3 WHERE  id=%(id)s",
                           {'id': litresnum})
        lines = []
        # фильтруем
        for line in form.card_lines.data.split('\n'):
            line = re.sub(u'\t', u'   ', line, 0)  # копипейст с сайта ргб могут быть табуляции
            if line[:3] == '245':
                line1 = re.search(u'[\|]+h +\[*[Тт]+екст\]* +[\|:]', line)
                if line1 is not None:
                    line = re.sub(u'[\|]+h +\[*[Тт]+екст\]*', u'|h [Электронный ресурс]', line)
                else:
                    line2 = re.search(u'([$|]a [^$|]+)', line)
                    line_into = line2.group(0) + u' |h [Электронный ресурс] |'
                    # print line_into
                    line = re.sub(u'[$|]a [^$|]+', line_into, line)
            if t(line[:3]):
                lines.append(line)
        mime_str = u'application/pdf'
        litres_special.append(
            u'8561    |a rsl.ru |n Российская государственная библиотека, Москва, РФ |q %s' % mime_str)
        isbn = re.sub('\r\n', u'', isbn1, 0, re.M)
        isbn = re.sub('"', u'', isbn, 0, re.M)
        isbn = re.sub(u', ', ',', isbn, 0, re.M)
        isbn = re.sub(u'[()\.А-Яа-яЁёI ,:;+\[\]]+', u',', isbn, 0, re.M)
        isbn = re.sub(u'\.', u',', isbn, 0, re.M)
        isbn = re.sub(u',+$', u'', isbn, 0, re.M)
        isbn = re.sub(u',{2,}', u',', isbn, 0, re.M)
        isbn = re.sub(u'^\s+', u'', isbn, 0, re.M)
        isbn = re.sub(u'\s+$', u'', isbn, 0, re.M)
        if isbn1 != u'отсутствует':
            if ',' in isbn:
                isbn_lst = string.split(isbn, ',')
            else:
                isbn_lst = []
                isbn_lst.append(isbn)
            for i in isbn_lst:
                litres_special.append(u'020     |a %s' % i)
        else:
            pass
        right_author = overwrite_author(author)
        litres_special.append(u'1001   |a %s' % right_author[0])
        for right_author1 in right_author[1:]:
            litres_special.append(u'7001   |a %s' % right_author1)
        # добавляем спец. строчки
        lines.extend(litres_special)
        if int(number) > int(100000):
            number1 = number[2:]
        else:
            number1 = number
        lines.append(u'001     ' + '%0.6i' % int(number1))
        # а теперь засовываем
        for line in lines:
            tag = line[:5]
            info = line[5:255]
            info_text = line[5:]
            tag = re.sub(u'\s+$', '', tag, 0)
            if tag == '':
                continue
            info = re.sub(u'^\s+', '', info, 0)
            info_text = re.sub(u'^\s+', '', info_text, 0)
            r = connection.execute(sql,
                                   {'id': litresnum, 'author': author, 'title': name, 'field': tag, 'info': info,
                                    'info_text': info_text})
        connection.execute("COMMIT;")
    ip = request.environ['REMOTE_ADDR']
    logging.info(u'%s copy %s' % (ip, number))
    return redirect('/show/' + number)


@app.route('/create/<number>', methods=['POST'])
def create_book(number):
    litres_special = [u'003     RU-MoLR',
                      u'005     20160201125050.0',
                      u'007     cr^cn^c|||a|cba',
                      u'040     |b rus |c rumolr |e rcr',
                      u'044     |a ru',
                      u'0410    |a rus',
                      u'538     |a Системные требования: Adobe Digital Editions',
                      u'000     00000nmm^a2200000^i^4500',
                      u'979     |a dluniv |a dlopen']
    connection = engine.connect()
    connection.execute("SET character_set_connection=utf8")
    r = connection.execute(
        "select author, title, isbn from parser_cards where (id='%s');" % number)  # забираем строчку задания
    (author, name, isbn1) = r.fetchone()
    if request.method == 'POST':
        litresnum = '%0.6i' % int(number) + 'Ru-MoLR'
        connection.execute("START TRANSACTION;")
        connection.execute("DELETE FROM aleph3 WHERE  id=%(id)s",
                           {'id': litresnum})
        lines = []
        # фильтруем
        litres_special.append(u'24510  |a %s |h [Электронный ресурс]' % name)
        right_author = overwrite_author(author)
        litres_special.append(u'1001   |a %s' % right_author[0])
        for right_author1 in right_author[1:]:
            litres_special.append(u'7001   |a %s' % right_author1)
        isbn = re.sub('\r\n', u'', isbn1, 0, re.M)
        isbn = re.sub('"', u'', isbn, 0, re.M)
        isbn = re.sub(u', ', ',', isbn, 0, re.M)
        isbn = re.sub(u'[()\.А-Яа-яЁёI ,:;+\[\]]+', u',', isbn, 0, re.M)
        isbn = re.sub(u'\.', u',', isbn, 0, re.M)
        isbn = re.sub(u',+$', u'', isbn, 0, re.M)
        isbn = re.sub(u',{2,}', u',', isbn, 0, re.M)
        isbn = re.sub(u'^\s+', u'', isbn, 0, re.M)
        isbn = re.sub(u'\s+$', u'', isbn, 0, re.M)
        if isbn1 != u'отсутствует':
            if ',' in isbn:
                isbn_lst = string.split(isbn, ',')
            else:
                isbn_lst = []
                isbn_lst.append(isbn1)
            for i in isbn_lst:
                litres_special.append(u'020     |a %s' % i)
        else:
            pass
        mime_str = u'application/pdf'
        litres_special.append(
            u'8561    |a rsl.ru |n Российская государственная библиотека, Москва, РФ |q %s' % mime_str)
        # добавляем спец. строчки
        lines.extend(litres_special)
        if int(number) > int(100000):
            number1 = number[2:]
        else:
            number1 = number
        lines.append(u'001     ' + '%0.6i' % int(number1))
        # а теперь засовываем
        for line in lines:
            tag = line[:5]
            info = line[5:255]
            info_text = line[5:]
            tag = re.sub(u'\s+$', '', tag, 0)
            if tag == '':
                continue
            info = re.sub(u'^\s+', '', info, 0)
            info_text = re.sub(u'^\s+', '', info_text, 0)
            r = connection.execute(sql,
                                   {'id': litresnum, 'author': author, 'title': name, 'field': tag, 'info': info,
                                    'info_text': info_text})
        connection.execute("COMMIT;")
    ip = request.environ['REMOTE_ADDR']
    logging.info(u'%s create card %s' % (ip, number))
    return redirect('/show/' + number)


@app.route('/list/<number>', methods=['GET', 'POST'])
def excel(number):
    connection = engine.connect()
    connection.execute("SET character_set_connection=utf8")
    result = connection.execute('select id, author, title from parser_cards order by id limit %s00,100;' % number)
    excel = []
    for row in result.fetchall():
        excel.append(row)
    books = []
    ip_curr = request.environ['REMOTE_ADDR']
    user_client_curr = request.user_agent.string
    user_client_curr = hashlib.md5(user_client_curr)
    user_client_curr = user_client_curr.hexdigest()
    for element in excel:
        element0 = element[0]  # выделяем номер для поиска в базе excel2base
        iscookie = request.cookies.get('user')
        litresnum = '%0.6i' % int(element0) + 'Ru-MoLR'
        result2 = connection.execute("select * from aleph3 where (id='%s');" % litresnum)
        element = tuple(element)
        l = []
        result1 = connection.execute(
            "select ip, user_client, date, cookie from marc.ufollow where (list_number='%s') and date > DATE_SUB(NOW(),INTERVAL 15 MINUTE) order by date desc;" % element0)
        try:
            row = result1.fetchone()
            ip = row[0]
            user_client = row[1]
            date_time = row[2]
            cookie = row[3]
        except TypeError:
            ip = 0
            user_client = 0
            date_time = 0
            cookie = 0
        if user_client != 0 and ip != 0:
            if cookie == iscookie:
                now = datetime.datetime.now()
                date_time = str(date_time)
                date_time2 = datetime.datetime.strptime(date_time, '%Y-%m-%d %H:%M:%S')
                diff = now - date_time2
                diff = int(diff.total_seconds()) / 60
                if diff == 0:
                    diff = 1
                if diff <= 1:
                    check_follow = (u' Вы были тут %s минутy назад ✍' % diff,)
                elif diff <= 4:
                    check_follow = (u' Вы были тут %s минуты назад ✍' % diff,)
                elif diff <= 15 or diff == 0:
                    check_follow = (u' Вы были тут %s минут назад ✍' % diff,)
                else:
                    check_follow = (u' Вы были тут (~15 минут назад) ✍',)
            else:
                if user_client == user_client_curr and ip == ip_curr:
                    now = datetime.datetime.now()
                    date_time = str(date_time)
                    date_time2 = datetime.datetime.strptime(date_time, '%Y-%m-%d %H:%M:%S')
                    diff = now - date_time2
                    diff = int(diff.total_seconds()) / 60
                    if diff == 0:
                        diff = 1
                    if diff <= 1:
                        check_follow = (u' Вы были тут %s минутy назад ✍' % diff,)
                    elif diff <= 4:
                        check_follow = (u' Вы были тут %s минуты назад ✍' % diff,)
                    elif diff <= 15 or diff == 0:
                        check_follow = (u' Вы были тут %s минут назад ✍' % diff,)
                    else:
                        check_follow = (u' Вы были тут (~15 минут назад) ✍',)
                else:
                    now = datetime.datetime.now()
                    date_time = str(date_time)
                    date_time2 = datetime.datetime.strptime(date_time, '%Y-%m-%d %H:%M:%S')
                    diff = now - date_time2
                    diff = int(diff.total_seconds()) / 60
                    if diff == 0:
                        diff = 1
                    if diff <= 1:
                        check_follow = (u' На карточку кто-то зашел %s минутy назад ✍' % diff,)
                    elif diff <= 4:
                        check_follow = (u' На карточку кто-то зашел %s минуты назад ✍' % diff,)
                    elif diff <= 15 or diff == 0:
                        check_follow = (u' На карточку кто-то зашел %s минут назад ✍' % diff,)
                    else:
                        check_follow = (u' На карточку кто-то зашел (~15 минут назад) ✍',)
        else:
            check_follow = (u'',)
        if result2.fetchall() != l:
            check_lr = (u'✓✓✓',)
            check_rgb = (u'',)
        else:
            check_rgb = (u'Нет найденных карточек!',)
            check_lr = (u'',)
        books.append(element + check_lr + check_rgb + check_follow)
    # print books
    next_number = int(number) + 1
    if next_number > 56:
        next_number = 56
    prev_number = int(number) - 1
    if prev_number < 0:
        prev_number = 0
    logging.info(u'%s Загрузил страницу list номер %s' % (ip_curr, number))
    iscookie = request.cookies.get('user')
    if iscookie is not None:
        logging.info(u'%s есть такая печенька!' % iscookie)
        return render_template('show.html', excel=books, number1=next_number, number2=prev_number)
    else:
        resp = make_response(render_template('show.html', excel=books, number1=next_number, number2=prev_number))
        resp.set_cookie('user', value='%s %s' % (datetime.datetime.now(), ip_curr), max_age=84000000)
        return resp


import StringIO


@app.route('/getfile/<number>', methods=['GET', 'POST'])
def make_marc(number):
    global tag1, tag2
    if request.method == 'POST':
        ip = request.environ['REMOTE_ADDR']
        logging.info(u'%s get marc file of %s card' % (ip, number))
        connection = engine.connect()
        connection.execute("SET character_set_connection=utf8")
        r = pymarc.Record(to_unicode=True, force_utf8=True)
        litresnum = '%0.6i' % int(number) + 'Ru-MoLR'
        result = connection.execute(
            "SELECT field, info_text FROM marc.aleph3 WHERE (id='%s') ORDER BY FIELD " % litresnum)
        for (field, info_text) in result.fetchall():
            field = u'%-5s' % field
            info = re.sub(u'^\s+', u'', info_text)
            tag = field[:3]
            if len(tag) < 3:
                continue
            elif tag == '000':
                r.leader = re.sub(u'\s', u'', info)
            elif tag < '010' and tag.isdigit():
                r.add_field(pymarc.Field(tag=tag, data=re.sub(u'\s', u'', info)))
            else:
                line_pymarc_onebyone = string.split(info, '|')
                subfields = []
                for oneline in line_pymarc_onebyone:
                    if len(oneline) < 2:
                        continue
                    # print '** ',i nfo
                    # print '== ', len(oneline)
                    # print '>> ',oneline
                    tag1 = u'%s' % field[3]
                    tag2 = u'%s' % field[4]
                    subfields.append(oneline[0])
                    subfield_value = re.sub(u'\s*$', u'', re.sub(u'^\s*', u'', oneline[1:]))
                    subfields.append(subfield_value)
                r.add_field(pymarc.Field(tag=tag, indicators=[tag1, tag2], subfields=subfields))
        # This is the key: Set the right header for the response
        # to be downloaded, instead of just printed on the browser
        # resp = r.as_marc()
        resp = StringIO.StringIO()
        writer = pymarc.MARCWriter(resp)
        writer.write(r)
        # print len(resp.getvalue())
        # print resp.getvalue()
        response = make_response(resp.getvalue())
        writer.close(close_fh=False)
        with open('bbb.xml', 'wb') as f2:
            f2.write(pymarc.marcxml.record_to_xml(r))
            f2.close()
        name_number = '%0.5i' % int(number)
        response.headers["Content-Disposition"] = "attachment; filename=book%s.mrc" % name_number
        response.headers["Content-Type"] = "application/octet-stream"
        return response


@app.errorhandler(404)
def page_not_found(error):
    return 'This page does not exist', 404


if __name__ == '__main__':
    app.debug = True
    app.run('0.0.0.0')
