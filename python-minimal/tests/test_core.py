from word_count.core import count


def test_empty():
    s = count("")
    assert s.chars == 0
    assert s.words == 0
    assert s.lines == 0


def test_single_line_no_newline():
    s = count("hello world")
    assert s.chars == 11
    assert s.words == 2
    assert s.lines == 1


def test_multiline_trailing_newline():
    s = count("a b c\nd e\n")
    assert s.words == 5
    assert s.lines == 2


def test_multiline_no_trailing_newline():
    s = count("a\nb\nc")
    assert s.words == 3
    assert s.lines == 3
