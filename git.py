from subprocess import check_output, CalledProcessError
import re
import os
import arrow


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
    def __init__(self, path):
        self._path = path

    @classmethod
    def clone(cls, remote, path, name):
        output = check_output('git clone {} {}'.format(remote, name), cwd=path, shell=True)
        return Repo(os.path.join(path, name))

    def _execute(self, command):
        try:
            # TODO some commands spew valid output to stderr for some reason, figure out how to handle it
            return check_output('git ' + command, cwd=self._path, shell=True)
        except CalledProcessError as e:
            # TODO some calls (like commit with no changes) fail, handle exceptions
            raise e

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
        return self._execute('commit -am "{}"'.format(message))

    def create_branch(self, name, revision=''):
        # TODO consider adding option to change to the newly created branch
        assert name not in self.branches
        return self._execute("branch {} {}".format(name, revision))

    def delete_branch(self, name):
        assert name in self.branches
        return self._execute("branch -d {}".format(name))

    def change_branch(self, name):
        assert name in self.branches
        return self._execute('checkout {}'.format(name))

    def merge(self, source, destination=None):
        destination = destination or self.current_branch
        print 'merging {} into {}'.format(source, destination)

    def push(self, remote='origin'):
        """Changed semantic - allow pushes between equaly named branches only,
push tags by default
"""
        return self._execute('push {1} {0}:{0} --tags'.format(self.current_branch, remote))
