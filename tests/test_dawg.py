from __future__ import with_statement

from nose.tools import assert_equal, assert_not_equal, assert_raises  #@UnresolvedImport

import random
from array import array

from whoosh.compat import b, u
from whoosh.filedb.filestore import RamStorage
from whoosh.support import dawg
from whoosh.support.testing import TempStorage


def gwrite(keys, st=None):
    st = st or RamStorage()
    f = st.create_file("test")
    gw = dawg.GraphWriter(f)
    for key in keys:
        gw.insert(key)
    gw.close()
    return st


def greader(st):
    return dawg.GraphReader(st.open_file("test"))


def enlist(string):
    return [part.encode("utf8") for part in string.split()]

#

def test_empty_fieldname():
    gw = dawg.GraphWriter(RamStorage().create_file("test"))
    assert_raises(ValueError, gw.start_field, "")
    assert_raises(ValueError, gw.start_field, None)
    assert_raises(ValueError, gw.start_field, 0)

def test_empty_key():
    gw = dawg.GraphWriter(RamStorage().create_file("test"))
    assert_raises(KeyError, gw.insert, b(""))

def test_keys_out_of_order():
    f = RamStorage().create_file("test")
    gw = dawg.GraphWriter(f)
    gw.insert(b("alfa"))
    assert_raises(KeyError, gw.insert, b("abba"))

def test_duplicate_keys():
    st = gwrite(enlist("alfa bravo bravo bravo charlie"))
    gr = greader(st)
    assert_equal(list(gr.flatten()), ["alfa", "bravo", "charlie"])

def test_types():
    st = RamStorage()

    types = ((dawg.IntValues, 100, 0),
             (dawg.BytesValues, b('abc'), b('')),
             (dawg.ArrayValues, array("i", [0, 123, 42]), array("i")),
             (dawg.IntListValues, [0, 6, 97], []))

    for t, v, z in types:
        assert_equal(t.common(None, v), None)
        assert_equal(t.common(v, None), None)
        assert_equal(t.common(None, None), None)
        assert_equal(t.subtract(v, None), v)
        assert_equal(t.subtract(None, v), None)
        assert_equal(t.subtract(None, None), None)
        assert_equal(t.add(v, None), v)
        assert_equal(t.add(None, v), v)
        assert_equal(t.add(None, None), None)
        f = st.create_file("test")
        t.write(f, v)
        t.write(f, z)
        f.close()
        f = st.open_file("test")
        assert_equal(t.read(f), v)
        assert_equal(t.read(f), z)

    assert_equal(dawg.IntValues.common(100, 20), 20)
    assert_equal(dawg.IntValues.add(20, 80), 100)
    assert_equal(dawg.IntValues.subtract(100, 80), 20)

    assert_equal(dawg.BytesValues.common(b("abc"), b("abc")), b("abc"))
    assert_equal(dawg.BytesValues.common(b("abcde"), b("abfgh")), b("ab"))
    assert_equal(dawg.BytesValues.common(b("abcde"), b("ab")), b("ab"))
    assert_equal(dawg.BytesValues.common(b("ab"), b("abcde")), b("ab"))
    assert_equal(dawg.BytesValues.common(None, b("abcde")), None)
    assert_equal(dawg.BytesValues.common(b("ab"), None), None)

    a1 = array("i", [0, 12, 123, 42])
    a2 = array("i", [0, 12, 420])
    cm = array("i", [0, 12])
    assert_equal(dawg.ArrayValues.common(a1, a1), a1)
    assert_equal(dawg.ArrayValues.common(a1, a2), cm)
    assert_equal(dawg.ArrayValues.common(a2, a1), cm)
    assert_equal(dawg.ArrayValues.common(None, a1), None)
    assert_equal(dawg.ArrayValues.common(a2, None), None)

def _fst_roundtrip(domain, t):
    with TempStorage() as st:
        f = st.create_file("test")
        gw = dawg.GraphWriter(f, vtype=t)
        for key, value in domain:
            gw.insert(key, value)
        gw.close()

        f = st.open_file("test")
        gr = dawg.GraphReader(f, vtype=t)
        assert_equal(list(gr.flatten_v()), domain)

def test_fst_int():
    domain = [(b("aaab"), 0), (b("aabc"), 12), (b("abcc"), 23), (b("bcab"), 30),
              (b("bcbc"), 31), (b("caaa"), 70), (b("cbba"), 80), (b("ccca"), 101)]
    _fst_roundtrip(domain, dawg.IntValues)

def test_fst_bytes():
    domain = [(b("aaab"), b("000")), (b("aabc"), b("001")), (b("abcc"), b("010")),
              (b("bcab"), b("011")), (b("bcbc"), b("100")), (b("caaa"), b("101")),
              (b("cbba"), b("110")), (b("ccca"), b("111"))]
    _fst_roundtrip(domain, dawg.BytesValues)

def test_fst_array():
    domain = [(b("000"), array("i", [10, 231, 36, 40])),
              (b("001"), array("i", [1, 22, 12, 15])),
              (b("010"), array("i", [18, 16, 18, 20])),
              (b("011"), array("i", [52, 3, 4, 5])),
              (b("100"), array("i", [353, 4, 56, 62])),
              (b("101"), array("i", [3, 42, 5, 6])),
              (b("110"), array("i", [894, 9, 101, 11])),
              (b("111"), array("i", [1030, 200, 1000, 2000])),
              ]
    _fst_roundtrip(domain, dawg.ArrayValues)

def test_fst_intlist():
    domain = [(b("000"), [1, 2, 3, 4]),
              (b("001"), [1, 2, 12, 15]),
              (b("010"), [1, 16, 18, 20]),
              (b("011"), [2, 3, 4, 5]),
              (b("100"), [3, 4, 5, 6]),
              (b("101"), [3, 4, 5, 6]),
              (b("110"), [8, 9, 10, 11]),
              (b("111"), [100, 200, 1000, 2000]),
              ]
    _fst_roundtrip(domain, dawg.IntListValues)

def test_fst_nones():
    domain = [(b("000"), [1, 2, 3, 4]),
              (b("001"), None),
              (b("010"), [1, 16, 18, 20]),
              (b("011"), None),
              (b("100"), [3, 4, 5, 6]),
              (b("101"), None),
              (b("110"), [8, 9, 10, 11]),
              (b("111"), None),
              ]
    _fst_roundtrip(domain, dawg.IntListValues)

def test_fst_accept():
    domain = [(b("a"), [1, 2, 3, 4]),
              (b("aa"), [1, 2, 12, 15]),
              (b("aaa"), [1, 16, 18, 20]),
              (b("aaaa"), [2, 3, 4, 5]),
              (b("b"), [3, 4, 5, 6]),
              (b("bb"), [3, 4, 5, 6]),
              (b("bbb"), [8, 9, 10, 11]),
              (b("bbbb"), [100, 200, 1000, 2000]),
              ]
    _fst_roundtrip(domain, dawg.IntListValues)

#def test_fst_merge():
#    # 2; 3; 5; 7; 11; 13; 17; 19
#    ins = [(b("000"), 2), (b("000"), 2), (b("001"), 3), (b("010"), 5),
#           (b("010"), 5), (b("011"), 7), (b("100"), 11), (b("101"), 13),
#           (b("101"), 13), (b("110"), 17), (b("111"), 19), (b("111"), 19)]
#    outs = [(b("000"), 4), (b("001"), 3), (b("010"), 10), (b("011"), 7),
#            (b("100"), 11), (b("101"), 26), (b("110"), 17), (b("111"), 38)]
#
#    with TempStorage() as st:
#        f = st.create_file("test")
#        gw = dawg.GraphWriter(f, vtype=dawg.IntValues,
#                              merge=lambda v1, v2: v1 + v2)
#        for key, value in ins:
#            gw.insert(key, value)
#        gw.close()
#
#        f = st.open_file("test")

def test_words():
    words = enlist("alfa alpaca amtrak bellow fellow fiona zebulon")
    with TempStorage() as st:
        gwrite(words, st)

        gr = greader(st)
        assert_equal(list(gr.flatten()), words)

def test_random():
    def randstring():
        length = random.randint(1, 10)
        a = array("B", (random.randint(0, 255) for _ in xrange(length)))
        return a.tostring()
    keys = sorted(randstring() for _ in xrange(1000))

    with TempStorage() as st:
        gwrite(keys, st)
        gr = greader(st)
        s1 = gr.flatten()
        s2 = sorted(set(keys))
        for i, (k1, k2) in enumerate(zip(s1, s2)):
            assert k1 == k2, "%s: %r != %r" % (i, k1, k2)

        sample = list(keys)
        random.shuffle(keys)
        for key in sample:
            assert gr.follow(key) is not None

def test_shared_suffix():
    st = gwrite(enlist("blowing blue glowing"))

    gr = greader(st)
    arc1 = gr.follow(b("blo"))
    arc2 = gr.follow(b("glo"))
    assert_equal(arc1.target, arc2.target)

def test_fields():
    with TempStorage() as st:
        f = st.create_file("test")
        gw = dawg.GraphWriter(f)
        gw.start_field("f1")
        gw.insert(b("a"))
        gw.insert(b("aa"))
        gw.insert(b("ab"))
        gw.finish_field()
        gw.start_field("f2")
        gw.insert(b("ba"))
        gw.insert(b("baa"))
        gw.insert(b("bab"))
        gw.close()

        gr = dawg.GraphReader(st.open_file("test"))
        assert_equal(list(gr.flatten(gr.root("f1"))), ["a", "aa", "ab"])
        assert_equal(list(gr.flatten(gr.root("f2"))), ["ba", "baa", "bab"])

def test_within():
    with TempStorage() as st:
        gwrite(enlist("0 00 000 001 01 010 011 1 10 100 101 11 110 111"), st)
        gr = greader(st)
        s = set(gr.within("01", k=1))
    assert_equal(s, set(["0", "00", "01", "011", "010", "001", "10", "101", "1", "11"]))

def test_within_match():
    st = gwrite(enlist("abc def ghi"))
    gr = greader(st)
    assert_equal(set(gr.within("def")), set(["def"]))

def test_within_insert():
    st = gwrite(enlist("00 01 10 11"))
    gr = greader(st)
    s = set(gr.within("0"))
    assert_equal(s, set(["00", "01", "10"]))

def test_within_delete():
    st = gwrite(enlist("abc def ghi"))
    gr = greader(st)
    assert_equal(set(gr.within("df")), set(["def"]))

    st = gwrite(enlist("0"))
    gr = greader(st)
    assert_equal(list(gr.within("01")), ["0"])

def test_within_replace():
    st = gwrite(enlist("abc def ghi"))
    gr = greader(st)
    assert_equal(set(gr.within("dez")), set(["def"]))

    st = gwrite(enlist("00 01 10 11"))
    gr = greader(st)
    s = set(gr.within("00"))
    assert_equal(s, set(["00", "10", "01"]), s)

def test_within_transpose():
    st = gwrite(enlist("abc def ghi"))
    gr = greader(st)
    s = set(gr.within("dfe"))
    assert_equal(s, set(["def"]))

def test_within_k2():
    st = gwrite(enlist("abc bac cba"))
    gr = greader(st)
    s = set(gr.within("cb", k=2))
    assert_equal(s, set(["abc", "cba"]))

def test_within_prefix():
    st = gwrite(enlist("aabc aadc babc badc"))
    gr = greader(st)
    s = set(gr.within("aaxc", prefix=2))
    assert_equal(s, set(["aabc", "aadc"]))










