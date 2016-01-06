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

def get_sync_branch(branch):
    if branch.endswith('/' + NAME):
        return branch[:-len('/' + NAME)]

def sync_repo(resolve=False):
    repo = Repo(os.getcwd())

    sync_branch = get_sync_branch(repo.current_branch)
    if sync_branch:
        repo.merge(sync_branch)
    else:
        print 'Unable to sync - you are not on a synching branch'


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

# TODO each of these usage functions should just be part of an instruction
def init_usage():
    return '''Usage:
  tig init :project-name'''

def tig_usage():
    # this is a function and not just a flat value to remind me to add some dynamic data to it
    return '''init :project-name
    Join or create a new project'''


def init(arguments):
    if len(arguments) > 0:
        project_name = arguments[0]
        init_project(project_name)
    else:
        print init_usage()

def save(arguments):
    if len(arguments) > 0:
        # TODO handle arguments
        pass  # for now just dismiss them
    repo = Repo(os.getcwd())
    if repo.changes:  # apparently empty list is falsy
        repo.add()
        repo.commit('Automated commit')

def sync(arguments):
    # TODO improve flag parsing
    RESOLVE = any([a in ('-r', '--resolve') for a in arguments])
    sync_repo(RESOLVE)

commands = {
    'init': init,
    'save': save,
    'sync': sync,
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
    #     elif sys.argv[1] == 'daemon':
    #         daemon()
    #     elif sys.argv[1] == 'tasks':
    #         if len(sys.argv) > 2:
    #             #
    #             pass
    #         else:
    #
    #         daemon()
    #     else:
    #         print 'Command not found: {}'.format(sys.argv[1])
    #         print TIG_USAGE
    # else:
    #     print TIG_USAGE
