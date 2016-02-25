# -*- coding: utf-8 -*-
from flask import Flask, render_template, request
from sqlalchemy import create_engine, MetaData
from wtforms import Form
from wtforms import StringField
from wtforms.validators import DataRequired
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Table

app = Flask(__name__)


class MyForm(Form):
    name = StringField(validators=[DataRequired()])


engine = create_engine('mysql://marc:123@localhost/marc?charset=utf8',
                       encoding='utf-8', convert_unicode=True, echo=True)
Session = sessionmaker(bind=engine)
metadata = MetaData(bind=engine)
aleph2 = Table('aleph2', metadata, autoload=True)


@app.route('/')
def index():
    return 'Index Page'


@app.route('/hello')
def hello():
    return render_template('index.html')


@app.route('/show', methods=['GET', 'POST'])
def show_entries():
    connection = engine.connect()
    connection.execute("SET character_set_connection=utf8")
    result = connection.execute('select * from aleph2 order by id desc limit 1000')
    m_id = 0
    a = []
    entries = []
    n = 0
    for row in result.fetchall():
        n_id = row[0]
        if n_id == m_id:
            row = dict(id=row[0], author=row[1], title=row[2], field=row[3], info=row[4], num=n)
            a.append(row)
            n += 1
        else:
            entries.append(a)
            a = []
            row = dict(id=row[0], author=row[1], title=row[2], field=row[3], info=row[4], num=n)
            a.append(row)
            m_id = n_id
            n += 1
    entries.append(a)
    print entries
    form = MyForm(request.form)
    if request.method == 'POST' and form.validate():
        new_info = form.name.data
        num = form.name.object_data
        print num
        for entry in entries:
            for x in entry:
                if x['num'] == num:
                    f_card = x
                else:
                    continue
        connection.execute(aleph2.insert(), info=new_info)
    return render_template('show_entries.html', entries=entries, form=form)

if __name__ == '__main__':
    app.run()
