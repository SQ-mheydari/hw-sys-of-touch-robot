from collections import deque
from typing import TypeVar, Iterator, Generator, List


T = TypeVar('T')


def window(seq: Iterator[T], window_size) -> Generator[List[T], None, None]:
    """
    Iterate with a window having subsequent items of original iterator.

    :param seq: Inner iterator
    :param window_size: The number of items in window
    :return: Generator that yields lists of items
    """
    it = iter(seq)
    win = deque((next(it, None) for _ in range(window_size)), maxlen=window_size)
    yield win
    for e in it:
        win.append(e)
        yield win
