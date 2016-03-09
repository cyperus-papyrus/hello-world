# -*- coding: utf-8 -*-
from flask import Flask, render_template, request, redirect
from sqlalchemy import create_engine, MetaData
from wtforms import Form
from wtforms import SubmitField, TextAreaField
from wtforms.validators import DataRequired
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Table
import re
from sqlalchemy import text
import string
from flask import make_response
import pymarc
import os, os.path
import time

app = Flask(__name__)
sql = u"""INSERT IGNORE INTO aleph2 (id, author, title, field, info, info_text)
        VALUES (%(id)s, %(author)s, %(title)s,%(field)s,%(info)s,%(info_text)s)
        """


class MyForm(Form):
    card_lines = TextAreaField(validators=[DataRequired()])  # форма для отрисовки строк в карточках в базе aleph2
    # litres = StringField(validators=[DataRequired()]) # форма для отрисовки новых, литресовских строк
    # hidden = HiddenField('Field 1', validators=[DataRequired()])
    submit = SubmitField('Submit', validators=[DataRequired()])
    copy = SubmitField('Copy card', validators=[DataRequired()])  # пока не работает


def t(n):
    if n not in ('SID', '000', '001', '003', '005', '008', '017', '035', '040', '018', '019', '044', '020',
                 '336', '337', '338', '538', '852', '912', '979', '856', '533', 'SYS', 'OWN', 'UID', 'FMT', 'CAT',
                 'LKR', '954', '955', '956', '010', '011', '012', '013', '014', '015', '100'):
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
aleph2 = Table('aleph2', metadata, autoload=True)


@app.route('/')
def index():
    t1 = os.path.getmtime('static/marc_cards.mrc') # дата последнего изменения файла
    t2 = os.path.getmtime('static/marc_cards.txt') # дата последнего изменения файла
    # напечатать дату в строковом формате:
    data_t1 = time.ctime(t1)
    data_t2 = time.ctime(t2)
    folder_size1 = os.path.getsize('static/marc_cards.mrc')
    folder_size2 = os.path.getsize('static/marc_cards.txt')
    return render_template('index.html', data1=data_t1, data2=data_t2, s1=folder_size1, s2=folder_size2)

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
        mystring.append(row1[4])  # ISBN
        mystring.append(row1[5])  # формат файла
        mystring.append(row1[6])  # название файла
        mystring.append(row1[7])  # размер файла
        excel.append(mystring)
    books = []  # в этом списке лежат id на все книги (001 и 003 поля)
    for element in excel:
        element = element[0]  # выделяем номер для поиска в базе excel2base
        result = connection.execute("SELECT * FROM marc.excel2base WHERE (number='%s');" % element)
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
            result = connection.execute("SELECT * FROM marc.aleph2 WHERE (id='%s') ORDER BY FIELD " % one_card)
            myone_card = []
            for row in result.fetchall():  # делаем словарь - одна строка из таблицы aleph2
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
        "SELECT id, author, title, field, info_text FROM marc.aleph2 WHERE (id='%s') ORDER BY FIELD " % litresnum)
    for (id, author, title, field, info_text) in result.fetchall():
        litrescard.append(dict(field='%-5s' % field, info=info_text))
    bibkomcard = []  # из карточек для каждой книги находим самую длинную и сохраняем ее
    bibkomtitle = excel[0][2]
    sql = "SELECT * FROM marc.aleph2  WHERE id LIKE :string and (title='%s') ORDER BY FIELD;" % bibkomtitle
    result_bibkom = connection.execute(text(sql),string="%BIBKOM")
    for row_bibkom in result_bibkom.fetchall():
        field_bib =row_bibkom[3]
        info_bib = row_bibkom[5]
        bibkomcard.append(dict(field='%-5s' % field_bib, info=info_bib))
    (result_count,) = connection.execute("select count(*) from excel e where e.number<=%s order by number" % number)
    my_list_int = (int(result_count[0]) - 1) / 100
    print int(result_count[0])
    print u'Загрузили страницу show %s' % number
    return render_template('show_entries.html', mybooks=zip(mybooks, excel),
                           excel=excel, form=form, litrescard=litrescard, bibkomcard=bibkomcard, int_lst=my_list_int)


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
            line = re.sub(u'\t',u'   ',line,0) # копипейст с сайта ргб могут быть табуляции
            tag = line[:5]
            info = line[5:250]
            info_text = line[5:]
            tag = re.sub(u'\s+$', '', tag, 0)
            info = re.sub(u'^\s+', '', info, 0)
            info_text = re.sub(u'^\s+', '', info_text, 0)
            if tag == '':
                continue
            r = connection.execute(sql,
                                   {'id': litresnum, 'author': author, 'title': name, 'field': tag, 'info': info, 'info_text': info_text})
        connection.execute("COMMIT;")
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
    r = connection.execute("select author, name, format, filename, isbn, pubhouse from excel where (number='%s');" % number)  # забираем строчку задания
    (author, name, frmt, filename, isbn1, pubhouse) = r.fetchone()
    form = MyForm(request.form)  # объявляем формы из класса выше
    if request.method == 'POST':
        litresnum = '%0.6i' % int(number) + 'Ru-MoLR'
        connection.execute("START TRANSACTION;")
        connection.execute("DELETE FROM aleph2 WHERE  id=%(id)s",
                           {'id': litresnum})
        lines = []
        # фильтруем
        for line in form.card_lines.data.split('\n'):
            line = re.sub(u'\t',u'   ',line,0) # копипейст с сайта ргб могут быть табуляции
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
        if frmt == 'epub':
           mime_str = u'application/epub+zip'
        litres_special.append(
                  u'8561    |a rsl.ru |f %s |n Российская государственная библиотека, Москва, РФ |q %s'%(filename,mime_str))
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
                litres_special.append(u'020     |a %s'%i)
        else:
            pass
        litres_special.append(u'1001   |a %s' % author)
        # добавляем спец. строчки
        lines.extend(litres_special)
        lines.append(u'001     ' + '%0.6i' % int(number))
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
                                   {'id': litresnum, 'author': author, 'title': name, 'field': tag, 'info': info, 'info_text': info_text})
        connection.execute("COMMIT;")
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
    r = connection.execute("select author, name, format, filename, isbn, pubhouse from excel where (number='%s');" % number)  # забираем строчку задания
    (author, name, frmt, filename, isbn1, pubhouse) = r.fetchone()
    if request.method == 'POST':
        litresnum = '%0.6i' % int(number) + 'Ru-MoLR'
        connection.execute("START TRANSACTION;")
        connection.execute("DELETE FROM aleph2 WHERE  id=%(id)s",
                           {'id': litresnum})
        lines = []
        # фильтруем
        litres_special.append(u'24510  |a %s |h [Электронный ресурс]' % name)
        litres_special.append(u'1001   |a %s' % author)
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
                litres_special.append(u'020     |a %s'%i)
        else:
            pass
        mime_str = u'application/pdf'
        if frmt == 'epub':
           mime_str = u'application/epub+zip'
        litres_special.append(
                  u'8561    |a rsl.ru |f %s |n Российская государственная библиотека, Москва, РФ |q %s'%(filename,mime_str))
        # добавляем спец. строчки
        lines.extend(litres_special)
        lines.append(u'001     ' + '%0.6i' % int(number))
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
                                   {'id': litresnum, 'author': author, 'title': name, 'field': tag, 'info': info, 'info_text': info_text})
        connection.execute("COMMIT;")
    return redirect('/show/' + number)


@app.route('/list/<number>', methods=['GET', 'POST'])
def excel(number):
    connection = engine.connect()
    connection.execute("SET character_set_connection=utf8")
    result = connection.execute('select number, author, name from excel order by number limit %s00,100;' % number)
    excel = []
    for row in result.fetchall():
        excel.append(row)
    books = []
    for element in excel:
        element0 = element[0]  # выделяем номер для поиска в базе excel2base
        result1 = connection.execute("SELECT * FROM marc.excel2base WHERE (number='%s');" % element0)
        litresnum = '%0.6i' % int(element0) + 'Ru-MoLR'
        result2 = connection.execute("select * from aleph2 where (id='%s');" % litresnum)
        element = tuple(element)
        l = []
        if result1.fetchall() != l:
            check_rgb = ('',)
        else:
            check_rgb = (u'Нет найденных карточек!',)
        if result2.fetchall() != l:
            check_lr = (u'Книга обработана!',)
        else:
            check_lr = ('',)
        books.append(element + check_lr + check_rgb)
    # print books
    next_number = int(number) + 1
    if next_number > 56:
        next_number = 56
    prev_number = int(number) - 1
    if prev_number < 0:
        prev_number = 0
    print u'Загрузили страницу list номер %s' % number
    return render_template('show.html', excel=books, number1=next_number, number2=prev_number)


import StringIO
@app.route('/getfile/<number>', methods=['GET', 'POST'])
def make_marc(number):
    if request.method == 'POST':
        connection = engine.connect()
        connection.execute("SET character_set_connection=utf8")
        r = pymarc.Record(to_unicode=True, force_utf8=True)
        litresnum = '%0.6i' % int(number) + 'Ru-MoLR'
        result = connection.execute(
        "SELECT field, info_text FROM marc.aleph2 WHERE (id='%s') ORDER BY FIELD " % litresnum)
        for (field, info_text) in result.fetchall():
            field = u'%-5s' % field
            info = re.sub(u'^\s+',u'',info_text)
            tag = field[:3]
            if len(tag)<3:
                continue
            elif tag == '000':
                r.leader = re.sub(u'\s',u'',info)
            elif tag < '010' and tag.isdigit():
                r.add_field(pymarc.Field(tag=tag, data=re.sub(u'\s',u'',info)))
            else :
                line_pymarc_onebyone = string.split(info,'|')
                subfields=[]
                for oneline in line_pymarc_onebyone:
                    if len(oneline)<2:
                        continue
                    # print '** ',i nfo
                    # print '== ', len(oneline)
                    # print '>> ',oneline
                    tag1=u'%s'%field[3]
                    tag2=u'%s'%field[4]
                    subfields.append(oneline[0])
                    subfield_value = re.sub(u'\s*$',u'', re.sub(u'^\s*',u'',oneline[1:]) )
                    subfields.append(subfield_value)
                r.add_field(pymarc.Field(tag=tag, indicators=[tag1,tag2], subfields=subfields))
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
        with open('bbb.xml','wb') as f2:
            f2.write(pymarc.marcxml.record_to_xml(r))
            f2.close()
        name_number = '%0.5i' % int(number)
        response.headers["Content-Disposition"] = "attachment; filename=book%s.mrc" % name_number
        response.headers["Content-Type"] = "application/octet-stream"
        # print r
        return response


if __name__ == '__main__':
    app.debug = True
    app.run('0.0.0.0')
