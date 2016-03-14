# coding=utf-8
from sqlalchemy import create_engine
import pymarc
import string
import re
from sqlalchemy import text
import io
import os
import StringIO
from datetime import datetime


def replace_russian_letters(x):
    x = u'%s' % x
    return {u'а': u'a', u'с': u'c', u'е': u'e', u'о': u'o', u'р': u'p', u'х': u'x'}.get(x, x)


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

def do_create_marc():
    engine = create_engine('mysql://marc:123@localhost/marc?charset=utf8',
                           encoding='utf-8', convert_unicode=True, echo=True)  # подключение к БД
    connection = engine.connect()
    connection.execute("SET character_set_connection=utf8")
    result = connection.execute(
        text("SELECT id, field, info_text FROM marc.aleph2 WHERE id LIKE '%Ru-MoLR' ORDER BY ID, FIELD"))
    r = pymarc.Record(to_unicode=True, force_utf8=True)
    mypath = os.path.dirname(os.path.abspath(__file__))
    time_now = datetime.strftime(datetime.now(), "%H-%M-%S-%f")
    writer = pymarc.MARCWriter(open('%s/static/marc_cards_%s.mrc' % (mypath, time_now), 'wb'))
    text_writer = io.open('%s/static/marc_cards_%s.txt' % (mypath, time_now), 'w', encoding='utf-8')
    test = io.open('%s/static/bad_marc_cards_%s.txt' % (mypath, time_now), 'w', encoding='utf-8')
    (id, field, info) = result.fetchone()
    current_num = id
    process_field(field, info, r)
    count = 0
    counter = 0

    for (id, field, info) in result.fetchall():
        if id == current_num:
            process_field(field, info, r)
        else:
            current_num = id
            test_string = StringIO.StringIO()
            testwriter = pymarc.MARCWriter(test_string)
            testwriter.write(r)
            test1 = pymarc.MARCReader(test_string.getvalue(), to_unicode=True, force_utf8=True)
            try:
                for x in test1:
                    count += 1
            except UnicodeDecodeError:
                counter += 1
                test.write(record2text(r) + u'\n\n\n')
            testwriter.close()
            writer.write(r)
            text_writer.write(record2text(r) + u'\n\n\n')
            r = pymarc.Record(to_unicode=True, force_utf8=True)
            process_field(field, info, r)

    else:
        writer.write(r)
        count += 1
        text_writer.write(record2text(r))
    writer.close()
    text_writer.close()
    test.close()
    os.rename('%s/static/marc_cards_%s.mrc' % (mypath, time_now), '%s/static/marc_cards.mrc' % mypath)
    os.rename('%s/static/marc_cards_%s.txt' % (mypath, time_now), '%s/static/marc_cards.txt' % mypath)
    os.rename('%s/static/bad_marc_cards_%s.txt' % (mypath, time_now), '%s/static/bad_marc_cards.txt' % mypath)
    print count
    print "Bad records counter:", counter
    total = int(count) + int(counter)
    num_file = open('%s/num_file.txt'%mypath, 'w')
    num_file.write(str(total) + u'\n' + str(count) + u'\n' + str(counter))
    num_file.close()
    
if __name__ == "__main__":
    do_create_marc()
    
