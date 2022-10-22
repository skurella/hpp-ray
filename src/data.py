from dataclasses import dataclass
from threading import Lock
from typing import List, Mapping


@dataclass
class CompileTarget:
    '''A (possibly local) build target with a single compile command.'''
    file: str
    target: str
    compile_deps: List[str]


class DependencyMap:
    '''
    For each dependency, stores the targets it comprises.
    Thread-safe.
    '''
    _map: Mapping[str, List[CompileTarget]] = {}
    _lock = Lock()

    def process(self, target: CompileTarget):
        with self._lock:
            for dep in target.compile_deps:
                if dep not in self._map:
                    self._map[dep] = []
                self._map[dep].append(target)

    def sorted_items(self):
        with self._lock:
            return sorted(self._map.items(), key=lambda item: -len(item[1]))
