import os
from tests.fixtures import NoRepoTestCase, EmptyRepoTestCase, RepoTestCase, TwoBranchRepoTestCase


class TestNoRepo(NoRepoTestCase):
    def test_init(self):
        self._repo.init()
        # no exception is enough


class TestEmptyRepo(EmptyRepoTestCase):
    def test_current_branch(self):
        output = self._repo.current_branch
        expected_output = None
        self.assertEquals(expected_output, output, "Expected {}, got {}".format(expected_output, output))

    def test_branches(self):
        output = self._repo.branches
        expected_output = []
        self.assertEquals(expected_output, output, "Expected {}, got {}".format(expected_output, output))


class TestRepo(RepoTestCase):
    def test_current_branch(self):
        output = self._repo.current_branch
        expected_output = 'master'
        self.assertEquals(expected_output, output, "Expected {}, got {}".format(expected_output, output))

    def test_branches(self):
        output = self._repo.branches
        expected_output = ['master']
        self.assertEquals(expected_output, output, "Expected {}, got {}".format(expected_output, output))

    def test_log(self):
        output = self._repo.log
        expected_commit_count = 1
        expected_message = "Initial commit"
        self.assertEquals(expected_commit_count, len(output))
        self.assertEquals(expected_message, output[0]['message'])


class TestTwoBranchRepo(TwoBranchRepoTestCase):
    def test_current_branch(self):
        output = self._repo.current_branch
        expected_output = 'master'
        self.assertEquals(expected_output, output, "Expected {}, got {}".format(expected_output, output))

    def test_branches(self):
        output = self._repo.branches
        expected_output = ['dev', 'master']
        self.assertEquals(expected_output, output, "Expected {}, got {}".format(expected_output, output))

    def test_change_branch(self):
        self._repo.change_branch('dev')
        output = self._repo.current_branch
        expected_output = 'dev'
        self.assertEquals(expected_output, output, "Expected {}, got {}".format(expected_output, output))


class TestLog(EmptyRepoTestCase):
    def setUp(self):
        super(TestLog, self).setUp()

        file_path = os.path.join(self._repo._path, 'file.txt')
        with open(file_path, 'a'):
            os.utime(file_path, None)

        self._commit_message = 'Multi\n  line\n\ncommit'
        self._repo.add()
        self._repo.commit(self._commit_message)

    def test_multiline_log(self):
        output = self._repo.log
        expected_commit_count = 1
        expected_message = self._commit_message
        self.assertEquals(expected_commit_count, len(output))
        self.assertEquals(expected_message, output[0]['message'])
