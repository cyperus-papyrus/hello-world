# -*- coding: utf-8 -*-
from flask import Flask, render_template, request, redirect
from sqlalchemy import create_engine, MetaData
from wtforms import Form
from wtforms import StringField, HiddenField, SubmitField, TextAreaField
from wtforms.validators import DataRequired
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Table
import re

app = Flask(__name__)
sql = u"""INSERT IGNORE INTO aleph2 (id, author, title, field, info)
        VALUES (%(id)s, %(author)s, %(title)s,%(field)s,%(info)s)
        """

class MyForm(Form):
    card_lines = TextAreaField(validators=[DataRequired()]) # форма для отрисовки строк в карточках в базе aleph2
    #litres = StringField(validators=[DataRequired()]) # форма для отрисовки новых, литресовских строк
    #hidden = HiddenField('Field 1', validators=[DataRequired()])
    submit = SubmitField('Submit', validators=[DataRequired()])
    copy = SubmitField('Copy card', validators=[DataRequired()]) #пока не работает
    
def t(n):                                                                                                                                    
    if n not in ('SID','000','001','003','005','008','017','035','040', 
    '336','337','338','538','852','979','856','533','SYS','OWN','UID','FMT','CAT','LKR'):                                                        
        return True                                                                                                                              
    return False  


engine = create_engine('mysql://marc:123@localhost/marc?charset=utf8',
                       encoding='utf-8', convert_unicode=True, echo=True) #подключение к БД
Session = sessionmaker(bind=engine)
metadata = MetaData(bind=engine)
aleph2 = Table('aleph2', metadata, autoload=True)


@app.route('/')
def index():
    return 'Index Page'


@app.route('/hello')
def hello():
    return render_template('index.html')

@app.route('/show/<number>')
def show_book(number):
    connection = engine.connect()
    connection.execute("SET character_set_connection=utf8")
    result = connection.execute("select * from excel where (number='%s');" % number) # забираем строчку задания
    excel = []
    form=MyForm(request.form)
    for row1 in result.fetchall():
        mystring = [] # собираем эти строки в список
        mystring.append(row1[0]) #номер
        mystring.append(row1[1]) #автор
        mystring.append(row1[2]) #название книги
        mystring.append(row1[7]) #название книги
        excel.append(mystring)
        books = [] #в этом списке лежат id на все книги (001 и 003 поля)
    for element in excel:
        element = element[0] #выделяем номер для поиска в базе excel2base
        result = connection.execute("SELECT * FROM marc.excel2base WHERE (number='%s');" % element)
        ids = []
        for row in result.fetchall():
            idaleph = row[1] #из всех найденных строк выделяем idaleph и отправляем в список ids
            ids.append(idaleph)
        books.append(ids)
    books = filter(None, books) #чистим от пустых списков, которые появляются, если книга не была найдена
    mybooks = [] # тут лежат все карточки на все книги
    thelongestcard = [] # для каждой книги - самая длинная карточка
    n = 0
    for book in books:
        mymulti_cards = []
        for one_card in book:
            result = connection.execute("SELECT * FROM marc.aleph2 WHERE (id='%s') ORDER BY FIELD "% one_card)
            myone_card = []
            for row in result.fetchall(): #делаем словарь - одна строка из таблицы aleph2
                row = dict(id=row[0], author=row[1], title=row[2], field='%-5s'%row[3], info=row[4], num=n)
                myone_card.append(row) # словарь кладем в myone_card - это одна карточка на одну книгу
                n += 1
            mymulti_cards.append(myone_card) #теперь mymulti_cards - это список карточек для каждой книги
        mybooks.append(mymulti_cards) # теперь mybooks - это список из книг
                                      # в котором лежит список из карточек на книги
                                      # в котором лежат списки на каждую карточку
                                      # в которых словари-строчки каждой карточки
    litrescard = [] # из карточек для каждой книги находим самую длинную и сохраняем ее
    litresnum = '%0.6i'%int(number) + 'Ru-MoLR'
    result = connection.execute("SELECT id, author,title, field,info,info_text FROM marc.aleph2 WHERE (id='%s') ORDER BY FIELD "% litresnum)
    for (id, author,title, field,info,info_text) in result.fetchall():
        litrescard.append(dict(field='%-5s'%field,info=info))

    return render_template('show_entries.html', mybooks=zip(mybooks, litrescard, excel),
       excel=excel,form=form,litrescard=litrescard )

@app.route('/update/<number>',methods=['POST'])
def update_book(number):
    connection = engine.connect()
    connection.execute("SET character_set_connection=utf8")
    r = connection.execute("select author,name from excel where (number='%s');" % number) # забираем строчку задания
    (author,name) = r.fetchone();
    form = MyForm(request.form) # объявляем формы из класса выше
    if request.method == 'POST':
        litresnum = '%0.6i'%int(number) + 'Ru-MoLR'
        connection.execute("START TRANSACTION;")
        connection.execute("DELETE FROM aleph2 WHERE  id=%(id)s",
                        {'id':litresnum})
        for line in form.card_lines.data.split('\n'):
            tag=line[:5]
            info=line[5:]
            tag = re.sub(u'\s+$', '',tag,0)
            info = re.sub(u'^\s+','',info,0)
            if tag == '':
                continue
            r = connection.execute(sql,
              {'id':litresnum, 'author':author, 'title':name,'field':tag,'info':info})
        connection.execute("COMMIT;")
    return redirect('/show/'+number)

litres_special=[u'003     RU-MoLR',
                u'005     20160201125050.0',
                u'007     cr^cn^c|||a|cba',
                u'040     |brus|crumolr$ercr',
                u'044     |a ru',
                u'538     |a Системные требования: Adobe Digital Editions',
                u'000     00000nmm^a2200000^i^4500']

@app.route('/copy/<number>',methods=['POST'])
def copy_book(number):
    connection = engine.connect()
    connection.execute("SET character_set_connection=utf8")
    r = connection.execute("select author,name from excel where (number='%s');" % number) # забираем строчку задания
    (author,name) = r.fetchone();
    form = MyForm(request.form) # объявляем формы из класса выше
    if request.method == 'POST':
        litresnum = '%0.6i'%int(number) + 'Ru-MoLR'
        connection.execute("START TRANSACTION;")
        connection.execute("DELETE FROM aleph2 WHERE  id=%(id)s",
                        {'id':litresnum})
        lines = []
        # фильтруем
        for line in form.card_lines.data.split('\n'):
            if t(line[:3]):
                lines.append(line)
        # добавляем спец. строчки
        lines.extend(litres_special)
        lines.append(u'001     '+'%0.6i'%int(number))
        # а теперь засовываем
        for line in lines:
            tag=line[:5]
            info=line[5:]
            tag = re.sub(u'\s+$', '',tag,0)
            if tag == '':
                continue
            info = re.sub(u'^\s+','',info,0)
            r = connection.execute(sql,
          {'id':litresnum, 'author':author, 'title':name,'field':tag,'info':info})
        connection.execute("COMMIT;")
    return redirect('/show/'+number)

@app.route('/xxx_show/<number>', methods=['GET', 'POST'])
def mybooks(number):
    connection = engine.connect()
    connection.execute("SET character_set_connection=utf8")
    result = connection.execute('select * from excel order by number limit 1') #выбираем первые 10 строк из таблицы excel
    excel = []
    for row1 in result.fetchall():
        mystring = [] # собираем эти строки в список
        mystring.append(row1[0]) #номер
        mystring.append(row1[1]) #автор
        mystring.append(row1[2]) #название книги
        mystring.append(row1[7]) #название книги
        excel.append(mystring)

    books = [] #в этом списке лежат id на все книги (001 и 003 поля)
    for element in excel:
        element = element[0] #выделяем номер для поиска в базе excel2base
        result = connection.execute("SELECT * FROM marc.excel2base WHERE (number='%s');" % element)
        ids = []
        for row in result.fetchall():
            idaleph = row[1] #из всех найденных строк выделяем idaleph и отправляем в список ids
            ids.append(idaleph)
        books.append(ids)
    books = filter(None, books) #чистим от пустых списков, которые появляются, если книга не была найдена

    mybooks = [] # тут лежат все карточки на все книги
    thelongestcard = [] # для каждой книги - самая длинная карточка
    n = 0
    for book in books:
        mymulti_cards = []
        for one_card in book:
            result = connection.execute("SELECT * FROM marc.aleph2 WHERE (id='%s');" % one_card)
            myone_card = []
            for row in result.fetchall(): #делаем словарь - одна строка из таблицы aleph2
                row = dict(id=row[0], author=row[1], title=row[2], field=row[3], info=row[4], num=n)
                myone_card.append(row) # словарь кладем в myone_card - это одна карточка на одну книгу
                n += 1
            mymulti_cards.append(myone_card) #теперь mymulti_cards - это список карточек для каждой книги
        mybooks.append(mymulti_cards) # теперь mybooks - это список из книг
                                      # в котором лежит список из карточек на книги
                                      # в котором лежат списки на каждую карточку
                                      # в которых словари-строчки каждой карточки
        thelongestcardlst = [] # из карточек для каждой книги находим самую длинную и сохраняем ее
        for i in mymulti_cards:
            a = len(i)
            thelongestcardlst.append(a)
        el = max(thelongestcardlst)
        ind = thelongestcardlst.index(el)
        thelongestcardonelst = mymulti_cards[int(ind)]
        tlcl = []
        for h in thelongestcardonelst:
            lrcard = dict(id=h['id'], author=h['author'], title=h['title'], field=h['field'], info='', num=h['num'])
            tlcl.append(lrcard)
        for r in tlcl:
            hh = r['field']
            non = ['CAT', 'SYS', 'FMT', 'OWN'] #попытка удалить ненужные филды - не проходит, например из 4х CAT удаляет только два
            for no in non:
                if hh == no:
                    try:
                        tlcl.remove(r)
                    except:
                        print u'Бу!'
                        continue
        thelongestcard.append(tlcl)
    form = MyForm(request.form) # объявляем формы из класса выше
    if request.method == 'POST':
        num = form.hidden.data

        print 'num'
        print num, num['id']
        author = num['author']
        print author
        title = num['title']
        oldid = num['id']
        myid = oldid[:-7] + 'RuMoLR'
        field = num['field']
        num = num['num']
        print u'Вот они! ', myid, field, num
        connection.execute(aleph2.insert(), field=field, author=author, title=title, num=num, id=myid)

        '''send = []
        for book in mybooks:
            for card in book:
                for cardstr in card:
                    if int(cardstr['num']) == int(num):
                        send.append(cardstr)
                    else:
                        continue
        for i in send:
            field = i['field']
            author = i['author']
            title = i['title']
            num = i['num']
            myid = i['id']
        print send
        connection.execute(aleph2.update(), field=field, info=new_info, author=author, title=title, num=num, id=myid)
    # if request.method == 'POST' and request.form['form-name'] == 'Submit':
    if request.method == 'GET' and form.validate():
        form.litres.data = mybooks[1][1][1]'''
    return render_template('show_entries.html', mybooks=zip(mybooks, thelongestcard, excel), excel=excel, form=form)


if __name__ == '__main__':
    app.debug = True
    app.run('0.0.0.0')
