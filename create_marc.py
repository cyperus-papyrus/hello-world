# coding=utf-8
from sqlalchemy import create_engine
import pymarc
import string
import re
from sqlalchemy import text
import io


def replace_russian_letters(x):
    x = u'%s' % x
    return {u'а': u'a', u'с': u'c', u'е': u'e', u'о': u'o', u'р': u'p', u'х': u'x'}.get(x,x)


def process_field(tag, info, r):
    field_num = u'%-5s' % tag
    tag = u'%s' % field_num[0:3]
    ind1 = u'%s' % field_num[3]
    ind2 = u'%s' % field_num[4]
    if tag == u'000':
        r.leader = re.sub(u'\s', u'', info)
        # print r.leader
    elif tag < '010' and tag.isdigit():
        r.add_field(pymarc.Field(tag=tag, data=re.sub(u'\s', u'', info)))
    else:
        line_pymarc_onebyone = string.split(info, '|')
        subfields = []
        for oneline in line_pymarc_onebyone:
            if len(oneline) < 2:
                continue
            one0 = replace_russian_letters(oneline[0])
            subfields.append(one0)
            subfield_value = re.sub(u'\s*$', u'', re.sub(u'^\s*', u'', oneline[1:]))
            subfields.append(subfield_value)
        r.add_field(pymarc.Field(tag=tag, indicators=[ind1, ind2], subfields=subfields))


def field2string(f):
    if f.is_control_field():
        text = u'%s    %s' % (f.tag, f.data)
    else:
        text = u'%s' % (f.tag)
        for indicator in f.indicators:
            if indicator != '':
                text += '%s' % indicator
            else:
                text += u' '
        text += u'  ' + u' '.join([u'|%s %s' % subf for subf in f])
    return text


def record2text(r):
    return u'\n'.join([field2string(field) for field in sorted(r.fields, key=lambda y: y.tag)])


engine = create_engine('mysql://marc:123@localhost/marc?charset=utf8',
                       encoding='utf-8', convert_unicode=True, echo=True)  # подключение к БД
connection = engine.connect()
connection.execute("SET character_set_connection=utf8")
result = connection.execute(
    text("SELECT id, field, info_text FROM marc.aleph2 WHERE id LIKE '%Ru-MoLR' ORDER BY ID, FIELD"))
r = pymarc.Record(to_unicode=True, force_utf8=True)
writer = pymarc.MARCWriter(open('static/marc_cards.mrc', 'wb'))
text_writer = io.open('static/marc_cards.txt', 'w', encoding='utf-8')
prev_num = 0
(id, field, info) = result.fetchone()
current_num = id
process_field(field, info, r)

for (id, field, info) in result.fetchall():
    if id == current_num:
        process_field(field, info, r)
    else:
        current_num = id
        writer.write(r)
        text_writer.write(record2text(r)+u'\n\n\n')
        r = pymarc.Record(to_unicode=True, force_utf8=True)
        process_field(field, info, r)

else:
    writer.write(r)
    text_writer.write(record2text(r))
writer.close()
text_writer.close()