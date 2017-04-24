import time

class Stopwatch:

    def __init__(self):
        self.counts = {}
        self.times = {}
        self.reset()
    
    def reset(self):
        self.clock = time.time()
    
    def lap(self, task, verbose = 0):
        elapsed = time.time() - self.clock
        self.reset()
        self.counts[task] = self.counts.get(task, 0) + 1
        self.times[task] = self.times.get(task, 0) + elapsed
        if verbose>0 and self.counts[task]%verbose == 0:
            print(task + " (iter. "+str(self.counts[task])+") took " + str(elapsed) + " seconds.")
    
    def __str__(self):
        out = ""
        for task, count in self.counts.items():
            avg = self.times[task] / count
            out = out + ("\n" if len(out) > 0 else "") + str(avg)
            out = out + "," + str(count) + "," + str(self.times[task]) + "," + task
        return out
