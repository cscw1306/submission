from os import listdir, remove
from os.path import isfile, join
import pandas as pd
import numpy as np
from todos import CommitInfo

class RepoDataHeader:
    LOC = "Code"
    REPO = "repo"
    SAMPLE = "Sample"
    LOG = "ln "
    TODO = "safe body"
    CONTEXT = "safe context"
    AGE = "Age"
    FILEPATHS = "filepaths"
    FILETOUCHES = "Filetouches"
    ADDED = "Added"
    DELETED = "Deleted"
    DAYS_OF_DATA = "Days of Data"
    AUTHOR_UNION = "Author Union"
    AUTHOR_INTERSECT = "Author Intersect"
        
class RepoDatumFileIO:
    # Does everything relating to parsing and validating.
    
    def __violation(self, violation):
        self.violations.append(violation)
    
    def __init__(self, handle):
        self.violations = []
        self.handle = handle
        self.__safe_handle = handle.replace("/", "_").replace("\\", "_").strip()
        self.__todo_file = None
        self.__cloc_file = None

    def validate_and_read(self):
        if self.__todo_file == None or self.__cloc_file == None:
            self.__violation("Failed validate_and_read: missing datafile")
            return False
        if not self.__read_cloc() or not self.__read_todos():
            self.__violation("Failed validate_and_read: bad read")
            return False
        return True
        
    def __read_todos(self):
        self.todos = pd.read_csv(self.__todo_file, quotechar='"', skipinitialspace=True)
        if len(self.todos) == 0:
            return True
        
        self.todos[RepoDataHeader.REPO] = self.handle
        
        blanks_zero = pd.isnull(self.todos[RepoDataHeader.TODO]).sum()
        if blanks_zero > 0:
            self.__violation("Todos can be NULL (" + str(added_zero) + " time(s))")
            
        added_zero = pd.isnull(self.todos[RepoDataHeader.ADDED]).sum()
        if added_zero > 0:
            self.__violation("Added can be NULL (" + str(added_zero) + " time(s))")
            
        if len(self.todos[self.todos[RepoDataHeader.AGE] == 0]) > 0:
            self.__violation("Age can be 0 or less")

        return True
        
    def __read_cloc(self):
        with open(self.__cloc_file) as f:
            ignore = True
            total_code = 0
            top_lang = None
            top_lang_code = 0
            total_comments = 0
            total_files = 0
            for line in f.readlines():
                if line.startswith("files,language,blank,comment,code"):
                    ignore = False
                elif not ignore:
                    values = line.split(",")
                    total_code += int(values[4])
                    total_comments += int(values[3])
                    total_files += int(values[0])
                    if top_lang == None: # First entry from cloc is most contributing lang
                        top_lang = values[1]
                        top_lang_code = int(values[4])
            self.cloc = {RepoDataHeader.LOC: total_code}
            return True
        self.__violation("Could not open and process cloc file")
        return False
    
    def add_file_if_matches(self, filename):
        if not self.__safe_handle in filename:
            return False
        if filename.endswith("_todos.csv"):
            self.__todo_file = filename
        elif filename.endswith("_cloc.csv"):
            self.__cloc_file = filename
        else:
            return False
        return True
    
    def get_sample_map(sample_list_filename):
        df = pd.read_csv(sample_list_filename, quotechar='"', sep=';', skipinitialspace=True)
        return df.set_index(RepoDataHeader.REPO).to_dict()[RepoDataHeader.SAMPLE]
    
    def remove_files(self):
        remove(self.__todo_file)
        remove(self.__cloc_file)

class RepoDataSample:
    
    def refresh(rds, kill_samples):
        for sample in kill_samples:
            for datum in rds.datum_list:
                if datum.handle == sample:
                    print("Removing " + sample)
                    datum.remove_files()
        slf = rds.__sample_list_filename
        del rds
        return RepoDataSample(slf)
    
    def __violation(self, violation):
        self.violations.append(violation)
    
    def print_violations(self):
        print("\n".join(self.violations))
        for datum in self.datum_list:
            if len(datum.violations) > 0:
                print(datum.handle + ": \n\t" + "\n\t".join(datum.violations))

    def __init__(self, sample_list_filename):
        self.__sample_list_filename = sample_list_filename
        self.sample_map = RepoDatumFileIO.get_sample_map(sample_list_filename)
        self.violations = []
        self.datum_list = []
        
        for handle, sample in self.sample_map.items():
            m = RepoDatumFileIO(handle)
            for f in listdir("."):
                m.add_file_if_matches(f)
            if m.validate_and_read():
                self.datum_list.append(m)

        self.combined_data = pd.concat(datum.todos for datum in self.datum_list)
        
        self.__agg_meta() # Add data from files
        self.__calc_per_repo() # Add data calculated
    
    def missing_samples(self):
        out = []
        for repo in self.sample_map.keys():
            if not repo in self.combined_data[RepoDataHeader.REPO].unique():
                empty_datum = False
                for datum in self.datum_list:
                    if datum.handle == repo:
                        self.__violation(repo + " has datafiles but no associated data")
                        empty_datum = True
                if not empty_datum:
                    out.append(repo)
        return out
    
    def violating_samples(self):
        out = []
        for datum in self.datum_list:
            if len(datum.violations) > 0:
                out.append(datum.handle)
        return out
    
    def all_meta_fields(self):
        output = set()
        for datum in self.datum_list:
            for key in datum.cloc.keys():
                output.add(key)
        return output
    
    def data_by_repo(self):
        g = self.combined_data.groupby(RepoDataHeader.REPO).agg({RepoDataHeader.DAYS_OF_DATA:['first'],
                                                        RepoDataHeader.SAMPLE:['first'],
                                                        RepoDataHeader.LOC:['first'],
                                                        RepoDataHeader.ADDED:['count'],
                                                        RepoDataHeader.DELETED:['count'],
                                                        RepoDataHeader.AGE:['mean']})
        g.columns = [col[0] for col in g.columns.values]

        g[RepoDataHeader.LOG + RepoDataHeader.DAYS_OF_DATA] = np.log(g[RepoDataHeader.DAYS_OF_DATA])
        g[RepoDataHeader.LOG + RepoDataHeader.LOC] = np.log(g[RepoDataHeader.LOC])
        return g
        
    # For now, just days of data. Also want: closed vs open only todos
    def __calc_per_repo(self):
        to_epoch = CommitInfo.epoch_from_human_readable
        q = self.combined_data
        q["minepoch"] = q.apply(lambda x: min(to_epoch(x[RepoDataHeader.ADDED], x[RepoDataHeader.DELETED]),
                                              to_epoch(x[RepoDataHeader.DELETED], x[RepoDataHeader.ADDED])), axis = 1)
        q["maxepoch"] = q.apply(lambda x: max(to_epoch(x[RepoDataHeader.ADDED], x[RepoDataHeader.DELETED]),
                                              to_epoch(x[RepoDataHeader.DELETED], x[RepoDataHeader.ADDED])), axis = 1)
        q = q.groupby(RepoDataHeader.REPO).agg({"minepoch":['min'],"maxepoch":['max']})
        q.columns = [' '.join(col).strip() for col in q.columns.values]
        q[RepoDataHeader.DAYS_OF_DATA] = (q["maxepoch max"] - q["minepoch min"]) / 60 / 60 / 24
        q[RepoDataHeader.REPO] = q.index
        q = q[[RepoDataHeader.REPO, RepoDataHeader.DAYS_OF_DATA]]
        self.combined_data = pd.merge(left=self.combined_data, right=q,
                      left_on=RepoDataHeader.REPO, right_on=RepoDataHeader.REPO)
        
    def __agg_meta(self):
        
        sum_data = {RepoDataHeader.REPO: [], RepoDataHeader.SAMPLE: []}
        
        for field in self.all_meta_fields():
            sum_data[field] = []
        
        for datum in self.datum_list:
            
            sum_data[RepoDataHeader.REPO].append(datum.handle)
            sum_data[RepoDataHeader.SAMPLE].append(self.sample_map[datum.handle])
            
            for key, value in datum.cloc.items():
                sum_data[key].append(value)
            
        len_prev = len(self.combined_data)
        
        self.combined_data = pd.merge(left=self.combined_data, right=pd.DataFrame(sum_data),
                      left_on=RepoDataHeader.REPO, right_on=RepoDataHeader.REPO)

        if len_prev != len(self.combined_data):
            self.__violation("Not all data in combined data were described by aggergate")
