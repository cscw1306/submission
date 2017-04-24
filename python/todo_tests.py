import unittest
from todos import TODO, RepoCommitReader
import io


class TODOTests(unittest.TestCase):
    
    def test_filetouches(self):
        self.todo = TODO("This is the TODO body")
        self.todo.touched_by("A")
        self.todo.touched_by("B")
        self.todo.touched_by("C")
        self.todo.touched_by("B")
        abc = set()
        abc.add("A")
        abc.add("B")
        abc.add("C")
        self.assertEqual(self.todo.filepaths, abc)

    def test_regex_filtering(self):
        rcr = RepoCommitReader(FakeRepo())
        rcr.iterate_over_commits(lines_after = 1)
        todos_map = rcr.get_todos_map()
        self.assertEqual(len(todos_map), 2)
        self.assertEqual("wow look this is a todo\\nand here is a fixme\\nthe line that follows" in todos_map,
                         True)
        self.assertEqual("todo\\ntodo\\nabc" in todos_map, True)
        self.assertEqual(len(todos_map), 2)
        rcr.iterate_over_commits(lines_after = 0)
        todos_map = rcr.get_todos_map()
        self.assertEqual(len(todos_map), 4)
        self.assertEqual("todo which is removed" in todos_map, True)
        self.assertEqual("wow look this is a todo" in todos_map, True)
        self.assertEqual("and here is a fixme" in todos_map, True)
        self.assertEqual("todo" in todos_map, True)
        
    def test_changelog(self):
        rcr = RepoCommitReader(FakeRepo())
        rcr.iterate_over_commits(lines_after = 0)
        todos_map = rcr.get_todos_map()
        self.assertEqual(len(todos_map["wow look this is a todo"].deleted), 1)
        self.assertEqual(len(todos_map["todo which is removed"].added), 1)
        self.assertEqual(len(todos_map["and here is a fixme"].deleted), 1)
        self.assertEqual(len(todos_map["todo"].ignored), 1)
        self.assertEqual(len(todos_map["wow look this is a todo"].ignored), 0)
        self.assertEqual(len(todos_map["todo which is removed"].ignored), 0)
        self.assertEqual(len(todos_map["and here is a fixme"].ignored), 0)
        self.assertEqual(len(todos_map["todo"].added), 0)
        self.assertEqual(len(todos_map["wow look this is a todo"].added), 0)
        self.assertEqual(len(todos_map["todo which is removed"].deleted), 0)
        self.assertEqual(len(todos_map["and here is a fixme"].added), 0)
        self.assertEqual(len(todos_map["todo"].deleted), 0)
        self.assertEqual(todos_map["todo"].get_ignore_sum(), 2)
        pass

    # todo. time_measures, get_time_measures(repo)
    # todo. author_measures, get_author_measures(repo)
    
    def test_filter_from_data_stream(self):
        
        #TODO.filter_from_data_stream()
        # TODO.filter_from_data_stream
        # TODO.UniqueHandle
        pass

class FakeAuthor:
    
    def __init__(self):
        self.email = "abc@me.me"
        
class FakeCommit:
    # .parents list
    # .diff(method) which returns list of FakeChangedFile
    # .author.email
    # .authored_date, which is an epoch
    def __init__(self):
        self.authored_date = 1480427844
        self.author = FakeAuthor()
    
    def diff(parent):
        return [FakeChangedFile()]

class FakeChangedFile:
    # .b_blob and .a_blob .a_rawpath b_rawpath, which are all byte arrays
    # eg, using f = io.BytesIO(b"some initial binary data:\n\n\rgdsfgsdfg \x00\x01")
    
    def __init__(self):
        self.a_blob = FakeBlob("A")
        self.b_blob = FakeBlob("B")
        self.a_rawpath = str.encode("path/one", "utf-8")
        self.b_rawpath = str.encode("path/two", "utf-8")

class FakeBlob:
    
    def __init__(self, blob_type):
        if blob_type == "A":
            self.data_stream = io.StringIO("\\nTODO\\nTODO\\nabc\\n\\nTODO which is removed")
        else:
            self.data_stream = io.StringIO("Wow look this is a TODO\\nand here is a FIXME\\nthe line that follows\\nTODO\\nTODO\\nabc\\n")

class FakeRepo:
    # .iter_commits() which returns commits
    def iter_commits(max_count):
        return [FakeCommit()]
    
if __name__ == '__main__':
    unittest.main()
    