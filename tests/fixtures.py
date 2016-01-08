from unittest import TestCase
from git import Repo
import os
import shutil


TEST_REPO_PATH = './test_repo'
FILE_NAME = 'file1.txt'


class NoRepoTestCase(TestCase):
    def setUp(self):
        if os.path.exists(TEST_REPO_PATH):
            raise Exception("Test repo path {} not empty".format(TEST_REPO_PATH))
        os.mkdir(TEST_REPO_PATH)
        self._repo = Repo(TEST_REPO_PATH)

    def tearDown(self):
        shutil.rmtree(TEST_REPO_PATH)


class EmptyRepoTestCase(NoRepoTestCase):
    def setUp(self):
        super(EmptyRepoTestCase, self).setUp()

        self._repo.init()


class RepoTestCase(EmptyRepoTestCase):
    def setUp(self):
        super(RepoTestCase, self).setUp()

        file_path = os.path.join(self._repo._path, FILE_NAME)
        with open(file_path, 'a'):
            os.utime(file_path, None)

        self._repo.add()
        self._repo.commit('Initial commit')


class TwoBranchRepoTestCase(RepoTestCase):
    def setUp(self):
        super(TwoBranchRepoTestCase, self).setUp()

        branch_name = 'dev'
        self._repo.create_branch(branch_name)
