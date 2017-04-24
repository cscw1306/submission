from git import Repo, Commit, NULL_TREE
import time, datetime
import re
import math
import argparse, os
import pandas as pd

class TodoArgs:

    def __init__(self):
        parser = argparse.ArgumentParser(description='Run commit analysis on a set of repositories.')
        parser.add_argument('repos', metavar='Repo', type=str, nargs='+',
                            help='the names of repositories to include')
        parser.add_argument('--baseDir', dest='base_dir', default=".",
                            help='base directory to look for all the repositories (default: . )')
        parser.add_argument('--maxCount', dest='max_count', default=-1,
                            help='max number of commits to load (default: no limit, or -1)')
        parser.add_argument('--linesAfter', dest='lines_after', default=1,
                            help='number of lines to include following the TODO (default: 1)')
        parser.add_argument('--runHandle', dest='run_handle', default="run",
                            help='name of the meta file (default: run)')
        parser.add_argument('--cloneFrom', dest='clone_from', default="https://github.com/",
                            help='clone repos from here ' + 
                            '(default: https://github.com/)')
        self.args = parser.parse_args()
        
    def open_data_file(self, repo_handle, file_handle):
        return open(self.data_file_name(repo_handle, file_handle), "w") 
    
    def data_file_name(self, repo_handle, file_handle):
        return os.path.join(self.args.base_dir,
                            self.args.run_handle + "_" + repo_handle.replace("/", "_").replace("\\", "_") + "_" + file_handle)
    
    def get_local_dir(self, repo_handle):
        return os.path.join(self.args.base_dir, repo_handle)
        
    def get_remote_dir(self, repo_handle):
        return os.path.join(self.args.clone_from, repo_handle)
    
    def get_max_count(self):
        return int(self.args.max_count)
    
    def get_lines_after(self):
        return int(self.args.lines_after)
        
    def unparse_by_repo(self, head = "", tail = ""):
        output = {}
        for repo in self.args.repos:
            output[self.get_local_dir(repo)] = head + repo + " --baseDir " + self.args.base_dir + " --linesAfter " + str(self.args.lines_after) + " --runHandle " + self.args.run_handle + " --cloneFrom " + self.args.clone_from + " --maxCount " + str(self.args.max_count) + tail
        return output

    def get_repos(self):
        return self.args.repos

class RepoCommitReader:
    
    def __init__(self, repo):
        self.repo = repo

    def get_local_repo(local):
        return RepoCommitReader(Repo(local))
        
    def get_cloned_repo(remote, local):
        Repo.clone_from(remote, local)
        return RepoCommitReader.get_local_repo(local)
    
    def get_todo(self, todo_body):
        return self.todos_map.get(todo_body, TODO(todo_body))
    
    def save_todo(self, todo_body, todo):
        self.todos_map[todo_body] = todo
    
    def repo_summary_measures():
        return ["Total Commits",
                "Earliest Commit Epoch", "Latest Commit Epoch", "Days of Data",
                "Commits from Top 1 Author","Commits from Top 25% Authors",
                "Commits from Top 50% Authors",
                "Commits from Top 75% Authors","Commits from All Authors"]
    
    def get_repo_summary_measures(self):
        output = [self.commit_count, self.oldest_commit, self.newest_commit]
        output.append(CommitInfo.day_diff_from_epoch(self.oldest_commit, self.newest_commit))
        
        quarters = []
        quarter = int(math.floor(len(self.author_map)/4))
        quarter = (1 if quarter == 0 else quarter)
            
        while len(quarters) < 5:
            contribs = 0
            current = len(quarters)
            quarters.append(0)
            while contribs < quarter or current == 4:
                max_commits = 0
                max_author = None
                for author, commits in self.author_map.items():
                    if commits > max_commits:
                        max_commits = commits
                        max_author = author
                if max_author == None:
                    break
                    # On the last quarter, as long as current is 4, ie were in the last quarter
                    # Or if very few contributors and we run ot of them quickly
                self.author_map[max_author] = 0
                contribs += 1
                quarters[current] += max_commits
                if current == 0:
                    break
                    # The first "quarter" is just the single top contributor
        output.extend(quarters)
        
        return output
    
    def update_commit_agg_stats(self, commit):
        
        self.commit_count += 1
        self.author_map[CommitInfo.author(commit)] = self.author_map.get(CommitInfo.author(commit), 0) + 1
        epoch = CommitInfo.epoch_time(commit)
        self.oldest_commit = (epoch if epoch < self.oldest_commit else self.oldest_commit)
        self.newest_commit = (epoch if epoch > self.newest_commit else self.newest_commit)
        
    def update_with_raw_diff(self, diff, lines_after, commit, token_regex = r'(?i)TODO|FIXME'):

        todo_diffs = []
        file_ended = True
        current_path = ""
        lines = str(diff).split("\n") # FIXME: rly not using gitpython much, better use own wrapper   
        
       
        #print("------------------------")
        # print(commit)
        #print(str(diff))
        
        for index, line in enumerate(lines):
            if file_ended:
                current_path = line
                self.path_touches[current_path] = self.path_touches.get(current_path, 0) + 1
                file_ended = False
            else:
                if line == "---":
                    file_ended = True
                elif len(re.findall(token_regex, line)) > 0:
                    context = " ".join(s[2:].strip() for s in lines[index:index + 1 + lines_after])
                    if line.startswith("+ ") or line.startswith("- "):
                        todo_diffs.append(TODODiff(('A' if line.startswith("+") else 'D'),
                                          line[2:], context, current_path))
                        
        self.update_with_diff_list(commit, todo_diffs)
    
    def update_with_diff_list(self, commit, todo_diffs):

        # Note that we're pretty much just tossing body vs context out the window here, and using
        # the longer context form, rather than body
        for todo_diff in todo_diffs:
            
            todo = self.get_todo(todo_diff.body)
            
            if todo_diff.diff_type == 'A':
                todo.added_in_commit(commit)
            if todo_diff.diff_type == 'D':
                todo.deleted_in_commit(commit)
            todo.touched_by(todo_diff.path)
            todo.add_context(todo_diff.context)
            
            self.save_todo(todo_diff.body, todo)

    def iterate_over_commits(self, max_count = -1, lines_after = 1):
    
        # We zero all the counts once this is invoked.
        self.path_touches = {} # Map from file paths to number of times they were touched
        self.todos_map = {} # Map from todo_body to a TODO object with that body
        self.commit_count = 0 # Count of commits in the dataset
        self.oldest_commit = time.time() # Oldest commit in our dataset
        self.newest_commit = 0 # Most recent commit in our dataset
        self.author_map = {} # Map the number of commits from each author
        
        for commit in (self.repo.iter_commits(max_count = max_count)
                       if max_count > 0 else self.repo.iter_commits()):
            self.update_commit_agg_stats(commit)
           
            diff =  ( commit.parents[0].diff(commit, create_patch = True) 
                     if len(commit.parents)>0
                     else commit.diff(NULL_TREE, create_patch = True) )
            
            if len(commit.parents) == 0:
                    print("0- parent commit: " + str(commit))
            
            for changed_file in diff:
                self.update_with_raw_diff(changed_file, lines_after, commit)
        
    def get_todos_map(self):
        return self.todos_map
    
    def get_path_touches(self, path):
        return self.path_touches.get(path, 0)

class TODO:

    def __init__(self, TODO_body):
        self.body = TODO_body
        self.added = []
        self.deleted = []
        self.contexts = set()
        self.filepaths = set()
        
    def touched_by(self, filepath):
        self.filepaths.add(filepath)
        
    def count_touches(self, rcr):
        all_touches = 0
        for fp in self.filepaths:
            all_touches += rcr.get_path_touches(fp)
        return all_touches
        
    def add_context(self, context):
        self.contexts.add(context)
        
    def added_in_commit(self, commit):
        self.added.append(commit)
            
    def deleted_in_commit(self, commit):
        self.deleted.append(commit)
            
    def time_measures():
        return ["Added", "Deleted", "Age", "Filetouches"]
    
    def get_time_measures(self, rcr):
        return [CommitInfo.human_readable_from_epoch(CommitInfo.earliest_epoch(self.added)),
                CommitInfo.human_readable_from_epoch(CommitInfo.latest_epoch(self.deleted)),
                CommitInfo.day_diff_from_set(self.added, self.deleted, rcr.oldest_commit, rcr.newest_commit),
                self.count_touches(rcr)]
    
    def author_measures():
        return ["Author Union", "Author Intersect"]
    
    def get_author_measures(self):
        return [len(CommitInfo.authors(self.added, self.deleted)),
               len(CommitInfo.author_intersect(self.added, self.deleted))]
    
    def plaintext_measures():
        return ["safe body", "safe contexts", "filepaths"]
    
    def get_plaintext_measures(self):
        body = self.body.replace('\n', '\\n').replace('\r', '').strip()
        contexts = (c.replace('\n', '\\n').replace('\r', '').strip() for c in self.contexts)
        return [body, ";;;".join(contexts), ";".join(self.filepaths)]
    
    def __str__(self):
        output = self.body
        union = CommitInfo.authors(self.added, self.deleted)
        intersect = CommitInfo.author_intersect(self.added, self.deleted)
        for commit in self.added:
            output = output + "\n+ " + str(commit)
            output = output + "\n  " + str(CommitInfo.author(commit))
        for commit in self.deleted:
            output = output + "\n- " + str(commit)
            output = output + "\n  " + str(CommitInfo.author(commit))
        output = output + "\n Author Union Len: " + str(len(union))
        for author in union:
            output = output + "\nU " + str(author)
        output = output + "\n Author Intersect Len: " + str(len(intersect))
        for author in intersect:
            output = output + "\n^ " + str(author)
        return output
    
class TODODiff:
    
    # types: 'A' and 'D'
    def __init__(self, diff_type, body, context, path):
        self.diff_type = diff_type
        self.body = body
        self.context = context
        self.path = path
        
class CommitInfo:
    
    def epoch_time(commit):
        return commit.authored_date
    
    def author(commit):
        return commit.author.email
                              
    def epoch_from_human_readable(strtime, default = None):
        if pd.isnull(strtime):
            return (0 if default == None else CommitInfo.epoch_from_human_readable(default, None))
        dt = datetime.datetime.strptime(strtime, "%a, %d %b %Y %H:%M")
        return time.mktime(dt.timetuple())
        
    def human_readable_from_epoch(epoch):
        if epoch == None:
            return "N/A"
        return time.strftime("%a, %d %b %Y %H:%M", time.gmtime(epoch))
    
    def day_diff_from_set(commits_added, commits_deleted, default_min_date, default_max_date):
        return CommitInfo.day_diff_from_epoch(CommitInfo.earliest_epoch(commits_added, default_min_date),
                                              CommitInfo.latest_epoch(commits_deleted, default_max_date))
        
    def day_diff_from_epoch(earlier, later):
        return (later - earlier) / 60 / 60 / 24
                
    def latest_epoch(commit_set, default_max_date = None):
        
        if len(commit_set) == 0 and default_max_date == None:
            return default_max_date
        
        max_date = default_max_date
        changed = False
        for commit in commit_set:
            if not changed or CommitInfo.epoch_time(commit) > max_date:
                max_date = CommitInfo.epoch_time(commit)
                changed = True
        return max_date
        
    def earliest_epoch(commit_set, default_min_date = None):
        
        if len(commit_set) == 0 and default_min_date == None:
            return default_min_date
        
        min_date = default_min_date
        changed = False
        for commit in commit_set:
            if not changed or CommitInfo.epoch_time(commit) < min_date:
                min_date = CommitInfo.epoch_time(commit)
                changed = True
        return min_date
        
    def authors(commits_x, commits_y = []):
        output = set()
        for commit in commits_x:
            output.add(CommitInfo.author(commit))
        for commit in commits_y:
            output.add(CommitInfo.author(commit))
        return output
    
    def author_intersect(commits_x, commits_y):
        output = set()
        for a in CommitInfo.authors(commits_x):
            if a in CommitInfo.authors(commits_y):
                output.add(a)
        return output
