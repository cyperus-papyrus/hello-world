# -*- coding: utf-8 -*-
from flask import Flask, render_template, request, redirect
from sqlalchemy import create_engine, MetaData
from wtforms import Form
from wtforms import SubmitField, TextAreaField
from wtforms.validators import DataRequired
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Table
import re
from math import ceil

app = Flask(__name__)
sql = u"""INSERT IGNORE INTO aleph2 (id, author, title, field, info)
        VALUES (%(id)s, %(author)s, %(title)s,%(field)s,%(info)s)
        """


class MyForm(Form):
    card_lines = TextAreaField(validators=[DataRequired()])  # форма для отрисовки строк в карточках в базе aleph2
    # litres = StringField(validators=[DataRequired()]) # форма для отрисовки новых, литресовских строк
    # hidden = HiddenField('Field 1', validators=[DataRequired()])
    submit = SubmitField('Submit', validators=[DataRequired()])
    copy = SubmitField('Copy card', validators=[DataRequired()])  # пока не работает


class Pagination(object):

    def __init__(self, page, per_page, total_count):
        self.page = page
        self.per_page = per_page
        self.total_count = total_count

    @property
    def pages(self):
        return int(ceil(self.total_count / float(self.per_page)))

    @property
    def has_prev(self):
        return self.page > 1

    @property
    def has_next(self):
        return self.page < self.pages

    def iter_pages(self, left_edge=2, left_current=2,
                   right_current=5, right_edge=2):
        last = 0
        for num in xrange(1, self.pages + 1):
            if num <= left_edge or \
               (num > self.page - left_current - 1 and num < self.page + right_current) or \
               num > self.pages - right_edge:
                if last + 1 != num:
                    yield None
                yield num
                last = num


def t(n):
    if n not in ('SID', '000', '001', '003', '005', '008', '017', '035', '040',
                 '336', '337', '338', '538', '852', '912', '979', '856', '533', 'SYS', 'OWN', 'UID', 'FMT', 'CAT',
                 'LKR'):
        return True
    return False


def url_for_other_page(page):
    args = request.view_args.copy()
    args['page'] = page
    return url_for(request.endpoint, **args)
app.jinja_env.globals['url_for_other_page'] = url_for_other_page


engine = create_engine('mysql://marc:123@localhost/marc?charset=utf8',
                       encoding='utf-8', convert_unicode=True, echo=True)  # подключение к БД
Session = sessionmaker(bind=engine)
metadata = MetaData(bind=engine)
aleph2 = Table('aleph2', metadata, autoload=True)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/show/<number>')
def show_book(number):
    connection = engine.connect()
    connection.execute("SET character_set_connection=utf8")
    result = connection.execute("select * from excel where (number='%s');" % number)  # забираем строчку задания
    excel = []
    form = MyForm(request.form)
    for row1 in result.fetchall():
        mystring = []  # собираем эти строки в список
        mystring.append(row1[0])  # номер
        mystring.append(row1[1])  # автор
        mystring.append(row1[2])  # название книги
        mystring.append(row1[3])  # издательство
        mystring.append(row1[4])  # расширение
        mystring.append(row1[5])  # название файла
        mystring.append(row1[6])  # размер файла
        mystring.append(row1[7])  # isbn
        excel.append(mystring)
    books = []  # в этом списке лежат id на все книги (001 и 003 поля)
    for element in excel:
        element = element[0]  # выделяем номер для поиска в базе excel2base
        result = connection.execute("SELECT * FROM marc.excel2base WHERE (number='%s');" % element)
        ids = []
        for row in result.fetchall():
            idaleph = row[1]  # из всех найденных строк выделяем idaleph и отправляем в список ids
            ids.append(idaleph)
        books.append(ids)
    books = filter(None, books)  # чистим от пустых списков, которые появляются, если книга не была найдена
    mybooks = []  # тут лежат все карточки на все книги
    thelongestcard = []  # для каждой книги - самая длинная карточка
    n = 0
    for book in books:
        mymulti_cards = []
        for one_card in book:
            result = connection.execute("SELECT * FROM marc.aleph2 WHERE (id='%s') ORDER BY FIELD " % one_card)
            myone_card = []
            for row in result.fetchall():  # делаем словарь - одна строка из таблицы aleph2
                row = dict(id=row[0], author=row[1], title=row[2], field='%-5s' % row[3], info=row[4], num=n)
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
        "SELECT id, author,title, field,info,info_text FROM marc.aleph2 WHERE (id='%s') ORDER BY FIELD " % litresnum)
    for (id, author, title, field, info, info_text) in result.fetchall():
        litrescard.append(dict(field='%-5s' % field, info=info))
    # print litresnum,litrescard
    return render_template('show_entries.html', mybooks=zip(mybooks, excel),
                           excel=excel, form=form, litrescard=litrescard)


@app.route('/update/<number>', methods=['POST'])
def update_book(number):
    connection = engine.connect()
    connection.execute("SET character_set_connection=utf8")
    r = connection.execute("select author,name from excel where (number='%s');" % number)  # забираем строчку задания
    (author, name) = r.fetchone()
    form = MyForm(request.form)  # объявляем формы из класса выше
    if request.method == 'POST':
        litresnum = '%0.6i' % int(number) + 'Ru-MoLR'
        connection.execute("START TRANSACTION;")
        connection.execute("DELETE FROM aleph2 WHERE  id=%(id)s",
                           {'id': litresnum})
        for line in form.card_lines.data.split('\n'):
            tag = line[:5]
            info = line[5:]
            tag = re.sub(u'\s+$', '', tag, 0)
            info = re.sub(u'^\s+', '', info, 0)
            if tag == '':
                continue
            r = connection.execute(sql,
                                   {'id': litresnum, 'author': author, 'title': name, 'field': tag, 'info': info})
        connection.execute("COMMIT;")
    return redirect('/show/' + number)


litres_special = [u'003     RU-MoLR',
                  u'005     20160201125050.0',
                  u'007     cr^cn^c|||a|cba',
                  u'040     |b rus |c rumolr |e rcr',
                  u'044     |a ru',
                  u'538     |a Системные требования: Adobe Digital Editions',
                  u'000     00000nmm^a2200000^i^4500',
                  u'979^^   |a dluniv |a dlopen']


@app.route('/copy/<number>', methods=['POST'])
def copy_book(number):
    connection = engine.connect()
    connection.execute("SET character_set_connection=utf8")
    r = connection.execute("select author, name, format, filename from excel where (number='%s');" % number)  # забираем строчку задания
    (author, name, frmt, filename) = r.fetchone()
    form = MyForm(request.form)  # объявляем формы из класса выше
    if request.method == 'POST':
        litresnum = '%0.6i' % int(number) + 'Ru-MoLR'
        connection.execute("START TRANSACTION;")
        connection.execute("DELETE FROM aleph2 WHERE  id=%(id)s",
                           {'id': litresnum})
        lines = []
        # фильтруем
        for line in form.card_lines.data.split('\n'):
            if line[:3] == '245':
                line = re.sub(u'\|h \[[Тт]екст\] :', u'|h [Электронный ресурс] :', line)
            if t(line[:3]):
                lines.append(line)
        mime_str = u'application/pdf'
        if frmt == 'epub':
           mime_str = u'application/epub+zip'
        litres_special.append(
                  u'8561^   |a rsl.ru |f %s |n Российская государственная библиотека, Москва, РФ |q %s'%(filename,mime_str))
        # добавляем спец. строчки
        lines.extend(litres_special)
        lines.append(u'001     ' + '%0.6i' % int(number))
        # а теперь засовываем
        for line in lines:
            tag = line[:5]
            info = line[5:]
            tag = re.sub(u'\s+$', '', tag, 0)
            if tag == '':
                continue
            info = re.sub(u'^\s+', '', info, 0)
            r = connection.execute(sql,
                                   {'id': litresnum, 'author': author, 'title': name, 'field': tag, 'info': info})
        connection.execute("COMMIT;")
    return redirect('/show/' + number)


PER_PAGE = 20

@app.route('/show/', defaults={'page': 1}, methods=['GET', 'POST'])
@app.route('/show/page/<int:page>')
def excel(page):
    connection = engine.connect()
    connection.execute("SET character_set_connection=utf8")
    result = connection.execute('select number, author, name from excel order by number limit 100')
    excel = []
    for row in result.fetchall():
        excel.append(row)
    books = []  # в этом списке лежат id на все книги (001 и 003 поля)
    for element in excel:
        element0 = element[0]  # выделяем номер для поиска в базе excel2base
        result = connection.execute("SELECT * FROM marc.excel2base WHERE (number='%s');" % element0)
        l = []
        if result.fetchall() != l:
            books.append(element)
        else:
            continue
    count = len(books)
    # users = get_users_for_page(page, PER_PAGE, count)
    pagination = Pagination(page, PER_PAGE, count)
    return render_template('show.html', pagination=pagination, excel=books)

if __name__ == '__main__':
    app.debug = True
    app.run('0.0.0.0')
