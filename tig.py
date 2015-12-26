#!/Users/grzegorz/Projects/Tig/tig-cli/venv/bin/python
import sys
import os
import subprocess
import time

from git import Repo


REMOTE = '/Users/grzegorz/Projects/Tig/tig-service/remotes'
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


api = FileSystemMockAPI(REMOTE, TEAM, NAME)

def daemon():
    SLEEP_TIME = 5  # seconds
    while True:
        save()
        time.sleep(SLEEP_TIME)


def save():
    repo = Repo(os.getcwd())
    if repo.changes:  # apparently empty list is falsy
        repo.add()
        repo.commit('Automated commit')


def project_exists(name):
    return name in api.projects

def init_project(project_name):
    if os.path.exists(project_name):
        print 'File already exists: {}'.format(project_name)
        exit(1)

    if not project_exists(project_name):
        api.create_project(project_name)
        repo = Repo.clone(api.project_url(project_name), '.', project_name)

        with open(os.path.join(project_name, 'README.md'), 'w') as f:
            default_readme = '''# TODO
'''
            f.write(default_readme)

        with open(os.path.join(project_name, '.gitignore'), 'w') as f:
            default_gitignore = '''# Don't spill your environment - exclude IDE and OS files in your private .gitignore
'''
            f.write(default_gitignore)

        with open(os.path.join(project_name, '.editorconfig'), 'w') as f:
            default_editorconfig= '''root = true

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

    branch_name = 'tig/master/{}'.format(NAME)
    repo.create_branch(branch_name)
    repo.change_branch(branch_name)

def init_usage():
    return '''Usage:
  tig init :project-name'''

def tig_usage():
    return '''Usage:
  tig init :project-name
    Join or create a new project'''

if __name__ == "__main__":
    # TODO properly parse arguments
    # print sys.argv
    if len(sys.argv) > 1:
        if sys.argv[1] == 'init':
            if len(sys.argv) > 2:
                init_project(sys.argv[2])
            else:
                print init_usage()
        elif sys.argv[1] == 'save':
            save()
        elif sys.argv[1] == 'daemon':
            daemon()
        else:
            print 'Command not found: {}'.format(sys.argv[1])
            print tig_usage()
    else:
        print tig_usage()
