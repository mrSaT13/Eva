from threading import Lock
from typing import Collection, TypeVar, Callable

from eva.brain.abc import OutputChannelPool, OutputChannel, OutputChannelNotFoundError

TChan = TypeVar('TChan', bound=OutputChannel)


class OutputPoolImpl(OutputChannelPool, list[OutputChannel]):
    def __init__(self, channels: Collection[OutputChannel]):
        super().__init__(channels)

    def query_channels(self, predicate: Callable[[OutputChannel], bool]) -> Collection[OutputChannel]:
        lst = list(filter(predicate, self))

        if len(lst) == 0:
            raise OutputChannelNotFoundError()

        return lst  # type: ignore


EMPTY_OUTPUT_POOL = OutputPoolImpl(())


class CompositeOutputPool(OutputChannelPool, list[OutputChannelPool]):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._lock = Lock()

    def insert(self, *args, **kwargs):
        with self._lock:
            return super().insert(*args, **kwargs)

    def remove(self, *args, **kwargs):
        with self._lock:
            return super().remove(*args, **kwargs)

    def query_channels(self, predicate: Callable[[OutputChannel], bool]) -> Collection[OutputChannel]:
        result: list[OutputChannel] = []

        with self._lock:
            pools = list(self)

        for pool in pools:
            try:
                result.extend(pool.query_channels(predicate))
            except OutputChannelNotFoundError:
                ...

        if len(result) == 0:
            raise OutputChannelNotFoundError()

        return result
