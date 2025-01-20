"""
Priority Queue.
"""

__author__ = 'mikemeko'
__date__ = 'August 8, 2013'

from heapq import heapify
from heapq import heappop
from heapq import heappush


class PriorityQueue:
    """
    A Priority Queue data structure that supports push, pop, contains, and remove.
    """

    def __init__(self, data=None):
        """
        |data| is the starting data, a list of (cost, item) tuples, where the items
            are distinct.
        """
        if data is None:
            data = []
        self._items = set()
        for cost, item in data:
            if item in self._items:
                raise Exception(
                    'Item "%s" is duplicated in initial data' % item)
            self._items.add(item)
        self._data = data
        self._heapify()

    def _heapify(self):
        """
        Restructures the list of items for efficient push and pop.
        """
        heapify(self._data)

    def push(self, item, cost):
        """
        Pushes the given |item| with the given |cost| to the list of items. The
            |item| should not already be in the list of items.
        """
        assert item not in self._items
        self._items.add(item)
        heappush(self._data, (cost, item))

    def pop(self):
        """
        Pops and returns the item with the minimum cost. Returns None if there are
            no items.
        """
        if not self._data:
            return None
        cost, item = heappop(self._data)
        self._items.remove(item)
        return item

    def contains(self, item):
        """
        Returns True if |item| is in the list of items, False otherwise.
        """
        return item in self._items

    def remove(self, item, cost=None):
        """
        Removes the given |item| from the list of items. |item| must currently be in
            the list of items. |cost| gives the current cost of the |item|, if known
            by the caller.
        """
        assert item in self._items, 'Item "%s" is not in list of items.' % item
        if cost is None:
            for c, i in self._data:
                if item == i:
                    cost = c
                    break
        else:
            assert (cost, item) in self._data, 'Incorrect cost for item "%s"' % item
        self._data.remove((cost, item))
        self._items.remove(item)
        self._heapify()

    def __len__(self):
        return len(self._data)
