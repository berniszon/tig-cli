from subprocess import check_output, CalledProcessError
from contextlib import contextmanager
import re
import os
import arrow
import json


# TODO git probably has some switch to output easily parsable data, remove the re
CURRENT_BRANCH_PATTERN = r'\*\s+(.*)'
BRANCH_PATTERN = r'\*?\s+(.*)'
LOG_PATTERN = r'commit ([a-fA-F0-9]{40})\n' + 'Author: (.+)\s+<(.+)>\n' + 'Date:   (.*)\n' + '\n((    .*\n)+)'

current_branch_matcher = re.compile(CURRENT_BRANCH_PATTERN)
branch_matcher = re.compile(BRANCH_PATTERN)
log_matcher = re.compile(LOG_PATTERN)


class Repo(object):
    """Git CLI sucks, most methods here don't follow it's default semantics.
"""
    def __init__(self, path, author):
        self._path = path
        self._author = author

    @classmethod
    def clone(cls, remote, path, name, author):
        output = check_output('git clone {} {}'.format(remote, name), cwd=path, shell=True)
        return Repo(os.path.join(path, name), author)

    def _execute(self, command):
        try:
            # TODO some commands spew valid output to stderr for some reason, figure out how to handle it
            return check_output('git ' + command, cwd=self._path, shell=True)
        except CalledProcessError as e:
            # TODO some calls (like commit with no changes) fail, handle exceptions
            # raise e
            pass

    @property
    def changes(self):
        # TODO maybe some parsing into friendlier format
        return self._execute('status --porcelain').split('\n')[:-1]

    @property
    def current_branch(self):
        for line in self._execute('branch').split('\n')[:-1]:
            m = current_branch_matcher.match(line)
            if m:
                return m.group(1)
        return None

    @property
    def branches(self):
        return sorted([branch_matcher.match(l).group(1) for l in self._execute('branch').split('\n')[:-1]])

    # TODO filters
    @property
    def log(self):
        return [
            {
                'hash': l[0],
                'author': l[1],
                'email': l[2],
                'date': arrow.get(l[3]).isoformat(),
                'message': '\n'.join([line[4:] for line in l[4].split('\n')[:-1]]),
            }
            for l in log_matcher.findall(self._execute('--no-pager log --date=iso-strict'))
        ]

    # TODO Parse tags correctly
    def _parse_tags(self, tags):
        tag_pattern = r'tag: (.+?),'
        output = []
        for m in re.findall(tag_pattern, tags):
            output.append(m)
        return output

    @property
    def log2(self):
        pretty_format = '\'{%n  "hash": "%H",%n  "author": "%an <%ae>",%n  "date": "%ad",%n  "message": "%f",%n  "tags": "%d"%n},\''
        logs_json_string = '[' + self._execute('--no-pager log --date=iso-strict --pretty=format:{}'.format(pretty_format))[:-1] + ']'
        logs = json.loads(logs_json_string)
        output = []
        for l in logs:
            l['tags'] = self._parse_tags(l['tags'])
            output.append(l)
        return output

    # TODO tig doesn't care for index, so no argument diff is useless
    # feel free to implement defaults
    # def diff(self, base=None, to=None):
    def diff(self, base, to):
        return self._execute('diff {} {}'.format(base, to))

    def init(self):
        return self._execute('init')

    def add(self, file_names=['.']):
        """Changed semantic - add all by default
"""
        return self._execute('add ' + ' '.join(file_names))

    def commit(self, message):
        """Changed semantic - commit changes to tracked files by default
"""
        return self._execute('commit --author="{}" -am "{}"'.format(self._author, message))

    def create_branch(self, name, revision=''):
        # TODO consider adding option to change to the newly created branch
        assert name not in self.branches
        return self._execute("branch {} {}".format(name, revision))

    def delete_branch(self, name, force=False):
        assert name in self.branches
        return self._execute("branch {} {}".format('-D' if force else '-d', name))

    def change_branch(self, name):
        assert name in self.branches
        return self._execute('checkout {}'.format(name))

    def update(self, source, destination=None):
        """Alternative name for a fast-forward only merge
"""
        output = self.merge(source, destination, ff_only=True)
        assert output
        return output

    def merge(self, source, destination=None, resolve=False, ff_only=False):
        destination = destination or self.current_branch
        with self._switch_branch(destination):
            print 'merging {} into {}'.format(source, destination)
            self._execute('merge{} {}'.format(' --ff-only' if ff_only else '', source))
            merge_worked = not self.changes

            if not merge_worked and not resolve:
                self._execute('merge --abort')

        return merge_worked

    def push(self, branch=None, remote='origin', flags=''):
        """Changed semantic - allow pushes between equaly named branches only,
push tags by default
"""
        branch = branch or self.current_branch
        return self._execute('push {1} {0}:{0} --tags {2}'.format(branch, remote, flags))

    def pull(self, branch=None, remote='origin'):
        branch = branch or self.current_branch
        with self._switch_branch(branch):
            return self._execute('pull {1} {0} --tags'.format(branch, remote))

    @contextmanager
    def _switch_branch(self, name):
        assert not self.changes
        return_branch = self.current_branch
        self.change_branch(name)
        yield
        self.change_branch(return_branch)
