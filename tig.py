#!/Users/grzegorz/Projects/Tig/venv/bin/python
import sys
import os
import subprocess
import time
from contextlib import contextmanager
import json
import re

from git import Repo


# TODO config
REMOTE = '/Users/grzegorz/Projects/Tig/remotes'
TEAM = 'sigmapoint'
NAME = 'sikor'

# initialize directories
try:
    os.makedirs(os.path.join(REMOTE, TEAM))
except OSError as e:
    # hack dont fail when directories already exist
    pass


class FileSystemMockAPI(object):
    # Talks to local file system instead of a real remote
    def __init__(self, remote, team, name):
        self._remote = remote
        self._team = team
        self._name = name

    @property
    def projects(self):
        # hack cut off .git
        return [n[:-4] for n in os.listdir(self.projects_url)]

    @property
    def projects_url(self):
        return os.path.join(self._remote, self._team)

    def project_url(self, project_name):
        return os.path.join(self.projects_url, project_name + '.git')

    def create_project(self, project_name):
        path = os.path.join(self._remote, self._team, project_name + '.git')
        os.makedirs(path)
        subprocess.call(['git', 'init', '--bare'], cwd=path)
        subprocess.call(['git', 'branch', 'tig-master'], cwd=path)


api = FileSystemMockAPI(REMOTE, TEAM, NAME)


def get_sync_branch(branch):
    if branch.startswith('tig-') and branch.endswith('-' + NAME):
        return branch[:-len('-' + NAME)]


@contextmanager
def temporary_branch(repo, start=None):
    start = start or repo.current_branch
    name = 'tig-temporary-'
    repo.create_branch(name, start)
    yield name
    repo.delete_branch(name)


def sync_repo(resolve=False):
    repo = Repo(os.getcwd())

    sync_branch = get_sync_branch(repo.current_branch)
    if sync_branch:
        save()
        repo.pull(sync_branch)
        with temporary_branch(repo, sync_branch) as temp_branch:
            if repo.merge(repo.current_branch, temp_branch, resolve=resolve):
                repo.update(temp_branch)  # pull onto working branch
                repo.push()               # update remote
                repo.update(repo.current_branch, sync_branch)  # update local sync branch
                repo.push(sync_branch)                         # update remote
            else:
                if resolve:
                    # TODO
                    print 'resolve conflicts'
                else:
                    # TODO
                    print 'abort everything'
    else:
        print 'Unable to sync - you are not on a synching branch'


def _diff_to_file_dict(diff):
    chunks = diff.split('diff --git ')[1:]

    pattern = r'^a\/([^\s]+) b\/(.|\n)*(@@ (.|\n)*)$'
    matches = [re.match(pattern, c) for c in chunks]
    files_list = [(m.group(1), m.group(3)) for m in matches if m]
    files = {}
    for name, content in files_list:
        files[name] = content

    return files


def parse_diff(diff):
    tasks_list = []

    files = _diff_to_file_dict(diff)
    todo_pattern = r'\+.*((#)|(\/\/)) TODO ?(.*)'

    for name, content in files.items():
        found = re.findall(todo_pattern, content)
        for m in found:
            tasks_list.append({
                'name': m[3].strip() or 'No name',
                'file': name,
                'line': 0,  # TODO
                'description': ''  # TODO
            })

    return tasks_list


def order_tasks(tasks):
    for t, i in zip(tasks, range(len(tasks))):
        t['order'] = i


def project_exists(name):
    return name in api.projects


def init_project(project_name):
    if os.path.exists(project_name):
        print 'File already exists: {}'.format(project_name)
        exit(1)

    if not project_exists(project_name):
        api.create_project(project_name)
        repo = Repo.clone(api.project_url(project_name), '.', project_name)


        # TODO this is a silly way to create an initial config, with file contents in a silly spot among the code
        with open(os.path.join(project_name, 'README.md'), 'w') as f:
            default_readme = '''# TODO
'''
            f.write(default_readme)

        with open(os.path.join(project_name, '.gitignore'), 'w') as f:
            default_gitignore = '''# Don't spill your environment - exclude IDE and OS files in your private .gitignore
'''
            f.write(default_gitignore)

        with open(os.path.join(project_name, '.editorconfig'), 'w') as f:
            default_editorconfig = '''root = true

# basic configuration
[*]
end_of_line = lf
insert_final_newline = true
charset = utf-8
trim-trailing-whitespace = true
indent-style = space
indent-size = 2

# You can add your extension-specific rules here!
# [*.js]
# [*.py]
# [*.md]
'''
            f.write(default_editorconfig)

        repo.add()
        repo.commit("Initial commit")
        # TODO consider wrapping next three in tag - push first is important to not break tagging
        repo.push()
        repo._execute('tag 0.0.0')
        repo.push()  # just the tag

    else:
        repo = Repo.clone(api.project_url(project_name), '.', project_name)

    common_sync_branch_name = 'tig-master'
    personal_sync_branch_name = common_sync_branch_name + '-{}'.format(NAME)

    repo.create_branch(common_sync_branch_name)
    repo.pull(common_sync_branch_name)
    repo.create_branch(personal_sync_branch_name, common_sync_branch_name)
    repo.change_branch(personal_sync_branch_name)


# TODO each of these usage functions should just be part of an instruction
def init_usage():
    return '''Usage:
  tig init :project-name'''


def tig_usage():
    # this is a function and not just a flat value to remind me to add some dynamic data to it
    return '''tig 0.0.0

    init :project-name
    Join or create a new project'''


def init(arguments=[]):
    if len(arguments) > 0:
        project_name = arguments[0]
        init_project(project_name)
    else:
        print init_usage()


def save(arguments=[]):
    if len(arguments) > 0:
        # TODO handle arguments
        pass  # for now just dismiss them
    repo = Repo(os.getcwd())
    if repo.changes:  # apparently empty list is falsy
        repo.add()
        repo.commit('Automated commit')

        sync_branch = get_sync_branch(repo.current_branch)
        if sync_branch:
            repo.push(flags='--force')  # only one private branch makes sense


def sync(arguments=[]):
    # TODO improve flag parsing
    RESOLVE = any([a in ('-r', '--resolve') for a in arguments])
    sync_repo(RESOLVE)


def daemon(arguments=[]):
    SLEEP_TIME = 5  # seconds
    while True:
        save()
        time.sleep(SLEEP_TIME)


def tasks(arguments=[]):
    JSON = '--json' in arguments

    repo = Repo(os.getcwd())
    commits = repo.log

    # we'll use commit hashes to refer to specific commits while diffing
    hashes = list(reversed([c['hash'] for c in commits]))  # from oldest

    pairs = zip(hashes[:-1], hashes[1:])
    diffs = [repo.diff(a, b) for a, b in pairs]
    first_diff_show = repo._execute('show {}'.format(hashes[0]))
    first_diff = first_diff_show[first_diff_show.find('diff --git'):]
    diffs = [first_diff] + diffs
    parsed_tasks = [parse_diff(d) for d in diffs]

    raw_tasks = []
    for commit, tasks in zip(commits, parsed_tasks):
        for t in tasks:
            raw_tasks.append({
                "name": t['name'],
                "description": t['description'],
                "author": commit['author'],
                "date": commit['date'],
            })

    order_tasks(raw_tasks)

    if JSON:
        output = json.dumps(raw_tasks)
    else:
        # TODO
        output = 'Current tasks:\n{}'.format(raw_tasks)

    print output


def log(arguments=[]):
    repo = Repo(os.getcwd())
    print repo.log


def test(arguments=[]):
    # TODO
    errors = []
    if errors:
        # TODO
        print reduce(lambda a, b: a + b, map(str, errors), '')


def team(arguments=[]):
    print 'Working as {}@{}'.format(NAME, TEAM)
    print 'Projects:'
    for p in api.projects:
        print '  ' + p


commands = {
    'init': init,
    'save': save,
    'sync': sync,
    'daemon': daemon,
    'tasks': tasks,
    'log': log,
    'test': test,
    'team': team,
}

if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command in commands.keys():
            commands[command](sys.argv[2:])
        else:
            print 'Command not found: {}'.format(command)
            print tig_usage()
    else:
        print tig_usage()
