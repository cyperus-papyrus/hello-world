# coding=utf-8
import re
import string

test_au = [u'Юлия Высоцкая', u'Гайворонский И.В.', u'С.И. Рябов', u'Баиндурашвили А.Г. Волошин С.Ю. Краснов А.И',
           u'Леонтьев О.В., Плавинский С.Л.', u'Виталий Вульф, Серафима Чеботарь', u'В. Н. Сингаевский',
           u'Толстой Л., Герцен А.', u'Воробьёв А.С., Зимина В.Ю.']


def overwrite_author(a):
    l = []
    a = string.strip(a)
    if ',' in a:
        a = re.sub(', ', ',', a)
        a = string.split(a, ',')
        for x in a:
            x = string.strip(x)
            if '.' in x:
                if re.match(u'[А-ЯЁ]\. [А-ЯЁ]\. ', x) is not None:
                    inish = x[0:2] + x[3:5]
                    lname = x[5:]
                elif re.match(u'[А-ЯЁ]\.[А-ЯЁ]\. ', x) is not None:
                    inish = x[0:4]
                    lname = x[5:]
                elif re.match(u'[А-ЯЁ][а-яё]+ [А-ЯЁ]\.$', x) is not None:
                    inish = x[-2:]
                    lname = x[:-2]
                else:
                    inish = x[-4:]
                    lname = x[:-4]
                inish = string.strip(inish)
                lname = string.strip(lname)
                new_a = lname + ', ' + inish
                l.append(new_a)
            else:
                x = string.strip(x)
                s = string.split(x, ' ')
                try:
                    x = s[1] + ', ' + s[0]
                except IndexError:
                    x = s[0]
                l.append(x)
    else:
        if '.' in a:
            if re.match(u'[А-ЯЁ]+\. [А-ЯЁ]\. ', a) is not None:
                inish = a[0:2] + a[3:5]
                lname = a[5:]
            elif re.match(u'[А-ЯЁ]+\.[А-ЯЁ]\.', a) is not None:
                inish = a[0:4]
                lname = a[5:]
            elif re.match(u'[А-ЯЁ][а-яё]+ [А-ЯЁ]\.$', a) is not None:
                inish = a[-2:]
                lname = a[:-2]
            else:
                inish = a[-4:]
                lname = a[:-4]
            inish = string.strip(inish)
            lname = string.strip(lname)
            new_a = lname + ', ' + inish
            l.append(new_a)
            # print lname + ', ' + inish
        else:
            try:
                a4 = string.split(a, ' ')
                a4 = a4[1] + ', ' + a4[0]
                l.append(a4)
            except IndexError:
                l.append(a)
    return l

# for a1 in test_au:
#     a2 = overwrite_author(a1)
#     for a3 in a2:
#        print a3