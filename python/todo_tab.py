from stopwatch import Stopwatch
from todos import RepoCommitReader, TODO, TodoArgs
import csv, os
import argparse

ta = TodoArgs()
sw = Stopwatch()

for repo_handle in ta.get_repos():
    
    sw.reset()
    repo = RepoCommitReader.get_cloned_repo(ta.get_remote_dir(repo_handle),
        ta.get_local_dir(repo_handle))
    sw.lap("cloned repo", verbose = 1)
    
    repo.iterate_over_commits(int(ta.get_max_count()), int(ta.get_lines_after()))
    todos_map = repo.get_todos_map()
    sw.lap("analyze commits", verbose = 1)
    
    csv_data = []
    count = 0
    
    with ta.open_data_file(repo_handle, "_commithashes.txt") as repo_lookup_file:
        with ta.open_data_file(repo_handle, "_todos.csv") as repo_data_csv:
            with ta.open_data_file(repo_handle, "_summary.csv") as repo_summary_csv:
            
                header = ["repo", "todo ID"]
                header.extend(TODO.time_measures())
                header.extend(TODO.author_measures())
                header.extend(TODO.plaintext_measures())
                csv_data.append(header)

                for todo_handle, todo_obj in todos_map.items():
                    
                    repo_lookup_file.write("\ntodo ID = " + str(count) + "\n")
                    repo_lookup_file.write(str(todo_obj))
                    data_row = [repo_handle, count]
                    
                    data_row.extend(todo_obj.get_time_measures(repo))
                    data_row.extend(todo_obj.get_author_measures())
                    data_row.extend(todo_obj.get_plaintext_measures())
                    
                    csv_data.append(data_row)
                    count = count + 1

                sw.lap("write hash data", verbose = 1)
                writer = csv.writer(repo_data_csv, lineterminator='\n')
                writer.writerows(csv_data)
                sw.lap("write todo data", verbose = 1)
                
                repo_summary = [RepoCommitReader.repo_summary_measures()]
                repo_summary.append(repo.get_repo_summary_measures())
                writer = csv.writer(repo_summary_csv, lineterminator='\n')
                writer.writerows(repo_summary)

print("Stopwatch lap stats:")
print(sw)
