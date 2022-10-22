from itertools import count
import logging
import pygit2
from os.path import join
from tqdm import trange

from .data import ChangeMap


def gather_changes(dir: str, max_commits=None) -> ChangeMap:
    '''
    Walk the HEAD ref along the first parent line.
    Store how many times each file was changed.
    '''
    repo = pygit2.Repository(dir)
    head = repo.head
    assert head
    logging.info("Gathering changes %son %s",
                 f"from {max_commits} latest commits " if max_commits else "",
                 head.shorthand)
    commit = repo[head.target]
    assert isinstance(commit, pygit2.Commit), "HEAD does not point to a commit"

    statistics = ChangeMap()

    for _ in (trange(max_commits) if max_commits else count()):
        logging.debug(
            f"Processing {commit.short_id} {commit.message.splitlines()[0]}")
        if not commit.parents:
            logging.warn(f"Commit {commit.short_id} doesn't have any parents.")
            break

        parent = commit.parents[0]
        diff = parent.tree.diff_to_tree(commit.tree)
        for delta in diff.deltas:
            logging.debug(f"- {delta.new_file.path} was touched")
            fullpath = join(repo.workdir, delta.new_file.path)
            statistics.process(fullpath)

        commit = parent

    return statistics
